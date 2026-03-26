"""
Pydantic schemas for Marketplace endpoints.
"""

from typing import Literal
from pydantic import BaseModel, Field


SETTLEMENT_CURRENCY = "USDC"
SETTLEMENT_DECIMALS = 6


class MarketplaceDataItem(BaseModel):
    """Schema for a single data item."""

    id: str = Field(..., description="Unique identifier (bytes32 hex) for the data item")
    title: str = Field(..., description="Title of the data item")
    description: str = Field(..., description="Description of the data item")
    seller: str = Field(..., description="Seller address")
    price_atomic: str = Field(..., description="Price in settlement token atomic units")
    settlement_currency: Literal["USDC"] = Field(
        default=SETTLEMENT_CURRENCY, description="Settlement currency for purchases"
    )
    settlement_decimals: int = Field(
        default=SETTLEMENT_DECIMALS, description="Decimal places for settlement token atomic units"
    )
    dataset_url: str = Field(..., description="URL to the dataset")
    dataset_hash: str = Field(
        ..., description="Hash of the dataset for integrity verification"
    )
    signature_url: str = Field(..., description="URL to the signature embeddings")
    signature_hash: str = Field(
        ..., description="Hash of the signature embeddings for integrity verification"
    )
    exists: bool = Field(
        ..., description="Indicates if the item exists in the marketplace"
    )
    purchase_count: int = Field(
        ..., description="Number of purchases recorded for the item"
    )
