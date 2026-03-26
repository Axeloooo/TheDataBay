from datetime import datetime

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.services import dataset_key_repo


def test_upsert_and_get_dataset_key():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        record = dataset_key_repo.upsert_dataset_key(
            session=session,
            listing_id="123e4567-e89b-12d3-a456-426614174000",
            key_b64="key",
            nonce_b64="nonce",
            dataset_url="ipfs://data",
            dataset_hash="0xhash",
        )

        assert record.listing_id == "123e4567-e89b-12d3-a456-426614174000"

        fetched = dataset_key_repo.get_dataset_key(
            session, "123e4567-e89b-12d3-a456-426614174000"
        )
        assert fetched is not None
        assert fetched.dataset_url == "ipfs://data"


def test_upsert_dataset_key_updates_existing_record(monkeypatch):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    class FakeDateTime:
        current = datetime(2024, 1, 1)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(dataset_key_repo, "datetime", FakeDateTime)

    with Session(engine) as session:
        created = dataset_key_repo.upsert_dataset_key(
            session=session,
            listing_id="123e4567-e89b-12d3-a456-426614174000",
            key_b64="key",
            nonce_b64="nonce",
            dataset_url="ipfs://data",
            dataset_hash="0xhash",
        )

        FakeDateTime.current = datetime(2024, 1, 2)

        updated = dataset_key_repo.upsert_dataset_key(
            session=session,
            listing_id="123e4567-e89b-12d3-a456-426614174000",
            key_b64="new-key",
            nonce_b64="new-nonce",
            dataset_url="ipfs://new-data",
            dataset_hash="0xnewhash",
        )

        assert updated.id == created.id
        assert updated.created_at == created.created_at
        assert updated.updated_at == datetime(2024, 1, 2)
        assert updated.key_b64 == "new-key"
        assert updated.nonce_b64 == "new-nonce"
        assert updated.dataset_url == "ipfs://new-data"
        assert updated.dataset_hash == "0xnewhash"
        assert (
            dataset_key_repo.get_dataset_key(
                session, "123e4567-e89b-12d3-a456-426614174000"
            ).dataset_hash
            == "0xnewhash"
        )
