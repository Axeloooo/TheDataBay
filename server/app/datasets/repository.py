"""
Repository for dataset key persistence.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from ..models.dataset_key import DatasetKey
from ..models.dataset_preview import DatasetPreview
from ..shared.vectorstore import DATASET_ROWS_COLLECTION


def upsert_dataset_key(
    session: Session,
    listing_id: str,
    key_b64: str,
    nonce_b64: str,
    dataset_url: str,
    dataset_hash: str,
    preview: dict[str, Any] | None = None,
    stats: dict[str, Any] | None = None,
    vector_spec: dict[str, Any] | None = None,
) -> DatasetKey:
    """Insert or update dataset key record.

    Args:
        session (Session): Database session
        listing_id (str): Listing ID (UUID)
        key_b64 (str): Base64-encoded encryption key
        nonce_b64 (str): Base64-encoded nonce
        dataset_url (str): URL of the dataset
        dataset_hash (str): Hash of the dataset

    Returns:
        DatasetKey: Updated or created DatasetKey record
    """

    statement = select(DatasetKey).where(DatasetKey.listing_id == listing_id)
    existing = session.exec(statement).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.key_b64 = key_b64
        existing.nonce_b64 = nonce_b64
        existing.dataset_url = dataset_url
        existing.dataset_hash = dataset_hash
        existing.updated_at = now
        session.add(existing)
        if preview is not None:
            upsert_dataset_preview(
                session=session,
                listing_id=listing_id,
                preview=preview,
                stats=stats,
                vector_spec=vector_spec,
                commit=False,
            )
        session.commit()
        session.refresh(existing)
        return existing

    record = DatasetKey(
        listing_id=listing_id,
        key_b64=key_b64,
        nonce_b64=nonce_b64,
        dataset_url=dataset_url,
        dataset_hash=dataset_hash,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    if preview is not None:
        upsert_dataset_preview(
            session=session,
            listing_id=listing_id,
            preview=preview,
            stats=stats,
            vector_spec=vector_spec,
            commit=False,
        )
    session.commit()
    session.refresh(record)
    return record


def upsert_dataset_preview(
    session: Session,
    listing_id: str,
    preview: dict[str, Any],
    stats: dict[str, Any] | None = None,
    vector_spec: dict[str, Any] | None = None,
    *,
    commit: bool = True,
) -> DatasetPreview:
    """Insert or update durable preview metadata using a sync session."""

    statement = select(DatasetPreview).where(DatasetPreview.listing_id == listing_id)
    existing = session.exec(statement).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.preview = preview
        existing.stats = stats
        existing.vector_spec = vector_spec
        existing.updated_at = now
        session.add(existing)
        if commit:
            session.commit()
            session.refresh(existing)
        return existing

    record = DatasetPreview(
        listing_id=listing_id,
        preview=preview,
        stats=stats,
        vector_spec=vector_spec,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    if commit:
        session.commit()
        session.refresh(record)
    return record


async def async_upsert_dataset_key(
    db: AsyncSession,
    listing_id: str,
    key_b64: str,
    nonce_b64: str,
    dataset_url: str,
    dataset_hash: str,
    preview: dict[str, Any] | None = None,
    stats: dict[str, Any] | None = None,
    vector_spec: dict[str, Any] | None = None,
) -> DatasetKey:
    """Insert or update a DatasetKey row using an async session.

    Flushes but does NOT commit — the caller owns the transaction.

    Args:
        db (AsyncSession): Open async database session.
        listing_id (str): Listing ID (UUID string).
        key_b64 (str): Base64-encoded encryption key.
        nonce_b64 (str): Base64-encoded nonce.
        dataset_url (str): URL of the encrypted dataset on IPFS.
        dataset_hash (str): Content hash of the encrypted dataset.

    Returns:
        DatasetKey: The upserted record.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(DatasetKey)
        .values(
            listing_id=listing_id,
            key_b64=key_b64,
            nonce_b64=nonce_b64,
            dataset_url=dataset_url,
            dataset_hash=dataset_hash,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["listing_id"],
            set_={
                "key_b64": key_b64,
                "nonce_b64": nonce_b64,
                "dataset_url": dataset_url,
                "dataset_hash": dataset_hash,
                "updated_at": now,
            },
        )
        .returning(DatasetKey)
    )
    result = await db.execute(stmt)
    row = result.scalar_one()
    if preview is not None:
        await async_upsert_dataset_preview(
            db=db,
            listing_id=listing_id,
            preview=preview,
            stats=stats,
            vector_spec=vector_spec,
        )
    await db.flush()
    return row


async def async_upsert_dataset_preview(
    db: AsyncSession,
    listing_id: str,
    preview: dict[str, Any],
    stats: dict[str, Any] | None = None,
    vector_spec: dict[str, Any] | None = None,
) -> DatasetPreview:
    """Insert or update durable preview metadata using an async session."""

    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(DatasetPreview)
        .values(
            listing_id=listing_id,
            preview=preview,
            stats=stats,
            vector_spec=vector_spec,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["listing_id"],
            set_={
                "preview": preview,
                "stats": stats,
                "vector_spec": vector_spec,
                "updated_at": now,
            },
        )
        .returning(DatasetPreview)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


class DatasetKeyRepository:
    """Async repository for dataset encryption key persistence."""

    async def upsert(
        self,
        db: AsyncSession,
        listing_id: str,
        key_b64: str,
        nonce_b64: str,
        dataset_url: str,
        dataset_hash: str,
        preview: dict[str, Any] | None = None,
        stats: dict[str, Any] | None = None,
        vector_spec: dict[str, Any] | None = None,
    ) -> DatasetKey:
        """Insert or update key material for a listing."""
        return await async_upsert_dataset_key(
            db=db,
            listing_id=listing_id,
            key_b64=key_b64,
            nonce_b64=nonce_b64,
            dataset_url=dataset_url,
            dataset_hash=dataset_hash,
            preview=preview,
            stats=stats,
            vector_spec=vector_spec,
        )


def get_dataset_key(session: Session, listing_id: str) -> Optional[DatasetKey]:
    """Retrieve dataset key record by listing ID.

    Args:
        session (Session): Database session
        listing_id (str): Listing ID (UUID)

    Returns:
        Optional[DatasetKey]: DatasetKey record or None if not found
    """

    statement = select(DatasetKey).where(DatasetKey.listing_id == listing_id)
    return session.exec(statement).first()


def get_dataset_preview(session: Session, listing_id: str) -> Optional[DatasetPreview]:
    """Retrieve preview metadata for a dataset listing."""

    statement = select(DatasetPreview).where(DatasetPreview.listing_id == listing_id)
    return session.exec(statement).first()


def _preview_from_documents(documents: list[str]) -> dict[str, Any] | None:
    """Build a tabular preview from CSVLoader document text."""

    column_names: list[str] = []
    rows: list[list[str]] = []
    for document in documents:
        values: dict[str, str] = {}
        ordered_keys: list[str] = []
        for line in document.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue
            key = key.strip()
            if not key:
                continue
            ordered_keys.append(key)
            values[key] = value.strip()

        if not values:
            continue
        if not column_names:
            column_names = ordered_keys
        rows.append([values.get(column_name, "") for column_name in column_names])

    if not column_names or not rows:
        return None
    return {"column_names": column_names, "rows": rows}


def get_vector_document_preview(
    session: Session,
    listing_id: str,
    limit: int = 10,
) -> dict[str, Any] | None:
    """Best-effort preview fallback from persisted LangChain row documents."""

    result = session.execute(
        text(
            """
            SELECT e.document
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON c.uuid = e.collection_id
            WHERE c.name = :collection_name
              AND e.cmetadata->>'listing_id' = :listing_id
            ORDER BY (e.cmetadata->>'row_index')::integer ASC
            LIMIT :limit
            """
        ),
        {
            "collection_name": DATASET_ROWS_COLLECTION,
            "listing_id": listing_id,
            "limit": limit,
        },
    )
    documents = [
        str(row["document"])
        for row in result.mappings().all()
        if row.get("document") is not None
    ]
    return _preview_from_documents(documents)
