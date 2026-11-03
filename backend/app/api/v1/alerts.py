import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.deps import CurrentUser, SessionDep
from app.core import notifications
from app.schemas.alert import AlertRead
from app.services import alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])
log = structlog.get_logger(__name__)

HEARTBEAT_SECONDS = 15.0


async def alert_events(
    redis: Redis | None,
    user_id: uuid.UUID,
    is_disconnected: Callable[[], Awaitable[bool]],
    heartbeat: float = HEARTBEAT_SECONDS,
) -> AsyncIterator[str]:
    """SSE lines: the user's alerts as they are published, a comment line when idle."""
    yield ": connected\n\n"
    pubsub = None
    try:
        if redis is not None:
            pubsub = redis.pubsub()
            await pubsub.subscribe(notifications.alerts_channel(user_id))
    except RedisError as error:
        log.warning("alerts.stream_unavailable", error=str(error))
        pubsub = None
    try:
        while not await is_disconnected():
            message = None
            if pubsub is not None:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=heartbeat
                )
            else:
                await asyncio.sleep(heartbeat)
            if message is None:
                yield ": ping\n\n"
                continue
            yield f"event: alert\ndata: {json.dumps(json.loads(message['data']))}\n\n"
    finally:
        if pubsub is not None:
            await pubsub.aclose()  # type: ignore[no-untyped-call]


@router.get("")
async def list_alerts(
    user: CurrentUser, session: SessionDep, unseen: bool = False
) -> list[AlertRead]:
    """The 50 newest alerts (or only the unseen ones)."""
    return await alerts.list_alerts(session, user, unseen=unseen)


@router.post("/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_seen(user: CurrentUser, session: SessionDep) -> None:
    await alerts.mark_seen(session, user)


@router.post("/{alert_id}/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_seen(alert_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await alerts.mark_seen(session, user, alert_id)


@router.get("/stream")
async def stream_alerts(
    request: Request,
    user: CurrentUser,
    session: SessionDep,
    redis: Annotated[Redis | None, Depends(notifications.get_subscriber)],
) -> StreamingResponse:
    """Server-Sent Events: `event: alert` with an AlertRead each time a limit is reached.

    Send the access token as a Bearer header (read the stream with fetch). A comment
    line every 15 s keeps proxies from closing an idle connection.
    """
    user_id = user.id
    # The stream may stay open for hours: give the database connection back now.
    await session.close()

    return StreamingResponse(
        alert_events(redis, user_id, request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
