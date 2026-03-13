"""
Pydantic schemas for dataset encryption key release.
"""

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
