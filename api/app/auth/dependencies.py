"""FastAPI dependencies that turn a bearer token into an authenticated wallet.

The wallet identity used by protected routes comes only from a verified token,
never from a request body or query parameter.
"""

from dataclasses import dataclass

from fastapi import Depends, Header

from ..config.settings import Settings, get_settings
from ..contracts import service as contract_service
from ..datasets.schemas import WalletType
from ..shared.errors import ApiError
from . import service as auth_service
from .schemas import AuthScope


@dataclass(frozen=True)
class AuthedWallet:
    wallet_type: WalletType
    address: str
    wallet_id: bytes


def _unauthorized(message: str = "Invalid or expired token.") -> ApiError:
    return ApiError(status_code=401, error="unauthorized", message=message)


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _unauthorized("Missing bearer token.")
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise _unauthorized("Malformed Authorization header.")
    return parts[1]


def _wallet_from_token(
    authorization: str | None, settings: Settings, scope: AuthScope
) -> AuthedWallet:
    token = _bearer_token(authorization)
    claims = auth_service.decode_token(token, settings, scope)

    if claims.get("wallet_type") != WalletType.EVM.value:
        raise _unauthorized()
    sub = claims.get("sub")
    try:
        address = auth_service.normalize_evm_address(sub)
    except ApiError as exc:
        raise _unauthorized() from exc
    if address != sub:
        raise _unauthorized()

    # Recompute the wallet id for this deployment's chain; a token minted for
    # another chain id (or with a forged claim) does not match.
    wallet_id = contract_service.wallet_id(WalletType.EVM, address, settings)
    if claims.get("wallet_id") != "0x" + bytes(wallet_id).hex():
        raise _unauthorized()

    return AuthedWallet(
        wallet_type=WalletType.EVM, address=address, wallet_id=bytes(wallet_id)
    )


def current_wallet(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthedWallet:
    """Return the wallet proven by a user-scope bearer token, or raise 401."""
    return _wallet_from_token(authorization, settings, AuthScope.USER)


def current_admin_wallet(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthedWallet:
    """Return the wallet proven by an admin-scope bearer token, or raise 401."""
    return _wallet_from_token(authorization, settings, AuthScope.ADMIN)


def require_owner(
    wallet: AuthedWallet = Depends(current_admin_wallet),
    settings: Settings = Depends(get_settings),
) -> AuthedWallet:
    """Allow only the contract owner holding an admin token; 403 otherwise."""
    owner = contract_service.owner(settings)
    if wallet.wallet_type != WalletType.EVM or str(owner).lower() != wallet.address.lower():
        raise ApiError(
            status_code=403,
            error="forbidden",
            message="Only the marketplace owner can perform this action.",
        )
    return wallet
