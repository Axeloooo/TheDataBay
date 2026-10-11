"""Background loop that runs the indexer inside the FastAPI process.

Every backend replica starts the loop, but only the replica holding a
Postgres session-level advisory lock indexes. The lock lives on a dedicated
connection kept open for as long as this replica is the indexer; if that
connection dies, Postgres releases the lock and another replica takes over
on its next tick. The others sleep and retry every poll interval.

Blocking work (SQL and RPC) runs in a worker thread so the event loop that
serves HTTP requests is never blocked.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from sqlalchemy import Connection, Engine, text
from sqlmodel import Session
from web3.contract import Contract

from ..config.settings import Settings
from .service import run_once

logger = logging.getLogger(__name__)

# Arbitrary constant identifying "the marketplace indexer" lock. It must stay
# stable across releases and fit a signed 64-bit integer.
ADVISORY_LOCK_KEY = 0x7468656462617931  # ASCII "thedbay1"


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
        if not self._hold_lock():
            return None
        if self._contract is None:
            self._contract = self._new_contract()
        try:
            with Session(self.engine) as session:
                return run_once(session, self.settings, contract=self._contract)
        except Exception:
            self._contract = None  # rebuild the RPC client next tick
            raise

    def close(self) -> None:
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


async def run_forever(
    settings: Settings,
    runner: Any | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Tick the indexer every INDEXER_POLL_SECONDS until cancelled."""
    runner = runner if runner is not None else IndexerRunner(settings)
    logger.info(
        "indexer: started start_block=%s chunk=%s confirmations=%s poll=%ss",
        settings.indexer_start_block,
        settings.indexer_block_chunk,
        settings.indexer_confirmations,
        settings.indexer_poll_seconds,
    )
    try:
        while True:
            try:
                written = await asyncio.to_thread(runner.tick)
                if written is None:
                    logger.debug("indexer: lock held by another replica")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("indexer: tick failed; retrying next poll")
            await sleep(settings.indexer_poll_seconds)
    finally:
        runner.close()
        logger.info("indexer: stopped")
