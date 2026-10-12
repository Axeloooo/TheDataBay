"""LLM provider registry and factory."""

from ..errors import LLMProviderError
from ..service import LLMService
from ...config.settings import Settings

# Known provider names → (module path relative to this package, class name).
# Each provider's dependencies are imported on-demand so missing optional
# packages (e.g. langchain_openai) never break unrelated provider paths.
_REGISTRY: dict[str, tuple[str, str]] = {
    "ollama": (".ollama", "OllamaLLMService"),
    "openai": (".openai", "OpenAILLMService"),
}


def create_provider(settings: Settings) -> LLMService:
    """Instantiate the LLM provider configured by *LLM_PROVIDER*.

    Raises :exc:`LLMProviderError` for unknown provider names so callers get a
    clear error message instead of a silent fallback.

    Provider dependencies (e.g. ``langchain_openai``) are imported only when
    that provider is actually selected, so missing optional packages do not
    affect unrelated providers.
    """
    entry = _REGISTRY.get(settings.llm_provider)
    if entry is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise LLMProviderError(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
            f"Supported values: {supported}"
        )

    module_suffix, class_name = entry
    import importlib  # noqa: PLC0415

    try:
        module = importlib.import_module(module_suffix, package=__name__)
    except ImportError as exc:
        raise LLMProviderError(
            f"Missing dependencies for LLM provider '{settings.llm_provider}': {exc}"
        ) from exc

    factory = getattr(module, class_name)
    return factory.from_settings(settings)
