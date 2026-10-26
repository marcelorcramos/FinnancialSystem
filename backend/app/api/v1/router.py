from fastapi import APIRouter

from app.api.v1 import auth, entries, labels, months, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(labels.router)
api_router.include_router(months.router)
api_router.include_router(entries.router)
