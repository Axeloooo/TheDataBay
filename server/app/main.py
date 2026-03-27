"""
BridgeMart FastAPI backend service.
"""

from contextlib import asynccontextmanager
import logging
import os
import time
import uuid
from typing import Any
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from .config.settings import Settings, get_settings
from .routers import (
    health_router,
    llm_router,
    ai_router,
    datasets_router,
    contract_router,
)
from .routers import agent_router
from .database.engine import create_db_and_tables

settings: Settings = get_settings()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI app.

    Args:
        app (FastAPI): FastAPI application instance

    Yields:
        Generator[None, Any, None]: Generator that yields None
    """
    create_db_and_tables()
    if (
        os.getenv("ENVIRONMENT") == "development"
        and os.getenv("SEED_AGENTS", "").lower() == "true"
    ):
        from .database.engine import get_engine
        from sqlmodel import Session as SQLSession
        from .seeds.agent_seeds import seed_agents

        engine = get_engine()
        with SQLSession(engine) as session:
            seed_agents(session)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for BridgeMart AI workloads and API orchestration",
    docs_url="/docs",
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
app.include_router(datasets_router.router)
app.include_router(contract_router.router)
app.include_router(agent_router.router)
app.include_router(agent_router.purchase_router)
app.include_router(agent_router.rec_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Attach request id and log request/response lifecycle."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started = time.perf_counter()
    base_logger = logging.LoggerAdapter(logger, {"request_id": request_id})
    base_logger.info(
        "request.start method=%s path=%s", request.method, request.url.path
    )

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        base_logger.exception(
            "request.error method=%s path=%s elapsed_ms=%s",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.headers["x-request-id"] = request_id
    base_logger.info(
        "request.done method=%s path=%s status=%s elapsed_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


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
            "health": "/health",
            "config": "/config",
        },
    }
