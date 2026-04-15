"""
Repository for dataset key persistence.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from ..models.dataset_key import DatasetKey


def upsert_dataset_key(
    session: Session,
    listing_id: str,
    key_b64: str,
    nonce_b64: str,
    dataset_url: str,
    dataset_hash: str,
) -> DatasetKey:
    """Insert or update dataset key record.

    Args:
        session (Session): Database session
        listing_id (str): Listing ID (UUID)
        key_b64 (str): Base64-encoded encryption key
        nonce_b64 (str): Base64-encoded nonce
        dataset_url (str): URL of the dataset
        dataset_hash (str): Hash of the dataset

    Returns:
        DatasetKey: Updated or created DatasetKey record
    """

    statement = select(DatasetKey).where(DatasetKey.listing_id == listing_id)
    existing = session.exec(statement).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.key_b64 = key_b64
        existing.nonce_b64 = nonce_b64
        existing.dataset_url = dataset_url
        existing.dataset_hash = dataset_hash
        existing.updated_at = now
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    record = DatasetKey(
        listing_id=listing_id,
        key_b64=key_b64,
        nonce_b64=nonce_b64,
        dataset_url=dataset_url,
        dataset_hash=dataset_hash,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


async def async_upsert_dataset_key(
    db: AsyncSession,
    listing_id: str,
    key_b64: str,
    nonce_b64: str,
    dataset_url: str,
    dataset_hash: str,
) -> DatasetKey:
    """Insert or update a DatasetKey row using an async session.

    Flushes but does NOT commit — the caller owns the transaction.

    Args:
        db (AsyncSession): Open async database session.
        listing_id (str): Listing ID (UUID string).
        key_b64 (str): Base64-encoded encryption key.
        nonce_b64 (str): Base64-encoded nonce.
        dataset_url (str): URL of the encrypted dataset on IPFS.
        dataset_hash (str): Content hash of the encrypted dataset.

    Returns:
        DatasetKey: The upserted record.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(DatasetKey)
        .values(
            listing_id=listing_id,
            key_b64=key_b64,
            nonce_b64=nonce_b64,
            dataset_url=dataset_url,
            dataset_hash=dataset_hash,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["listing_id"],
            set_={
                "key_b64": key_b64,
                "nonce_b64": nonce_b64,
                "dataset_url": dataset_url,
                "dataset_hash": dataset_hash,
                "updated_at": now,
            },
        )
    )
    await db.execute(stmt)
    await db.flush()
    result = await db.execute(
        select(DatasetKey).where(DatasetKey.listing_id == listing_id)
    )
    return result.scalar_one()


def get_dataset_key(session: Session, listing_id: str) -> Optional[DatasetKey]:
    """Retrieve dataset key record by listing ID.

    Args:
        session (Session): Database session
        listing_id (str): Listing ID (UUID)

    Returns:
        Optional[DatasetKey]: DatasetKey record or None if not found
    """

    statement = select(DatasetKey).where(DatasetKey.listing_id == listing_id)
    return session.exec(statement).first()
