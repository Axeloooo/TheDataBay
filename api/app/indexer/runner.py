"""Background loop that runs the indexer inside the FastAPI process.

Every backend replica starts the loop, but only the replica holding a
Postgres session-level advisory lock indexes. The lock lives on a dedicated
connection kept open for as long as this replica is the indexer; if that
connection dies, Postgres releases the lock and another replica takes over
on its next tick. The others sleep and retry every poll interval.

Blocking work (SQL and RPC) runs in a worker thread so the event loop that
serves HTTP requests is never blocked. Shutdown sets a stop flag that the
indexer checks between chunks, and close() waits for the worker thread
before touching the lock connection, so that connection is never used from
two threads.

Errors back off exponentially (capped at MAX_BACKOFF_SECONDS) and are logged
by type with the RPC URL redacted: provider URLs often embed an API key.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

from sqlalchemy import Connection, Engine, text
from sqlmodel import Session
from web3.contract import Contract

from ..config.settings import Settings
from .service import run_once

logger = logging.getLogger(__name__)

# Arbitrary constant identifying "the marketplace indexer" lock. It must stay
# stable across releases and fit a signed 64-bit integer.
ADVISORY_LOCK_KEY = 0x7468656462617931  # ASCII "thedbay1"
MAX_BACKOFF_SECONDS = 60
CLOSE_TIMEOUT_SECONDS = 15.0


def redact_rpc_text(message: str, rpc_url: str) -> str:
    """Remove the RPC URL's secret parts (path, query, credentials) from text.

    The full URL is replaced by its redacted form; the path and query are
    also scrubbed on their own because HTTP client errors often print only
    the path (e.g. "Max retries exceeded with url: /v2/<key>").
    """
    from ..contracts.service import _redact_rpc_url

    if not rpc_url:
        return message
    out = message.replace(rpc_url, _redact_rpc_url(rpc_url))
    try:
        parsed = urlsplit(rpc_url)
    except ValueError:
        return out
    query = f"?{parsed.query}" if parsed.query else ""
    secrets = {parsed.path + query, parsed.path, parsed.query, parsed.username, parsed.password}
    for secret in sorted((s for s in secrets if s and s != "/"), key=len, reverse=True):
        out = out.replace(secret, "<redacted>")
    return out


def backoff_seconds(settings: Settings, consecutive_errors: int) -> float:
    """Poll interval after a success; doubles per consecutive error, capped."""
    poll = settings.indexer_poll_seconds
    if consecutive_errors <= 0:
        return poll
    return min(poll * 2**consecutive_errors, max(MAX_BACKOFF_SECONDS, poll))


class IndexerRunner:
    """One replica's indexer: owns the lock connection and a cached contract."""

    def __init__(
        self,
        settings: Settings,
        engine: Engine | None = None,
        contract_factory: Callable[[], Contract] | None = None,
    ) -> None:
        self.settings = settings
        self._engine = engine
        self._contract_factory = contract_factory
        self._contract: Contract | None = None
        self._lock_connection: Connection | None = None
        self._stop = threading.Event()
        # Held for the whole tick; close() takes it before touching the lock
        # connection so it is never used by two threads at once.
        self._busy = threading.Lock()

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            from ..database import engine as db_engine

            self._engine = db_engine.get_engine()
        return self._engine

    def _new_contract(self) -> Contract:
        if self._contract_factory is not None:
            return self._contract_factory()
        from ..contracts.service import _get_contract

        return _get_contract(self.settings)

    def _drop_lock_connection(self) -> None:
        conn, self._lock_connection = self._lock_connection, None
        if conn is None:
            return
        try:
            # Invalidate rather than return to the pool: closing the DBAPI
            # connection guarantees Postgres releases the session lock.
            conn.invalidate()
            conn.close()
        except Exception:  # pragma: no cover - best effort cleanup
            logger.debug("indexer: error closing lock connection", exc_info=True)

    def _hold_lock(self) -> bool:
        if self._lock_connection is not None:
            try:
                self._lock_connection.execute(text("SELECT 1"))
                self._lock_connection.commit()
                return True
            except Exception:
                logger.warning("indexer: lock connection lost; re-acquiring")
                self._drop_lock_connection()

        conn = self.engine.connect()
        try:
            acquired = bool(
                conn.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": ADVISORY_LOCK_KEY},
                ).scalar()
            )
            # End the implicit transaction; the session-level lock survives.
            conn.commit()
        except Exception:
            conn.invalidate()
            conn.close()
            raise
        if not acquired:
            conn.close()
            return False
        logger.info("indexer: acquired advisory lock; this replica is the indexer")
        self._lock_connection = conn
        return True

    def tick(self) -> int | None:
        """Index once if this replica holds the lock.

        Returns:
            int | None: Rows written, or None when another replica holds the lock.
        """
        with self._busy:
            if self._stop.is_set() or not self._hold_lock():
                return None
            if self._contract is None:
                self._contract = self._new_contract()
            try:
                with Session(self.engine) as session:
                    return run_once(
                        session,
                        self.settings,
                        contract=self._contract,
                        stop_event=self._stop,
                    )
            except Exception:
                self._contract = None  # rebuild the RPC client next tick
                raise

    def close(self, timeout: float = CLOSE_TIMEOUT_SECONDS) -> None:
        """Stop indexing, wait for a running tick, then release the lock.

        If the tick does not finish within ``timeout`` the lock connection is
        left alone (it is still in use); it closes with the process.
        """
        self._stop.set()
        if not self._busy.acquire(timeout=timeout):
            logger.warning(
                "indexer: tick still running after %ss; leaving the lock to process exit",
                timeout,
            )
            return
        try:
            conn = self._lock_connection
            if conn is not None:
                try:
                    conn.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY}
                    )
                    conn.commit()
                except Exception:
                    logger.debug("indexer: unlock failed; closing connection", exc_info=True)
            self._drop_lock_connection()
        finally:
            self._busy.release()


async def run_forever(
    settings: Settings,
    runner: Any | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Tick the indexer every INDEXER_POLL_SECONDS until cancelled."""
    runner = runner if runner is not None else IndexerRunner(settings)
    if settings.indexer_start_block > 0:
        logger.warning(
            "indexer: INDEXER_START_BLOCK=%s; listings created before block %s will "
            "not appear in indexed reads",
            settings.indexer_start_block,
            settings.indexer_start_block,
        )
    logger.info(
        "indexer: started start_block=%s chunk=%s confirmations=%s poll=%ss",
        settings.indexer_start_block,
        settings.indexer_block_chunk,
        settings.indexer_confirmations,
        settings.indexer_poll_seconds,
    )
    consecutive_errors = 0
    try:
        while True:
            try:
                written = await asyncio.to_thread(runner.tick)
                consecutive_errors = 0
                if written is None:
                    logger.debug("indexer: lock held by another replica")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                consecutive_errors += 1
                # No traceback: it would carry the unredacted RPC URL.
                logger.error(
                    "indexer: tick failed (%s): %s; retrying in %ss",
                    type(exc).__name__,
                    redact_rpc_text(str(exc), settings.rpc_url),
                    backoff_seconds(settings, consecutive_errors),
                )
            await sleep(backoff_seconds(settings, consecutive_errors))
    finally:
        await asyncio.to_thread(runner.close)
        logger.info("indexer: stopped")
