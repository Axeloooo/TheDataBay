from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.services import dataset_key_repo


def test_upsert_and_get_dataset_key(monkeypatch):
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
