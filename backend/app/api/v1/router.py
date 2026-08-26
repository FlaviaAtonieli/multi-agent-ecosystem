from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    dashboard,
    health,
    orchestrations,
    requests,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(requests.router)
api_router.include_router(orchestrations.router)
api_router.include_router(admin.router)
