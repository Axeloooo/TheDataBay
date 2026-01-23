"""
Pydantic schemas for Marketplace endpoints.
"""

from pydantic import BaseModel, Field


class MarketplaceDataItem(BaseModel):
    """Schema for a single data item."""

    id: int = Field(..., description="Unique identifier for the data item")
    title: str = Field(..., description="Title of the data item")
    description: str = Field(..., description="Description of the data item")
    seller: str = Field(..., description="Seller address")
    price: int = Field(..., description="Price in USD")
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
