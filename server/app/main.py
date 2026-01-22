"""
BridgeMart FastAPI backend service.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from .config.settings import Settings, get_settings
from .routers import health_router, llm_router, ai_router

settings: Settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for BridgeMart AI workloads and API orchestration",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/config")
def read_config(settings: Settings = Depends(get_settings)):
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
    }
