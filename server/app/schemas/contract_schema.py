"""
Pydantic schemas for contract router endpoints.
"""

from pydantic import BaseModel, Field

from .dataset_schema import WalletType


class TxHashResponse(BaseModel):
    """Transaction hash response schema."""

    tx_hash: str = Field(..., description="Submitted transaction hash")


class BuyItemRequest(BaseModel):
    """Buy item request schema."""

    value_wei: int = Field(..., ge=0, description="Payment amount in wei")


class UpdateDatasetUrlRequest(BaseModel):
    """Update dataset URL request schema."""

    new_url: str = Field(..., min_length=1, description="New dataset URL")


class UpdateSignatureRequest(BaseModel):
    """Update signature request schema."""

    new_url: str = Field(..., min_length=1, description="New signature URL")
    new_hash: str = Field(..., min_length=1, description="New signature hash (0x...)")


class UpdatePriceRequest(BaseModel):
    """Update price request schema."""

    new_price: int = Field(..., gt=0, description="New item price in wei")


class SetFeeConfigRequest(BaseModel):
    """Set fee config request schema."""

    fee_recipient: str = Field(..., description="Fee recipient EVM address")
    fee_bps: int = Field(..., ge=0, le=10_000, description="Fee basis points")


class TransferOwnershipRequest(BaseModel):
    """Transfer ownership request schema."""

    new_owner: str = Field(..., description="New owner EVM address")


class WalletAccessRequest(BaseModel):
    """Wallet access request schema."""

    wallet_type: WalletType = Field(..., description="Wallet type")
    address: str = Field(..., description="Wallet address/public key")


class AccessCheckResponse(BaseModel):
    """Access check response schema."""

    has_access: bool = Field(..., description="Whether wallet has access to item")


class GrantAccessRequest(BaseModel):
    """Grant access request schema."""

    wallet_type: WalletType = Field(..., description="Wallet type")
    address: str = Field(..., description="Wallet address/public key")


class CreateItemRequest(BaseModel):
    """Create item request schema."""

    listing_id: str = Field(..., description="UUID listing ID")
    title: str = Field(..., min_length=1, description="Item title")
    description: str = Field(..., min_length=1, description="Item description")
    seller: str = Field(..., description="Seller EVM address")
    price: int = Field(..., gt=0, description="Price in wei")
    dataset_url: str = Field(..., min_length=1, description="Encrypted dataset IPFS URL")
    dataset_hash: str = Field(..., min_length=1, description="Dataset sha256 hash (0x...)")
    signature_url: str = Field(..., min_length=1, description="Signature IPFS URL")
    signature_hash: str = Field(..., min_length=1, description="Signature sha256 hash (0x...)")
