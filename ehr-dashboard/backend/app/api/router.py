from fastapi import APIRouter

from app.api import ehr, patients

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(ehr.router, tags=["ehr"])
api_router.include_router(patients.router, tags=["patients"])
