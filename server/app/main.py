"""
BridgeMart FastAPI backend service.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import health_router, llm_router, ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler."""
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📍 Environment: {settings.environment}")
    print(f"🤖 Ollama host: {settings.ollama_host}")

    yield

    # Shutdown
    print(f"👋 Shutting down {settings.app_name}")


# Initialize FastAPI app with metadata and lifespan
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for BridgeMart AI workloads and API orchestration",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_router.router)
app.include_router(llm_router.router)
app.include_router(ai_router.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
