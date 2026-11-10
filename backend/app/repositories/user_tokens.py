import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TokenPurpose
from app.models import UserToken


async def get_usable_for_update(
    session: AsyncSession, token_hash: str, purpose: TokenPurpose, now: datetime
) -> UserToken | None:
    stmt = (
        select(UserToken)
        .where(
            UserToken.token_hash == token_hash,
            UserToken.purpose == purpose,
            UserToken.used_at.is_(None),
            UserToken.expires_at > now,
        )
        .with_for_update()
    )
    return await session.scalar(stmt)


async def use_all(
    session: AsyncSession, user_id: uuid.UUID, purpose: TokenPurpose, now: datetime
) -> None:
    """Spend every open token of this purpose (a new link replaces the old ones)."""
    await session.execute(
        update(UserToken)
        .where(
            UserToken.user_id == user_id,
            UserToken.purpose == purpose,
            UserToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
