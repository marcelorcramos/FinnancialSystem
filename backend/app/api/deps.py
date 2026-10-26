from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User
from app.repositories import users

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# OAuth2 password flow só para o botão Authorize do Swagger (/docs) pedir email e password.
# A app usa POST /auth/login (JSON); ambos devolvem o mesmo access token.
_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_current_user(
    session: SessionDep, token: Annotated[str | None, Depends(_oauth2)]
) -> User:
    user_id = decode_access_token(token) if token else None
    user = await users.get_active_by_id(session, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
