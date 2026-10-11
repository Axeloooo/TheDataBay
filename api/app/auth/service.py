"""Wallet sign-in: one-time nonces, signature verification and bearer tokens.

Security properties:
- Nonces are random (128 bits), bound to one wallet, single use and short-lived.
  The first verify attempt burns the nonce whether or not it succeeds, and the
  burn is an atomic conditional UPDATE so two concurrent verifies cannot both
  succeed.
- The message the wallet signs is generated and stored by the server; the
  client never supplies it.
- Tokens are HS256 JWTs. Issuing or checking one fails closed (503) when
  ``AUTH_JWT_SECRET`` is unset or shorter than 32 characters.
"""

from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Union

from eth_account import Account
from eth_account.messages import encode_defunct
import jwt
from sqlalchemy import delete, update
from sqlmodel import Session, select
from web3 import Web3

from ..config.settings import Settings
from ..contracts import service as contract_service
from ..datasets.schemas import WalletType
from ..shared.errors import ApiError
from .models import AuthNonce
from .schemas import NonceResponse, TokenResponse

logger = logging.getLogger(__name__)

TOKEN_ALGORITHM = "HS256"
TOKEN_ISSUER = "thedatabay-api"
TOKEN_AUDIENCE = "thedatabay"
MIN_SECRET_LENGTH = 32
NONCE_RETENTION = timedelta(hours=1)
SIGN_IN_STATEMENT = (
    "Sign in to TheDataBay. This request will not trigger a blockchain "
    "transaction or cost any fees."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes (SQLite drops tzinfo) as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _unauthorized(message: str = "Sign-in failed.") -> ApiError:
    return ApiError(status_code=401, error="unauthorized", message=message)


def _wallet_type_value(wallet_type: Union[WalletType, str]) -> str:
    if isinstance(wallet_type, WalletType):
        return wallet_type.value
    return str(wallet_type).lower()


def _require_evm(wallet_type: Union[WalletType, str]) -> str:
    value = _wallet_type_value(wallet_type)
    if value == WalletType.SOLANA.value:
        raise ApiError(
            status_code=501,
            error="not_implemented",
            message="Solana sign-in is not supported yet.",
        )
    if value != WalletType.EVM.value:
        raise ApiError(
            status_code=400,
            error="invalid_wallet_type",
            message="Unsupported wallet type.",
        )
    return value


def jwt_secret(settings: Settings) -> str:
    """Return the token signing secret or fail closed with 503."""
    secret = (
        settings.auth_jwt_secret.get_secret_value()
        if settings.auth_jwt_secret is not None
        else ""
    )
    if len(secret) < MIN_SECRET_LENGTH:
        logger.error("auth.misconfigured AUTH_JWT_SECRET missing or too short")
        raise ApiError(
            status_code=503,
            error="auth_not_configured",
            message="Wallet sign-in is not configured on this server.",
        )
    return secret


def normalize_evm_address(address: str) -> str:
    """Return the EIP-55 checksum form or raise 400."""
    if not isinstance(address, str) or not Web3.is_address(address):
        raise ApiError(
            status_code=400,
            error="invalid_address",
            message="Invalid EVM address.",
        )
    return Web3.to_checksum_address(address)


def build_sign_in_message(
    *,
    domain: str,
    address: str,
    chain_id: int,
    nonce: str,
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    """Build an EIP-4361 (Sign-In with Ethereum) style message."""
    return (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n"
        "\n"
        f"{SIGN_IN_STATEMENT}\n"
        "\n"
        f"URI: https://{domain}\n"
        "Version: 1\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {_iso(issued_at)}\n"
        f"Expiration Time: {_iso(expires_at)}"
    )


def _prune_expired(session: Session, now: datetime) -> None:
    session.execute(
        delete(AuthNonce).where(AuthNonce.expires_at < now - NONCE_RETENTION)
    )


def create_nonce(
    session: Session,
    wallet_type: Union[WalletType, str],
    address: str,
    settings: Settings,
) -> NonceResponse:
    """Issue a one-time sign-in nonce and the exact message to sign."""
    wallet_type_value = _require_evm(wallet_type)
    jwt_secret(settings)
    checksum_address = normalize_evm_address(address)

    now = _utcnow()
    expires_at = now + timedelta(seconds=settings.auth_nonce_ttl_seconds)
    nonce = secrets.token_hex(16)
    message = build_sign_in_message(
        domain=settings.auth_domain,
        address=checksum_address,
        chain_id=settings.chain_id,
        nonce=nonce,
        issued_at=now,
        expires_at=expires_at,
    )

    _prune_expired(session, now)
    session.add(
        AuthNonce(
            wallet_type=wallet_type_value,
            address=checksum_address,
            nonce=nonce,
            message=message,
            created_at=now,
            expires_at=expires_at,
        )
    )
    session.commit()
    logger.info("auth.nonce issued wallet_type=%s", wallet_type_value)
    return NonceResponse(nonce=nonce, message=message, expires_at=expires_at)


def _burn_nonce(session: Session, row_id, now: datetime) -> bool:
    """Atomically mark the nonce used. Returns False if it was already used."""
    result = session.execute(
        update(AuthNonce)
        .where(AuthNonce.id == row_id, AuthNonce.used_at.is_(None))
        .values(used_at=now)
    )
    session.commit()
    return result.rowcount == 1


def _recover_signer(message: str, signature: str) -> str | None:
    try:
        return Account.recover_message(
            encode_defunct(text=message), signature=signature
        )
    except Exception:  # malformed signatures raise a variety of errors
        return None


def issue_token(
    wallet_type: str, address: str, settings: Settings
) -> TokenResponse:
    """Sign a bearer token for an already verified wallet."""
    secret = jwt_secret(settings)
    issued_at = int(_utcnow().timestamp())
    expires = issued_at + settings.auth_token_ttl_seconds
    wallet_id_hex = "0x" + bytes(
        contract_service.wallet_id(wallet_type, address, settings)
    ).hex()
    claims = {
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "sub": address,
        "wallet_type": wallet_type,
        "wallet_id": wallet_id_hex,
        "iat": issued_at,
        "exp": expires,
        "jti": secrets.token_hex(16),
    }
    token = jwt.encode(claims, secret, algorithm=TOKEN_ALGORITHM)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=datetime.fromtimestamp(expires, tz=timezone.utc),
        wallet_type=WalletType(wallet_type),
        address=address,
    )


def verify_signature(
    session: Session,
    wallet_type: Union[WalletType, str],
    address: str,
    nonce: str,
    signature: str,
    settings: Settings,
) -> TokenResponse:
    """Verify a signed sign-in message and return a bearer token.

    Raises:
        ApiError: 501 for Solana, 503 when unconfigured, 400 for a malformed
            address, 401 for any unknown, foreign, used or expired nonce and for
            any signature that does not recover to ``address``.
    """
    wallet_type_value = _require_evm(wallet_type)
    jwt_secret(settings)
    checksum_address = normalize_evm_address(address)

    row = session.exec(select(AuthNonce).where(AuthNonce.nonce == nonce)).first()
    if (
        row is None
        or row.wallet_type != wallet_type_value
        or row.address != checksum_address
        or row.used_at is not None
    ):
        logger.warning("auth.verify rejected reason=unknown_or_used_nonce")
        raise _unauthorized()

    now = _utcnow()
    if not _burn_nonce(session, row.id, now):
        logger.warning("auth.verify rejected reason=nonce_race")
        raise _unauthorized()

    if _as_utc(row.expires_at) <= now:
        logger.warning("auth.verify rejected reason=expired_nonce")
        raise _unauthorized()

    signer = _recover_signer(row.message, signature)
    if signer is None or signer != checksum_address:
        logger.warning("auth.verify rejected reason=bad_signature")
        raise _unauthorized()

    logger.info("auth.verify success wallet_type=%s", wallet_type_value)
    return issue_token(wallet_type_value, checksum_address, settings)
