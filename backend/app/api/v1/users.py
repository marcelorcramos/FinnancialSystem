from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.user import PasswordChange, UserRead, UserUpdate
from app.services import auth

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me")
async def update_me(data: UserUpdate, user: CurrentUser, session: SessionDep) -> UserRead:
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, field, value)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: PasswordChange, user: CurrentUser, session: SessionDep) -> None:
    await auth.change_password(session, user, data.current_password, data.new_password)
