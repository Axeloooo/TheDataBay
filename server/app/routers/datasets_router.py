"""
Dataset key release router.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..database.engine import get_session

from ..config.settings import Settings, get_settings
from ..schemas.dataset_schema import KeyReleaseRequest, KeyReleaseResponse
from ..services import contract_service, dataset_key_repo


router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])
logger = logging.getLogger(__name__)


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
