"""Routes for the authenticated wallet's own purchases and listings."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..auth.dependencies import AuthedWallet, current_wallet
from ..config.settings import Settings, get_settings
from ..database.engine import get_session
from . import service
from .schemas import PurchasedListing, SellerListing

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/purchases", response_model=list[PurchasedListing])
def my_purchases(
    wallet: AuthedWallet = Depends(current_wallet),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> list[PurchasedListing]:
    """Listings the token's wallet has bought, newest first."""
    return service.get_purchases(session, wallet, settings)


@router.get("/listings", response_model=list[SellerListing])
def my_listings(
    wallet: AuthedWallet = Depends(current_wallet),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> list[SellerListing]:
    """Listings the token's wallet sells, with sales and earnings."""
    return service.get_seller_listings(session, wallet, settings)
