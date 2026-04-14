"""
Generic async base repository.

All concrete repositories inherit from BaseRepository[ModelType] and receive
an AsyncSession from the caller.  Methods flush but do NOT commit — the
caller owns the transaction boundary.
"""

from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD operations for a SQLModel table class."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: object) -> Optional[ModelType]:
        """Fetch a single record by primary key.

        Args:
            db: Open async database session.
            id: Primary key value.

        Returns:
            The model instance or None if not found.
        """
        return await db.get(self.model, id)

    async def list(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Return a paginated list of records.

        Args:
            db: Open async database session.
            offset: Number of rows to skip.
            limit: Maximum rows to return.

        Returns:
            List of model instances.
        """
        stmt = select(self.model).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj: ModelType) -> ModelType:
        """Persist a new record (flush only — caller commits).

        Args:
            db: Open async database session.
            obj: Model instance to insert.

        Returns:
            The persisted model instance (with server-side defaults populated
            after flush).
        """
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, id: object) -> None:
        """Delete a record by primary key (flush only — caller commits).

        Args:
            db: Open async database session.
            id: Primary key value of the record to delete.
        """
        obj = await db.get(self.model, id)
        if obj is not None:
            db.delete(obj)
            await db.flush()
