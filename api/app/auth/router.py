"""Wallet sign-in routes."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..config.settings import Settings, get_settings
from ..database.engine import get_session
from . import service as auth_service
from .schemas import NonceRequest, NonceResponse, TokenResponse, VerifyRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/nonce", response_model=NonceResponse)
def request_nonce(
    request: NonceRequest,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> NonceResponse:
    """Issue a one-time nonce and the exact message the wallet must sign."""
    return auth_service.create_nonce(
        session, request.wallet_type, request.address, settings, scope=request.scope
    )


@router.post("/verify", response_model=TokenResponse)
def verify(
    request: VerifyRequest,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Verify the signed message and return a short-lived bearer token."""
    return auth_service.verify_signature(
        session,
        request.wallet_type,
        request.address,
        request.nonce,
        request.signature,
        settings,
        scope=request.scope,
    )
