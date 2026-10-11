"""Background runner tests: advisory lock, loop resilience, app lifespan.

There is no Postgres in the unit-test environment, so the advisory lock is
exercised against SQLite with pg_try_advisory_lock / pg_advisory_unlock
registered as functions that mimic Postgres session-level semantics: a lock
belongs to the DB connection that took it and is released when that
connection closes.
"""

import asyncio
import logging
import threading
import uuid
from collections.abc import Generator
from typing import Any

import pytest
import requests
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, select

from app.indexer.models import IndexedListing
from app.indexer.runner import ADVISORY_LOCK_KEY, IndexerRunner, run_forever

from .conftest import make_settings
from .fakes import FakeChain, contract_for


@pytest.fixture
def pg_like_engine() -> Generator[Engine, None, None]:
    holders: dict[int, int] = {}
    name = f"indexer_lock_{uuid.uuid4().hex}"
    eng = create_engine(
        f"sqlite:///file:{name}?mode=memory&cache=shared&uri=true",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _register(dbapi_conn, _record):
        owner = id(dbapi_conn)

        def try_lock(key: int) -> int:
            if holders.get(key, owner) != owner:
                return 0
            holders[key] = owner
            return 1

        def unlock(key: int) -> int:
            if holders.get(key) == owner:
                del holders[key]
                return 1
            return 0

        dbapi_conn.create_function("pg_try_advisory_lock", 1, try_lock)
        dbapi_conn.create_function("pg_advisory_unlock", 1, unlock)

    @event.listens_for(eng, "close")
    def _release(dbapi_conn, _record):
        for key, owner in list(holders.items()):
            if owner == id(dbapi_conn):
                del holders[key]

    keeper = eng.raw_connection()  # keeps the shared in-memory DB alive
    SQLModel.metadata.create_all(eng)
    try:
        yield eng
    finally:
        keeper.close()
        eng.dispose()


def _chain() -> FakeChain:
    chain = FakeChain(head=200)
    chain.add_listing(1, block=101)
    return chain


def test_lock_key_fits_postgres_bigint():
    assert -(2**63) <= ADVISORY_LOCK_KEY < 2**63


def test_second_runner_does_not_index_while_first_holds_the_lock(pg_like_engine):
    settings = make_settings()
    chain_a, chain_b = _chain(), _chain()
    first = IndexerRunner(settings, engine=pg_like_engine, contract_factory=lambda: contract_for(chain_a))
    second = IndexerRunner(settings, engine=pg_like_engine, contract_factory=lambda: contract_for(chain_b))
    try:
        assert first.tick() == 1
        assert second.tick() is None
        assert chain_b.get_logs_calls == []

        chain_a.head = 210
        assert first.tick() == 0  # still holds the lock across ticks
    finally:
        first.close()
        second.close()


def test_other_runner_takes_over_after_lock_holder_closes(pg_like_engine):
    settings = make_settings()
    chain_b = _chain()
    first = IndexerRunner(settings, engine=pg_like_engine, contract_factory=lambda: contract_for(_chain()))
    second = IndexerRunner(settings, engine=pg_like_engine, contract_factory=lambda: contract_for(chain_b))
    try:
        first.tick()
        first.close()

        assert second.tick() == 0  # rows already written by the first runner
        assert chain_b.get_logs_calls == []  # cursor is already at head - confirmations
        chain_b.head = 220
        second.tick()
        assert chain_b.get_logs_calls != []
    finally:
        second.close()

    with Session(pg_like_engine) as session:
        assert len(session.exec(select(IndexedListing)).all()) == 1


def test_runner_retakes_the_lock_after_its_connection_drops(pg_like_engine):
    settings = make_settings()
    chain = _chain()
    first = IndexerRunner(settings, engine=pg_like_engine, contract_factory=lambda: contract_for(chain))
    try:
        first.tick()
        first._lock_connection.invalidate()  # e.g. Postgres restarted

        chain.head = 230
        assert first.tick() is not None
    finally:
        first.close()


def test_rpc_failure_resets_the_cached_contract(pg_like_engine):
    settings = make_settings()
    calls = {"n": 0}
    chain = _chain()

    def factory():
        calls["n"] += 1
        return contract_for(chain)

    runner = IndexerRunner(settings, engine=pg_like_engine, contract_factory=factory)
    try:
        runner.tick()
        chain.fail_block_times = {205}
        chain.add_purchase(next(iter(chain.items)), block=205)
        chain.head = 220
        with pytest.raises(ConnectionError):
            runner.tick()
        chain.fail_block_times = set()
        runner.tick()
    finally:
        runner.close()

    assert calls["n"] == 2


class _FakeRunner:
    def __init__(self, results):
        self.results = list(results)
        self.ticks = 0
        self.closed = False

    def tick(self):
        self.ticks += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


def _sleeper(stop_after: int) -> tuple[list[float], Any]:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == stop_after:
            raise asyncio.CancelledError

    return sleeps, fake_sleep


async def test_run_forever_survives_tick_errors_and_closes_on_cancel():
    fake = _FakeRunner([RuntimeError("rpc down"), None, 3, 0])
    sleeps, fake_sleep = _sleeper(4)

    with pytest.raises(asyncio.CancelledError):
        await run_forever(make_settings(INDEXER_POLL_SECONDS=7), runner=fake, sleep=fake_sleep)

    assert fake.ticks == 4
    assert sleeps == [14, 7, 7, 7]
    assert fake.closed is True


async def test_consecutive_errors_back_off_exponentially_up_to_a_cap_and_reset():
    fake = _FakeRunner([RuntimeError("down")] * 6 + [0, RuntimeError("down")])
    sleeps, fake_sleep = _sleeper(8)

    with pytest.raises(asyncio.CancelledError):
        await run_forever(make_settings(INDEXER_POLL_SECONDS=5), runner=fake, sleep=fake_sleep)

    assert sleeps == [10, 20, 40, 60, 60, 60, 5, 10]


async def test_tick_errors_are_logged_without_the_rpc_url_secret(caplog):
    secret_url = "https://rpc.example.com/v2/SECRETKEY123"
    errors = [
        requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='rpc.example.com', port=443): Max retries "
            "exceeded with url: /v2/SECRETKEY123 (Caused by NewConnectionError)"
        ),
        requests.exceptions.HTTPError(f"401 Client Error: Unauthorized for url: {secret_url}"),
    ]
    fake = _FakeRunner(errors)
    _, fake_sleep = _sleeper(2)

    with caplog.at_level(logging.INFO, logger="app.indexer.runner"):
        with pytest.raises(asyncio.CancelledError):
            await run_forever(make_settings(RPC_URL=secret_url), runner=fake, sleep=fake_sleep)

    assert "SECRETKEY123" not in caplog.text
    assert "ConnectionError" in caplog.text
    assert "HTTPError" in caplog.text
    assert "https://rpc.example.com" in caplog.text


async def test_startup_warns_when_start_block_skips_history(caplog):
    _, fake_sleep = _sleeper(1)
    with caplog.at_level(logging.WARNING, logger="app.indexer.runner"):
        with pytest.raises(asyncio.CancelledError):
            await run_forever(
                make_settings(INDEXER_START_BLOCK=500), runner=_FakeRunner([0]), sleep=fake_sleep
            )
    assert any("500" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)

    caplog.clear()
    _, fake_sleep = _sleeper(1)
    with caplog.at_level(logging.WARNING, logger="app.indexer.runner"):
        with pytest.raises(asyncio.CancelledError):
            await run_forever(
                make_settings(INDEXER_START_BLOCK=0), runner=_FakeRunner([0]), sleep=fake_sleep
            )
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def _blocking_runner(engine):
    chain = FakeChain(head=200)
    chain.add_listing(1, block=101)
    entered, release = threading.Event(), threading.Event()

    def block(_flt):
        entered.set()
        release.wait(5)

    runner = IndexerRunner(make_settings(), engine=engine, contract_factory=lambda: contract_for(chain))
    runner.tick()  # take the lock and catch up
    chain.head = 400
    chain.get_logs_calls.clear()
    chain.on_get_logs = block
    worker = threading.Thread(target=runner.tick)
    worker.start()
    assert entered.wait(5)
    return runner, chain, worker, release


def test_close_waits_for_the_running_tick_then_releases_the_lock(pg_like_engine):
    runner, chain, worker, release = _blocking_runner(pg_like_engine)

    closer = threading.Thread(target=runner.close)
    closer.start()
    closer.join(0.2)
    assert closer.is_alive()  # waiting: the tick is still using the connection
    assert runner._lock_connection is not None

    release.set()
    worker.join(5)
    closer.join(5)
    assert not closer.is_alive()
    assert runner._lock_connection is None
    assert len(chain.get_logs_calls) == 1  # stop flag ended the backfill after one chunk


def test_close_gives_up_after_timeout_without_touching_the_connection(pg_like_engine):
    runner, _chain, worker, release = _blocking_runner(pg_like_engine)
    try:
        runner.close(timeout=0.1)
        assert runner._lock_connection is not None
    finally:
        release.set()
        worker.join(5)
        runner.close()

