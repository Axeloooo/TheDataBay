"""LLM provider registry and factory."""

from typing import Callable

from ..errors import LLMProviderError
from ..service import LLMService
from ...config.settings import Settings

# Registry maps LLM_PROVIDER values to their from_settings constructors.
# Add a new entry here to support additional providers.
_REGISTRY: dict[str, Callable[[Settings], LLMService]] = {}


def _register() -> None:
    """Populate the registry lazily to avoid circular imports at module load."""
    from .ollama import OllamaLLMService  # noqa: PLC0415
    from .openai import OpenAILLMService  # noqa: PLC0415

    _REGISTRY["ollama"] = OllamaLLMService.from_settings
    _REGISTRY["openai"] = OpenAILLMService.from_settings


def create_provider(settings: Settings) -> LLMService:
    """Instantiate the LLM provider configured by *LLM_PROVIDER*.

    Raises :exc:`LLMProviderError` for unknown provider names so callers get a
    clear error message instead of a silent fallback.
    """
    if not _REGISTRY:
        _register()

    factory = _REGISTRY.get(settings.llm_provider)
    if factory is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise LLMProviderError(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
            f"Supported values: {supported}"
        )
    return factory(settings)
