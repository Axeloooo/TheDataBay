"""FastAPI dependencies for LLM services."""

from fastapi import Depends

from ..config.settings import Settings, get_settings
from .services.ollama_provider import OllamaLLMService
from .services.openai_provider import OpenAILLMService
from .service import LLMService


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    """Return the configured LLM provider."""
    if settings.llm_provider == "openai":
        return OpenAILLMService.from_settings(settings)
    return OllamaLLMService.from_settings(settings)
