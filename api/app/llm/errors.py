"""Domain errors for LLM provider operations."""


class LLMError(Exception):
    """Base class for LLM domain errors."""


class LLMInputError(LLMError):
    """Raised when an LLM request is invalid before provider execution."""


class LLMProviderError(LLMError):
    """Raised when the underlying provider call fails."""


class LLMResponseValidationError(LLMError):
    """Raised when an LLM response cannot be validated as the expected format."""
