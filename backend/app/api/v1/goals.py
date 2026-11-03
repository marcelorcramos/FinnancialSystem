import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.goal import GoalCreate, GoalList, GoalRead, GoalUpdate
from app.services import goals

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("")
async def list_goals(user: CurrentUser, session: SessionDep) -> GoalList:
    """Active goals with their pace, and the history of completed ones."""
    return await goals.list_goals(session, user)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_goal(data: GoalCreate, user: CurrentUser, session: SessionDep) -> GoalRead:
    return await goals.get_view(session, user, await goals.create(session, user, data))


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: uuid.UUID, data: GoalUpdate, user: CurrentUser, session: SessionDep
) -> GoalRead:
    return await goals.get_view(session, user, await goals.update(session, user, goal_id, data))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await goals.delete(session, user, goal_id)


@router.post("/{goal_id}/restore")
async def restore_goal(goal_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> GoalRead:
    return await goals.get_view(session, user, await goals.restore(session, user, goal_id))
