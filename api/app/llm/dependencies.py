"""FastAPI dependencies for LLM services."""

from fastapi import Depends

from ..config.settings import Settings, get_settings
from .providers import create_provider
from .service import LLMService


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    """Return the configured LLM provider."""
    return create_provider(settings)
