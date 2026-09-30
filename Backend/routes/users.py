from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from core.deps import CurrentUser, DbSession
from models.user import User
from schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser):
    return current_user


@router.get("/search", response_model=UserRead)
def search_user(
    db: DbSession,
    user_id: int | None = Query(default=None),
    email: str | None = Query(default=None),
):
    if user_id is None and email is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "At least one search parameter is required"
        )

    if user_id is not None:
        user = db.get(User, user_id)
    else:
        user = db.scalar(select(User).where(User.email == email.lower().strip()))

    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    return user


@router.get("", response_model=list[UserRead])
def list_users(
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    users = db.scalars(select(User).offset(skip).limit(limit)).all()
    return users


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user