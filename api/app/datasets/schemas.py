"""Pydantic schemas for dataset upload, preview, and key release."""

from enum import Enum
from pydantic import BaseModel, Field


class WalletType(str, Enum):
    EVM = "evm"
    SOLANA = "solana"


class KeyReleaseRequest(BaseModel):
    wallet_type: WalletType = Field(..., description="Wallet type (evm, solana)")
    address: str = Field(..., description="Wallet address or public key")


class KeyReleaseResponse(BaseModel):
    id: str = Field(..., description="Listing UUID")
    key_b64: str = Field(..., description="AES key (base64)")
    nonce_b64: str = Field(..., description="AES-GCM nonce (base64)")
    algorithm: str = Field(..., description="Encryption algorithm")


class DatasetPreviewResponse(BaseModel):
    """First rows of a dataset returned before purchase."""

    column_names: list[str] = Field(..., description="Dataset column headers")
    rows: list[list[str]] = Field(..., description="Up to 10 preview rows")


class DatasetStats(BaseModel):
    """Dataset statistics."""

    total_rows: int = Field(..., description="Total number of data rows")
    total_columns: int = Field(..., description="Total number of columns")
    has_header: bool = Field(..., description="Whether dataset appears to have a header row")
    empty_rows_skipped: int = Field(
        default=0, description="Number of empty rows skipped"
    )


class VectorSpec(BaseModel):
    """Vector specification metadata."""

    model: str = Field(..., description="Embedding model name")
    dimension: int = Field(..., description="Embedding vector dimension")


class DatasetEmbedResponse(BaseModel):
    """Completed synchronous dataset embed response."""

    listing_id: str = Field(..., description="Listing UUID")
    dataset_url: str = Field(..., description="Encrypted dataset IPFS URL")
    dataset_hash: str = Field(..., description="Encrypted dataset SHA-256 hash")
    preview: DatasetPreviewResponse
    stats: DatasetStats
    vector_spec: VectorSpec
