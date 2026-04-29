"""Dataset upload and embedding service."""

from __future__ import annotations

import base64
import csv
import logging
import os
import tempfile
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Depends, UploadFile
from langchain_community.document_loaders import CSVLoader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from web3 import Web3

from ..config.settings import Settings, get_settings
from ..contracts.marketplace_schemas import TOKEN_DECIMALS
from ..database.async_engine import get_async_session_factory
from ..shared.encryption import encrypt_bytes, generate_key
from ..shared.errors import ApiError
from ..shared.ipfs import upload_bytes
from ..shared.vectorstore import DATASET_ROWS_COLLECTION, vectorstore_for_settings
from .repository import DatasetKeyRepository
from .schemas import (
    DatasetEmbedResponse,
    DatasetPreviewResponse,
    DatasetStats,
    VectorSpec,
)

logger = logging.getLogger(__name__)


def _api_error(
    status_code: int,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ApiError:
    return ApiError(
        status_code=status_code,
        error=error,
        message=message,
        details=details or {},
    )


def _looks_numeric(value: str) -> bool:
    return value.replace(".", "", 1).replace("-", "", 1).isdigit()


def _parse_csv_preview(content: str) -> tuple[list[str], list[list[str]], bool, int]:
    rows = list(csv.reader(content.splitlines()))
    if not rows:
        raise _api_error(400, "invalid_file_format", "CSV file is empty.")

    has_header = False
    if len(rows) > 1:
        first_row_numeric = sum(1 for value in rows[0] if _looks_numeric(value))
        second_row_numeric = sum(1 for value in rows[1] if _looks_numeric(value))
        has_header = (
            first_row_numeric < len(rows[0]) * 0.3
            and second_row_numeric > len(rows[1]) * 0.5
        )

    data_rows: list[list[str]] = []
    empty_rows_skipped = 0
    start_idx = 1 if has_header else 0
    for row in rows[start_idx:]:
        if not row or all(not str(value).strip() for value in row):
            empty_rows_skipped += 1
            continue
        data_rows.append([str(value).strip() for value in row])

    if not data_rows:
        raise _api_error(400, "invalid_file_format", "CSV file has no data rows.")

    if has_header:
        column_names = [str(value).strip() for value in rows[0]]
    else:
        column_names = [f"feature_{i}" for i in range(len(data_rows[0]))]

    return column_names, data_rows, has_header, empty_rows_skipped


async def delete_stale_listing_documents(
    listing_id: str,
    current_ids: list[str],
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Delete PGVector row documents for a listing whose IDs are not current."""
    factory = session_factory or get_async_session_factory()
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    DELETE FROM langchain_pg_embedding e
                    USING langchain_pg_collection c
                    WHERE e.collection_id = c.uuid
                      AND c.name = :collection_name
                      AND e.cmetadata->>'listing_id' = :listing_id
                      AND e.id != ALL(:current_ids)
                    """
                ),
                {
                    "collection_name": DATASET_ROWS_COLLECTION,
                    "listing_id": listing_id,
                    "current_ids": current_ids,
                },
            )


class DatasetEmbedService:
    """Synchronous dataset upload, vectorization, encryption, and key persistence."""

    def __init__(
        self,
        settings: Settings,
        *,
        vectorstore_factory: Callable[[Settings], object] = vectorstore_for_settings,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        key_repository: DatasetKeyRepository | None = None,
        csv_loader_cls: type[CSVLoader] = CSVLoader,
        key_generator: Callable[[], bytes] = generate_key,
        encryptor: Callable[[bytes, bytes, bytes], tuple[bytes, bytes]] = encrypt_bytes,
        uploader: Callable[[bytes, str, Settings], Any] = upload_bytes,
        stale_document_deleter: Callable[..., Any] = delete_stale_listing_documents,
    ) -> None:
        self._settings = settings
        self._vectorstore_factory = vectorstore_factory
        self._session_factory = session_factory or get_async_session_factory()
        self._key_repository = key_repository or DatasetKeyRepository()
        self._csv_loader_cls = csv_loader_cls
        self._key_generator = key_generator
        self._encryptor = encryptor
        self._uploader = uploader
        self._stale_document_deleter = stale_document_deleter

    async def embed(
        self,
        *,
        file: UploadFile,
        title: str,
        description: str,
        seller: str,
        price_atomic: int,
        settlement_currency: str = "USDC",
        settlement_decimals: int | None = None,
        seller_wallet_type: str = "evm",
    ) -> DatasetEmbedResponse:
        """Embed a CSV dataset and return completed upload metadata."""
        del title, description, price_atomic
        started = time.perf_counter()
        filename = file.filename or ""
        self._validate_static_inputs(
            filename=filename,
            seller=seller,
            settlement_currency=settlement_currency,
            settlement_decimals=settlement_decimals,
            seller_wallet_type=seller_wallet_type,
        )

        raw = await file.read()
        file_size_mb = len(raw) / (1024 * 1024)
        if file_size_mb > self._settings.max_file_size_mb:
            raise _api_error(
                413,
                "file_too_large",
                f"File is {file_size_mb:.2f}MB; maximum is {self._settings.max_file_size_mb}MB.",
                {"max_file_size_mb": self._settings.max_file_size_mb},
            )

        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _api_error(
                400,
                "encoding_error",
                "CSV file must be UTF-8 encoded.",
            ) from exc

        row_count = sum(1 for row in csv.reader(decoded.splitlines()) if row)
        if row_count > self._settings.max_dataset_rows:
            raise _api_error(
                413,
                "too_many_rows",
                f"CSV has {row_count} rows; maximum is {self._settings.max_dataset_rows}.",
                {"max_dataset_rows": self._settings.max_dataset_rows},
            )

        column_names, data_rows, has_header, empty_rows_skipped = _parse_csv_preview(
            decoded
        )
        preview = DatasetPreviewResponse(
            column_names=column_names,
            rows=data_rows[:10],
        )
        stats = DatasetStats(
            total_rows=len(data_rows),
            total_columns=len(column_names),
            has_header=has_header,
            empty_rows_skipped=empty_rows_skipped,
        )
        vector_spec = VectorSpec(
            model=self._settings.embedding_model,
            dimension=self._settings.embedding_dimension,
        )
        listing_id = str(uuid.uuid4())
        tmp_path: str | None = None

        logger.info(
            "datasets.embed start listing_id=%s filename=%s rows=%s size_mb=%.3f",
            listing_id,
            filename,
            len(data_rows),
            file_size_mb,
        )

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".csv", delete=False
            ) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            docs = self._csv_loader_cls(file_path=tmp_path).load()
            for index, document in enumerate(docs):
                metadata = dict(getattr(document, "metadata", {}) or {})
                metadata.pop("source", None)
                metadata["listing_id"] = listing_id
                metadata["row_index"] = index
                document.metadata = metadata

            document_ids = [f"{listing_id}:{index}" for index in range(len(docs))]

            vectorstore = self._vectorstore_factory(self._settings)
            await vectorstore.acreate_collection()
            await vectorstore.aadd_documents(docs, ids=document_ids)
            await self._stale_document_deleter(
                listing_id, document_ids, self._session_factory
            )

            key = self._key_generator()
            ciphertext, nonce = self._encryptor(raw, key, listing_id.encode("utf-8"))
            dataset_url, dataset_hash = await self._uploader(
                ciphertext, filename, self._settings
            )

            async with self._session_factory() as session:
                async with session.begin():
                    await self._key_repository.upsert(
                        db=session,
                        listing_id=listing_id,
                        key_b64=base64.b64encode(key).decode("utf-8"),
                        nonce_b64=base64.b64encode(nonce).decode("utf-8"),
                        dataset_url=dataset_url,
                        dataset_hash=dataset_hash,
                        preview=preview.model_dump(),
                        stats=stats.model_dump(),
                        vector_spec=vector_spec.model_dump(),
                    )
        except ApiError:
            raise
        except Exception as exc:
            logger.exception("datasets.embed failed listing_id=%s", listing_id)
            if "pinata" in str(exc).lower() or "ipfs" in str(exc).lower():
                raise _api_error(
                    502,
                    "ipfs_error",
                    "Encrypted dataset upload failed.",
                    {"cause": str(exc)},
                ) from exc
            raise _api_error(
                500,
                "vectorstore_error",
                "Dataset vectorization or persistence failed.",
                {"cause": str(exc)},
            ) from exc
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except FileNotFoundError:
                    pass

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "datasets.embed completed listing_id=%s rows=%s docs=%s elapsed_ms=%s",
            listing_id,
            len(data_rows),
            len(document_ids),
            elapsed_ms,
        )
        return DatasetEmbedResponse(
            listing_id=listing_id,
            dataset_url=dataset_url,
            dataset_hash=dataset_hash,
            preview=preview,
            stats=stats,
            vector_spec=vector_spec,
        )

    def _validate_static_inputs(
        self,
        *,
        filename: str,
        seller: str,
        settlement_currency: str,
        settlement_decimals: int | None,
        seller_wallet_type: str,
    ) -> None:
        if not filename.lower().endswith(".csv"):
            raise _api_error(
                400,
                "invalid_file_format",
                "Only CSV files are supported.",
                {"filename": filename},
            )

        if seller_wallet_type.strip().lower() != "evm":
            raise _api_error(
                400,
                "unsupported_wallet_type",
                "Only EVM seller wallets are supported.",
                {"seller_wallet_type": seller_wallet_type},
            )

        if not Web3.is_address(seller):
            raise _api_error(
                400,
                "invalid_seller_address",
                "Seller must be a valid EVM address.",
                {"seller": seller},
            )

        normalized_currency = settlement_currency.strip().upper()
        if normalized_currency not in TOKEN_DECIMALS:
            raise _api_error(
                400,
                "unsupported_currency",
                "Unsupported settlement currency.",
                {"settlement_currency": settlement_currency},
            )

        expected_decimals = TOKEN_DECIMALS[normalized_currency]
        resolved_decimals = expected_decimals if settlement_decimals is None else settlement_decimals
        if resolved_decimals != expected_decimals:
            raise _api_error(
                400,
                "decimals_mismatch",
                f"{normalized_currency} requires {expected_decimals} decimals.",
                {
                    "settlement_currency": normalized_currency,
                    "expected_decimals": expected_decimals,
                    "settlement_decimals": resolved_decimals,
                },
            )


def get_dataset_embed_service(
    settings: Settings = Depends(get_settings),
) -> DatasetEmbedService:
    """FastAPI dependency for DatasetEmbedService."""
    return DatasetEmbedService(settings)
