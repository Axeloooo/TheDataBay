"""Response models for the /api/v1/me endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DataSource = Literal["indexer", "contract"]


class PurchasedListing(BaseModel):
    listing_id: str
    title: str
    description: str
    dataset_url: str
    price_paid: str = Field(description="Amount paid in token base units (decimal string).")
    payment_token: str
    token_symbol: str
    token_decimals: int
    purchased_at: datetime | None = Field(
        default=None,
        description="Block time of the purchase; null when served from contract reads.",
    )
    source: DataSource


class SellerListing(BaseModel):
    listing_id: str
    title: str
    price: str = Field(description="Current price in token base units (decimal string).")
    payment_token: str
    token_symbol: str
    token_decimals: int
    sales_count: int
    earnings_by_token: dict[str, str] = Field(
        description=(
            "Sum of seller_paid per payment token address, in base units. "
            "Empty when source is 'contract' (earnings need the indexer)."
        )
    )
    price_editable: bool = Field(description="False once the listing has any sale.")
    source: DataSource
