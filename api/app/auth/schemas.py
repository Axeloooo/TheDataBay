"""Pydantic schemas for wallet sign-in."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ..datasets.schemas import WalletType


class AuthScope(str, Enum):
    """``user`` tokens unlock key release; ``admin`` tokens unlock owner routes."""

    USER = "user"
    ADMIN = "admin"


class NonceRequest(BaseModel):
    wallet_type: WalletType = Field(..., description="Wallet type (evm, solana)")
    address: str = Field(..., min_length=1, max_length=128)
    scope: AuthScope = Field(AuthScope.USER, description="Token scope (user, admin)")


class NonceResponse(BaseModel):
    nonce: str = Field(..., description="One-time nonce")
    message: str = Field(..., description="Exact message the wallet must sign")
    expires_at: datetime = Field(..., description="Nonce expiry (UTC)")


class VerifyRequest(BaseModel):
    wallet_type: WalletType = Field(..., description="Wallet type (evm, solana)")
    address: str = Field(..., min_length=1, max_length=128)
    nonce: str = Field(..., min_length=1, max_length=128)
    signature: str = Field(..., min_length=1, max_length=512)
    scope: AuthScope = Field(AuthScope.USER, description="Must match the nonce scope")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime = Field(..., description="Token expiry (UTC)")
    wallet_type: WalletType
    address: str
    scope: AuthScope = AuthScope.USER
