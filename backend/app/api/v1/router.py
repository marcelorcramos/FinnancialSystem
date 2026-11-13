from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    attachments,
    auth,
    entries,
    exports,
    goals,
    google,
    labels,
    limits,
    months,
    reports,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(google.router)
api_router.include_router(users.router)
api_router.include_router(labels.router)
api_router.include_router(months.router)
api_router.include_router(entries.router)
api_router.include_router(reports.router)
api_router.include_router(limits.router)
api_router.include_router(alerts.router)
api_router.include_router(goals.router)
api_router.include_router(attachments.router)
api_router.include_router(exports.router)
