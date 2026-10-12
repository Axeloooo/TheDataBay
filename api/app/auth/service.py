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
- Tokens carry a scope. ``user`` tokens (key release) and ``admin`` tokens
  (owner-only contract routes) use different audiences, so one is never
  accepted in place of the other. Admin tokens live at most 5 minutes and come
  from a message that plainly says it authorizes administrative actions.
- The audience includes ``AUTH_DOMAIN``, so tokens from one environment are
  rejected by another that shares the secret.
- Each address has at most MAX_OUTSTANDING_NONCES live nonces (oldest dropped)
  and expired rows are pruned in bounded batches.
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
from .schemas import AuthScope, NonceResponse, TokenResponse

logger = logging.getLogger(__name__)

TOKEN_ALGORITHM = "HS256"
TOKEN_ISSUER = "thedatabay-api"
MIN_SECRET_LENGTH = 32
MAX_OUTSTANDING_NONCES = 5
NONCE_RETENTION = timedelta(minutes=5)
PRUNE_BATCH_SIZE = 500
SIGN_IN_STATEMENT = (
    "Sign in to TheDataBay. This request will not trigger a blockchain "
    "transaction or cost any fees."
)
ADMIN_SIGN_IN_STATEMENT = (
    "ADMINISTRATOR SIGN-IN for the TheDataBay marketplace. Signing this message "
    "authorizes administrative contract actions for the next 5 minutes: fee "
    "changes, access grants, and listing price and dataset URL edits. Only sign "
    "if you are the marketplace operator and started this action yourself."
)


def _scope(value: Union[AuthScope, str]) -> AuthScope:
    try:
        return AuthScope(value.value if isinstance(value, AuthScope) else value)
    except ValueError as exc:
        raise ApiError(
            status_code=400, error="invalid_scope", message="Unsupported token scope."
        ) from exc


def token_audience(settings: Settings, scope: Union[AuthScope, str]) -> str:
    """Audience bound to this deployment's AUTH_DOMAIN and the token scope."""
    return f"thedatabay:{settings.auth_domain}:{_scope(scope).value}"


def _token_ttl_seconds(settings: Settings, scope: AuthScope) -> int:
    if scope == AuthScope.ADMIN:
        return settings.auth_admin_token_ttl_seconds
    return settings.auth_token_ttl_seconds


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


def same_evm_address(a: str | None, b: str | None) -> bool:
    """Return True when both values are the same EVM address, ignoring case.

    EVM addresses are case-insensitive (mixed case is only an EIP-55
    checksum), so a stored lowercase address matches the checksummed address
    carried by a token. Anything that is not a 20-byte hex address never
    matches.
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    a_lower, b_lower = a.lower(), b.lower()
    return Web3.is_address(a_lower) and a_lower == b_lower


def build_sign_in_message(
    *,
    scope: AuthScope = AuthScope.USER,
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
        f"{ADMIN_SIGN_IN_STATEMENT if scope == AuthScope.ADMIN else SIGN_IN_STATEMENT}\n"
        "\n"
        f"URI: https://{domain}\n"
        "Version: 1\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {_iso(issued_at)}\n"
        f"Expiration Time: {_iso(expires_at)}"
    )


def _prune_expired(session: Session, now: datetime) -> None:
    """Delete one bounded batch of nonces that expired over NONCE_RETENTION ago."""
    stale_ids = (
        select(AuthNonce.id)
        .where(AuthNonce.expires_at < now - NONCE_RETENTION)
        .limit(PRUNE_BATCH_SIZE)
    )
    session.execute(delete(AuthNonce).where(AuthNonce.id.in_(stale_ids)))


def _drop_excess_outstanding(
    session: Session, wallet_type: str, address: str, now: datetime
) -> None:
    """Keep room for one new nonce under the per-address cap (oldest dropped)."""
    outstanding = session.exec(
        select(AuthNonce.id)
        .where(
            AuthNonce.wallet_type == wallet_type,
            AuthNonce.address == address,
            AuthNonce.used_at.is_(None),
            AuthNonce.expires_at > now,
        )
        .order_by(AuthNonce.created_at.desc(), AuthNonce.id)
    ).all()
    excess = outstanding[MAX_OUTSTANDING_NONCES - 1 :]
    if excess:
        session.execute(delete(AuthNonce).where(AuthNonce.id.in_(excess)))


def create_nonce(
    session: Session,
    wallet_type: Union[WalletType, str],
    address: str,
    settings: Settings,
    scope: Union[AuthScope, str] = AuthScope.USER,
) -> NonceResponse:
    """Issue a one-time sign-in nonce and the exact message to sign."""
    wallet_type_value = _require_evm(wallet_type)
    scope = _scope(scope)
    jwt_secret(settings)
    checksum_address = normalize_evm_address(address)

    now = _utcnow()
    expires_at = now + timedelta(seconds=settings.auth_nonce_ttl_seconds)
    nonce = secrets.token_hex(16)
    message = build_sign_in_message(
        scope=scope,
        domain=settings.auth_domain,
        address=checksum_address,
        chain_id=settings.chain_id,
        nonce=nonce,
        issued_at=now,
        expires_at=expires_at,
    )

    _prune_expired(session, now)
    _drop_excess_outstanding(session, wallet_type_value, checksum_address, now)
    session.add(
        AuthNonce(
            wallet_type=wallet_type_value,
            scope=scope.value,
            address=checksum_address,
            nonce=nonce,
            message=message,
            created_at=now,
            expires_at=expires_at,
        )
    )
    session.commit()
    logger.info(
        "auth.nonce issued wallet_type=%s scope=%s", wallet_type_value, scope.value
    )
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
    wallet_type: str,
    address: str,
    settings: Settings,
    scope: Union[AuthScope, str] = AuthScope.USER,
) -> TokenResponse:
    """Sign a bearer token for an already verified wallet."""
    scope = _scope(scope)
    secret = jwt_secret(settings)
    issued_at = int(_utcnow().timestamp())
    expires = issued_at + _token_ttl_seconds(settings, scope)
    wallet_id_hex = "0x" + bytes(
        contract_service.wallet_id(wallet_type, address, settings)
    ).hex()
    claims = {
        "iss": TOKEN_ISSUER,
        "aud": token_audience(settings, scope),
        "scope": scope.value,
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
        scope=scope,
    )


REQUIRED_CLAIMS = [
    "exp", "iat", "iss", "aud", "scope", "sub", "wallet_type", "wallet_id",
]


def decode_token(
    token: str, settings: Settings, scope: Union[AuthScope, str] = AuthScope.USER
) -> dict:
    """Strictly verify a bearer token of the given scope and return its claims.

    The algorithm is pinned to HS256; ``exp``, ``iat``, issuer, the
    scope-and-domain audience and the wallet claims are all required. Any
    failure raises 401.
    """
    scope = _scope(scope)
    secret = jwt_secret(settings)
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[TOKEN_ALGORITHM],
            audience=token_audience(settings, scope),
            issuer=TOKEN_ISSUER,
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as exc:
        logger.info("auth.token rejected reason=%s", type(exc).__name__)
        raise _unauthorized("Invalid or expired token.") from exc
    if claims.get("scope") != scope.value:
        logger.info("auth.token rejected reason=scope_mismatch")
        raise _unauthorized("Invalid or expired token.")
    return claims


def verify_signature(
    session: Session,
    wallet_type: Union[WalletType, str],
    address: str,
    nonce: str,
    signature: str,
    settings: Settings,
    scope: Union[AuthScope, str] = AuthScope.USER,
) -> TokenResponse:
    """Verify a signed sign-in message and return a bearer token.

    Raises:
        ApiError: 501 for Solana, 503 when unconfigured, 400 for a malformed
            address, 401 for any unknown, foreign, used or expired nonce and for
            any signature that does not recover to ``address``.
    """
    wallet_type_value = _require_evm(wallet_type)
    scope = _scope(scope)
    jwt_secret(settings)
    checksum_address = normalize_evm_address(address)

    row = session.exec(select(AuthNonce).where(AuthNonce.nonce == nonce)).first()
    if (
        row is None
        or row.wallet_type != wallet_type_value
        or row.address != checksum_address
        or row.scope != scope.value
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

    logger.info(
        "auth.verify success wallet_type=%s scope=%s", wallet_type_value, scope.value
    )
    return issue_token(wallet_type_value, checksum_address, settings, scope=scope)
