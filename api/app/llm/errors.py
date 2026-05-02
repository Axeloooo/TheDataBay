"""Domain errors for LLM provider operations."""


class LLMError(Exception):
    """Base class for LLM domain errors."""


class LLMInputError(LLMError):
    """Raised when an LLM request is invalid before provider execution."""


class LLMProviderError(LLMError):
    """Raised when the underlying provider call fails."""


class LLMSummaryValidationError(LLMError):
    """Raised when a summary response cannot be validated as strict JSON."""
