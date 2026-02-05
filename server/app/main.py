"""
BridgeMart FastAPI backend service.
"""

from contextlib import asynccontextmanager
from typing import Any, Generator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from .config.settings import Settings, get_settings
from .routers import health_router, llm_router, ai_router
from .database.engine import create_db_and_tables

settings: Settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Generator[None, Any, None]:
    """Lifespan event handler for FastAPI app.

    Args:
        app (FastAPI): FastAPI application instance

    Yields:
        Generator[None, Any, None]: Generator that yields None
    """
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for BridgeMart AI workloads and API orchestration",
    docs_url="/docs",
    redoc_url="/redoc",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router.router)
app.include_router(llm_router.router)
app.include_router(ai_router.router)


@app.get("/")
def read_root(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Get basic service info.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        dict: Service information
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "links": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "config": "/config",
        },
    }
