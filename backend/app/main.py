from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import get_session_factory, settings
from app.routes import router, seed_sources


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.database_url:
        with get_session_factory()() as session:
            seed_sources(session)
    yield

app = FastAPI(
    title="EHR/FHIR Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [settings.frontend_url.rstrip("/")]
        if settings.frontend_url
        else []
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
