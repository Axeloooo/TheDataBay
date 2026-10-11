"""Mirror Marketplace contract events into Postgres.

Safety properties:

* Only logs emitted by the configured Marketplace address are read (the
  address is part of the eth_getLogs filter and re-checked per log).
* Only blocks at or below ``latest - INDEXER_CONFIRMATIONS`` are read, so
  shallow reorgs never reach the tables.
* Every write is idempotent. Purchases are keyed by (tx_hash, log_index)
  and inserted with ON CONFLICT DO NOTHING. Listing updates carry the
  (block, log_index) of the event that produced them and are only applied
  when the incoming event is newer, so replays cannot roll state back.
* The cursor advances in the same transaction as the rows of each chunk:
  a crash mid-chunk rolls both back and the chunk is simply replayed.
* Every tick refreshes ``indexer_state.updated_at``; reads only trust the
  tables while that heartbeat is recent (see ``synced_state``).

Indexed reads therefore lag the chain by INDEXER_CONFIRMATIONS blocks plus
up to one poll interval.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import and_, or_, update
from sqlmodel import Session, select
from web3 import Web3
from web3.contract import Contract

from ..config.settings import Settings
from .models import IndexedListing, IndexedPurchase, IndexerState

logger = logging.getLogger(__name__)

STATE_NAME = "marketplace"
HANDLED_EVENTS = (
    "ItemCreated",
    "ItemPurchased",
    "PriceUpdated",
    "DatasetUrlUpdated",
    "SignatureUpdated",
)
# Smallest eth_getLogs range tried when a provider rejects a range.
MIN_LOG_RANGE = 1
# Reads stop trusting the tables when the heartbeat is older than this many
# poll intervals (and never sooner than MIN_STALE_SECONDS).
STALE_POLL_INTERVALS = 3
MIN_STALE_SECONDS = 60


class LogsRequestError(Exception):
    """eth_getLogs failed for a block range (often a provider range cap)."""

    def __init__(self, from_block: int, to_block: int, cause: Exception) -> None:
        super().__init__(
            f"eth_getLogs failed for blocks {from_block}-{to_block}: {type(cause).__name__}"
        )
        self.from_block = from_block
        self.to_block = to_block


@dataclass
class _Context:
    contract: Contract
    block_times: dict[int, datetime] = field(default_factory=dict)
    token_decimals: dict[str, int] = field(default_factory=dict)

    def block_time(self, block_number: int) -> datetime:
        if block_number not in self.block_times:
            block = self.contract.w3.eth.get_block(block_number)
            self.block_times[block_number] = datetime.fromtimestamp(
                int(block["timestamp"]), tz=timezone.utc
            )
        return self.block_times[block_number]

    def decimals(self, token: str) -> int:
        if token not in self.token_decimals:
            config = self.contract.functions.acceptedTokens(token).call()
            self.token_decimals[token] = int(config[1])
        return self.token_decimals[token]


def _hex(value: Any) -> str:
    if isinstance(value, str):
        return Web3.to_hex(hexstr=value).lower()
    return Web3.to_hex(value).lower()


def _insert(session: Session, model: type):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:  # pragma: no cover - only Postgres (prod) and SQLite (tests) are used
        raise RuntimeError(f"Unsupported database dialect for indexer: {dialect}")
    return insert(model)


def _is_newer(block: int, log_index: int):
    """SQL predicate: the incoming event is after the row's last applied event."""
    return or_(
        IndexedListing.last_event_block < block,
        and_(
            IndexedListing.last_event_block == block,
            IndexedListing.last_event_log_index < log_index,
        ),
    )


def _listing_missing(session: Session, listing_id: str) -> bool:
    return (
        session.exec(
            select(IndexedListing.listing_id).where(IndexedListing.listing_id == listing_id)
        ).first()
        is None
    )


def _apply_listing_update(
    session: Session, event: Any, values: dict[str, Any]
) -> int:
    block, log_index = int(event["blockNumber"]), int(event["logIndex"])
    listing_id = _hex(event["args"]["itemId"])
    result = session.exec(  # type: ignore[call-overload]
        update(IndexedListing)
        .where(IndexedListing.listing_id == listing_id)
        .where(_is_newer(block, log_index))
        .values(
            **values,
            last_event_block=block,
            last_event_log_index=log_index,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount == 0 and _listing_missing(session, listing_id):
        logger.warning(
            "indexer: %s for unknown listing %s at block %s (created before "
            "INDEXER_START_BLOCK?)",
            event["event"],
            listing_id,
            block,
        )
    return result.rowcount


def _on_item_created(session: Session, ctx: _Context, event: Any) -> int:
    args = event["args"]
    listing_id = _hex(args["itemId"])
    exists = session.exec(
        select(IndexedListing.listing_id).where(IndexedListing.listing_id == listing_id)
    ).first()
    if exists is not None:
        return 0
    # Title and description are not in the event and cannot change on-chain,
    # so the current view is authoritative for them.
    view = ctx.contract.functions.getItemView(args["itemId"]).call()
    stmt = (
        _insert(session, IndexedListing)
        .values(
            listing_id=listing_id,
            title=view[1],
            description=view[2],
            seller=args["seller"],
            payment_token=args["paymentToken"],
            payment_token_decimals=ctx.decimals(args["paymentToken"]),
            price=Decimal(args["price"]),
            dataset_url=args["datasetUrl"],
            dataset_hash=_hex(args["datasetHash"]),
            signature_url=args["signatureUrl"],
            signature_hash=_hex(args["signatureHash"]),
            created_block=int(event["blockNumber"]),
            created_log_index=int(event["logIndex"]),
            frozen=False,
            last_event_block=int(event["blockNumber"]),
            last_event_log_index=int(event["logIndex"]),
        )
        .on_conflict_do_nothing(index_elements=["listing_id"])
    )
    return session.exec(stmt).rowcount  # type: ignore[call-overload]


def _on_item_purchased(session: Session, ctx: _Context, event: Any) -> int:
    args = event["args"]
    block = int(event["blockNumber"])
    listing_id = _hex(args["itemId"])
    stmt = (
        _insert(session, IndexedPurchase)
        .values(
            tx_hash=_hex(event["transactionHash"]),
            log_index=int(event["logIndex"]),
            listing_id=listing_id,
            buyer=args["buyer"],
            payment_token=args["paymentToken"],
            price_paid=Decimal(args["pricePaid"]),
            fee_paid=Decimal(args["feePaid"]),
            seller_paid=Decimal(args["sellerPaid"]),
            block_number=block,
            block_time=ctx.block_time(block),
        )
        .on_conflict_do_nothing(index_elements=["tx_hash", "log_index"])
    )
    written = session.exec(stmt).rowcount  # type: ignore[call-overload]
    session.exec(  # type: ignore[call-overload]
        update(IndexedListing)
        .where(IndexedListing.listing_id == listing_id)
        .where(IndexedListing.frozen.is_(False))  # type: ignore[union-attr]
        .values(frozen=True, updated_at=datetime.now(timezone.utc))
    )
    if written and _listing_missing(session, listing_id):
        logger.warning(
            "indexer: purchase at block %s for unknown listing %s (created before "
            "INDEXER_START_BLOCK?); it will not appear in indexed reads",
            block,
            listing_id,
        )
    return written


def _on_price_updated(session: Session, ctx: _Context, event: Any) -> int:
    return _apply_listing_update(
        session, event, {"price": Decimal(event["args"]["newPrice"])}
    )


def _on_dataset_url_updated(session: Session, ctx: _Context, event: Any) -> int:
    return _apply_listing_update(
        session, event, {"dataset_url": event["args"]["newUrl"]}
    )


def _on_signature_updated(session: Session, ctx: _Context, event: Any) -> int:
    return _apply_listing_update(
        session,
        event,
        {
            "signature_url": event["args"]["newUrl"],
            "signature_hash": _hex(event["args"]["newHash"]),
        },
    )


_HANDLERS: dict[str, Callable[[Session, _Context, Any], int]] = {
    "ItemCreated": _on_item_created,
    "ItemPurchased": _on_item_purchased,
    "PriceUpdated": _on_price_updated,
    "DatasetUrlUpdated": _on_dataset_url_updated,
    "SignatureUpdated": _on_signature_updated,
}


def index_range(session: Session, contract: Contract, from_block: int, to_block: int) -> int:
    """Apply all handled Marketplace events in [from_block, to_block].

    Does not commit: the caller owns the transaction.

    Returns:
        int: Number of rows inserted or updated.
    """
    topics = {_hex(contract.events[name].topic): name for name in HANDLED_EVENTS}
    address = contract.address.lower()
    try:
        raw_logs = contract.w3.eth.get_logs(
            {
                "address": contract.address,
                "fromBlock": from_block,
                "toBlock": to_block,
                "topics": [list(topics)],
            }
        )
    except Exception as exc:
        raise LogsRequestError(from_block, to_block, exc) from exc
    logs = sorted(
        (
            log
            for log in raw_logs
            if not log.get("removed", False)
            and str(log["address"]).lower() == address
            and log["topics"]
            and _hex(log["topics"][0]) in topics
        ),
        key=lambda log: (int(log["blockNumber"]), int(log["logIndex"])),
    )

    ctx = _Context(contract=contract)
    written = 0
    for log in logs:
        name = topics[_hex(log["topics"][0])]
        event = contract.events[name]().process_log(log)
        written += _HANDLERS[name](session, ctx, event)
    session.flush()
    logger.info(
        "indexer: indexed blocks %s-%s logs=%s rows=%s",
        from_block,
        to_block,
        len(logs),
        written,
    )
    return written


def stale_after(settings: Settings) -> timedelta:
    """How old the indexer heartbeat may be before its tables are distrusted."""
    return timedelta(
        seconds=max(STALE_POLL_INTERVALS * settings.indexer_poll_seconds, MIN_STALE_SECONDS)
    )


def is_stale(state: IndexerState, settings: Settings, now: datetime | None = None) -> bool:
    """True when no indexer tick has refreshed the state recently."""
    if state.updated_at is None:
        return True
    updated = state.updated_at
    if updated.tzinfo is None:  # SQLite returns naive UTC timestamps
        updated = updated.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - updated > stale_after(settings)


def synced_state(session: Session, settings: Settings) -> IndexerState | None:
    """Return the indexer state when its tables can serve reads, else None.

    Tables serve reads only when the indexer is enabled, has completed a run,
    that run reached the confirmed head (it is not still backfilling), and a
    tick has refreshed the state recently (the indexer is not stuck).
    """
    if not settings.indexer_enabled:
        return None
    state = session.get(IndexerState, STATE_NAME)
    if state is None or state.chain_head_block is None:
        return None
    if state.last_indexed_block < state.chain_head_block - settings.indexer_confirmations:
        return None
    if is_stale(state, settings):
        return None
    return state


def _advance_cursor(session: Session, last_block: int, chain_head: int) -> None:
    state = session.get(IndexerState, STATE_NAME)
    if state is None:
        state = IndexerState(name=STATE_NAME, last_indexed_block=last_block)
    state.last_indexed_block = last_block
    state.chain_head_block = chain_head
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)


def run_once(
    session: Session,
    settings: Settings,
    contract: Contract | None = None,
    stop_event: threading.Event | None = None,
) -> int:
    """Index every confirmed block after the cursor, one committed chunk at a time.

    If the provider rejects a log range, the chunk size is halved for the
    rest of this run (down to MIN_LOG_RANGE). ``stop_event`` is checked
    between chunks so shutdown does not wait for a long backfill.

    Returns:
        int: Number of rows written across all chunks.
    """
    if contract is None:
        from ..contracts.service import _get_contract

        contract = _get_contract(settings)

    latest = int(contract.w3.eth.block_number)
    safe_head = latest - max(settings.indexer_confirmations, 0)
    state = session.get(IndexerState, STATE_NAME)
    cursor = state.last_indexed_block if state else settings.indexer_start_block - 1
    if safe_head <= cursor:
        if state is not None:
            # Nothing new is confirmed; still record the head and heartbeat.
            _advance_cursor(session, state.last_indexed_block, latest)
            session.commit()
        return 0

    chunk = max(settings.indexer_block_chunk, MIN_LOG_RANGE)
    written = 0
    start = cursor + 1
    while start <= safe_head:
        if stop_event is not None and stop_event.is_set():
            logger.info("indexer: stop requested; cursor at %s", start - 1)
            break
        end = min(start + chunk - 1, safe_head)
        try:
            written += index_range(session, contract, start, end)
            _advance_cursor(session, end, latest)
            session.commit()
        except LogsRequestError:
            session.rollback()
            if chunk <= MIN_LOG_RANGE:
                raise
            chunk = max(chunk // 2, MIN_LOG_RANGE)
            logger.warning(
                "indexer: eth_getLogs rejected blocks %s-%s; retrying with %s-block ranges",
                start,
                end,
                chunk,
            )
            continue
        except Exception:
            session.rollback()
            raise
        start = end + 1
    return written
