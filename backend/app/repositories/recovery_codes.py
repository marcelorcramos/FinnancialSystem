import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecoveryCode


async def replace_all(session: AsyncSession, user_id: uuid.UUID, hashes: list[str]) -> None:
    await session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))
    session.add_all(RecoveryCode(user_id=user_id, code_hash=h) for h in hashes)


async def delete_all(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))


async def use(session: AsyncSession, user_id: uuid.UUID, code_hash: str, now: datetime) -> bool:
    stmt = (
        select(RecoveryCode)
        .where(
            RecoveryCode.user_id == user_id,
            RecoveryCode.code_hash == code_hash,
            RecoveryCode.used_at.is_(None),
        )
        .with_for_update()
    )
    code = await session.scalar(stmt)
    if code is None:
        return False
    code.used_at = now
    return True


async def count_unused(session: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(
        RecoveryCode.user_id == user_id, RecoveryCode.used_at.is_(None)
    )
    return int(await session.scalar(stmt) or 0)
