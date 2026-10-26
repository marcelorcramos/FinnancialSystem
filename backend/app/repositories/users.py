import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_active_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
    return await session.scalar(stmt)


async def get_active_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    return await session.scalar(stmt)
