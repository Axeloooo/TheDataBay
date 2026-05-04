"""
Dataset key release router.
"""

import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from ..database.engine import get_session

from ..config.settings import Settings, get_settings
from .schemas import (
    DatasetEmbedResponse,
    DatasetPreviewResponse,
    KeyReleaseRequest,
    KeyReleaseResponse,
)
from .service import DatasetEmbedService, get_dataset_embed_service
from ..contracts import service as contract_service
from . import repository as dataset_key_repo
from ..shared.errors import ApiError

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])
logger = logging.getLogger(__name__)


@router.post("/embed", response_model=DatasetEmbedResponse)
async def embed_dataset(
    file: UploadFile = File(...),
    seller: str = Form(...),
    settlement_currency: str = Form("USDC"),
    settlement_decimals: int | None = Form(None),
    seller_wallet_type: str = Form("evm"),
    service: DatasetEmbedService = Depends(get_dataset_embed_service),
) -> DatasetEmbedResponse:
    """Synchronously embed, encrypt, upload, and persist a dataset."""
    logger.info(
        "datasets.embed route called filename=%s seller=%s currency=%s",
        file.filename,
        seller,
        settlement_currency,
    )
    return await service.embed(
        file=file,
        seller=seller,
        settlement_currency=settlement_currency,
        settlement_decimals=settlement_decimals,
        seller_wallet_type=seller_wallet_type,
    )


@router.get("/{listing_id}/preview", response_model=DatasetPreviewResponse)
async def get_dataset_preview(
    listing_id: str,
    session: Session = Depends(get_session),
) -> DatasetPreviewResponse:
    """Return persisted preview rows for a dataset listing."""
    record = dataset_key_repo.get_dataset_preview(session, listing_id)
    if record and record.preview:
        logger.info("datasets.preview found listing_id=%s", listing_id)
        return DatasetPreviewResponse.model_validate(record.preview)

    try:
        vector_preview = dataset_key_repo.get_vector_document_preview(
            session, listing_id
        )
    except Exception:
        logger.exception("datasets.preview vector_fallback_failed listing_id=%s", listing_id)
        vector_preview = None
    if vector_preview:
        logger.info("datasets.preview vector_fallback_found listing_id=%s", listing_id)
        return DatasetPreviewResponse.model_validate(vector_preview)

    logger.info("datasets.preview unavailable listing_id=%s", listing_id)
    raise ApiError(
        status_code=404,
        error="preview_unavailable",
        message="Dataset preview is not available for this listing.",
        details={"listing_id": listing_id},
    )


@router.post("/{id}/key", response_model=KeyReleaseResponse)
def release_key(
    id: str,
    request: KeyReleaseRequest,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> KeyReleaseResponse:
    """Release dataset encryption key if authorized.

    Args:
        id (str): Item ID
        request (KeyReleaseRequest): Key release request data
        settings (Settings, optional): Application settings. Defaults to Depends(get_settings).
        session (Session, optional): Database session. Defaults to Depends(get_session).

    Raises:
        HTTPException: Authentication error
        HTTPException: Key not found error

    Returns:
        KeyReleaseResponse: Dataset key release response
    """

    logger.info(
        "datasets.release_key called listing_id=%s wallet_type=%s",
        id,
        request.wallet_type,
    )
    wallet_id_bytes = contract_service.wallet_id(
        request.wallet_type, request.address, settings
    )

    authorized = contract_service.has_access(id, wallet_id_bytes, settings)

    if not authorized:
        logger.warning("datasets.release_key unauthorized listing_id=%s", id)
        raise HTTPException(status_code=403, detail="Access not authorized")

    record = dataset_key_repo.get_dataset_key(session, id)

    if not record:
        logger.warning("datasets.release_key missing_key listing_id=%s", id)
        raise HTTPException(status_code=404, detail="Key not found for listing")

    logger.info("datasets.release_key success listing_id=%s", id)

    return KeyReleaseResponse(
        id=id,
        key_b64=record.key_b64,
        nonce_b64=record.nonce_b64,
        algorithm="AES-256-GCM",
    )
