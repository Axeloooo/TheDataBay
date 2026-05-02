"""Ollama-backed implementation of the generic LLM service."""

from typing import Any
from urllib.parse import urlparse

from langchain_ollama import ChatOllama, OllamaEmbeddings
from ollama import ResponseError
from pydantic import ValidationError

from ...config.settings import Settings
from ..errors import LLMInputError, LLMProviderError, LLMSummaryValidationError
from ..schemas import EmbeddingBatchResult, EmbeddingResult, SummaryResult, TextSummary
from ..service import LLMService

DEFAULT_SUMMARY_MODEL = "deepseek-v4-flash"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

_SUMMARY_SYSTEM_PROMPT = (
    "Summarize the provided text as strict JSON only. The JSON object must contain "
    'exactly these keys: "title" (string), "summary" (string), and '
    '"keywords" (array of strings). Do not include markdown or extra keys.'
)


class OllamaLLMService(LLMService):
    """LLM service that delegates summaries and embeddings to Ollama."""

    def __init__(
        self,
        *,
        chat_client: Any,
        embeddings_client: Any,
        summary_model: str,
        embedding_model: str,
    ) -> None:
        self._chat_client = chat_client
        self._embeddings_client = embeddings_client
        self.summary_model = summary_model
        self.embedding_model = embedding_model

    @property
    def embeddings_client(self) -> Any:
        """Return the provider-owned LangChain embeddings client for vector stores."""
        return self._embeddings_client

    @classmethod
    def from_settings(cls, settings: Settings) -> "OllamaLLMService":
        """Build the Ollama clients from application settings."""
        base_url = getattr(settings, "llm_base_url", DEFAULT_OLLAMA_BASE_URL)
        embedding_base_url = getattr(settings, "llm_embedding_base_url", DEFAULT_OLLAMA_BASE_URL)
        summary_model = getattr(settings, "llm_chat_model", DEFAULT_SUMMARY_MODEL)
        embedding_model = getattr(settings, "llm_embedding_model", DEFAULT_EMBEDDING_MODEL)
        client_kwargs = _client_kwargs(settings)
        _validate_auth_configuration(base_url, client_kwargs)
        return cls(
            chat_client=ChatOllama(
                model=summary_model,
                base_url=base_url,
                format="json",
                client_kwargs=client_kwargs,
                async_client_kwargs=client_kwargs,
            ),
            embeddings_client=OllamaEmbeddings(
                model=embedding_model,
                base_url=embedding_base_url,
                client_kwargs={},
                async_client_kwargs={},
            ),
            summary_model=summary_model,
            embedding_model=embedding_model,
        )

    async def summarize_text(self, text: str) -> SummaryResult:
        """Generate and validate a strict JSON summary, retrying malformed JSON once."""
        clean_text = _require_text(text)
        last_error: Exception | None = None

        for attempt in range(2):
            raw_content = await self._invoke_summary(clean_text, retry=attempt > 0)
            try:
                summary = TextSummary.model_validate_json(raw_content)
                return SummaryResult(summary=summary, model=self.summary_model)
            except (ValidationError, ValueError) as exc:
                last_error = exc

        raise LLMSummaryValidationError(
            "Ollama returned malformed summary JSON after retry"
        ) from last_error

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        clean_text = _require_text(text)
        try:
            vector = await self._embeddings_client.aembed_query(clean_text)
        except ResponseError as exc:
            raise _provider_error_from_response(exc, "embedding") from exc
        except Exception as exc:
            raise LLMProviderError("Ollama embedding request failed") from exc

        return EmbeddingResult(
            vector=vector,
            model=self.embedding_model,
            dimension=len(vector),
        )

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        """Embed multiple text strings."""
        clean_texts = [_require_text(text) for text in texts]
        try:
            vectors = await self._embeddings_client.aembed_documents(clean_texts)
        except ResponseError as exc:
            raise _provider_error_from_response(exc, "batch embedding") from exc
        except Exception as exc:
            raise LLMProviderError("Ollama batch embedding request failed") from exc

        return EmbeddingBatchResult(
            embeddings=[
                EmbeddingResult(
                    vector=vector,
                    model=self.embedding_model,
                    dimension=len(vector),
                )
                for vector in vectors
            ],
            model=self.embedding_model,
        )

    async def _invoke_summary(self, text: str, *, retry: bool) -> str:
        human_prompt = text
        if retry:
            human_prompt = (
                "Your previous response was not valid for the required schema. "
                "Return only the strict JSON object for this text:\n\n"
                f"{text}"
            )

        try:
            response = await self._chat_client.ainvoke(
                [
                    ("system", _SUMMARY_SYSTEM_PROMPT),
                    ("human", human_prompt),
                ]
            )
        except ResponseError as exc:
            raise _provider_error_from_response(exc, "summary") from exc
        except Exception as exc:
            raise LLMProviderError("Ollama summary request failed") from exc

        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise LLMSummaryValidationError("Ollama summary response was not text")
        return content


def _require_text(text: str) -> str:
    clean_text = text.strip()
    if not clean_text:
        raise LLMInputError("Text cannot be empty")
    return clean_text


def _client_kwargs(settings: Settings) -> dict[str, dict[str, str]]:
    api_key = getattr(settings, "ollama_api_key", None)
    if api_key is None:
        return {}
    secret = api_key.get_secret_value().strip()
    if not secret:
        return {}
    return {"headers": {"Authorization": f"Bearer {secret}"}}


def _validate_auth_configuration(
    base_url: str,
    client_kwargs: dict[str, dict[str, str]],
) -> None:
    if client_kwargs:
        return
    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""
    if hostname in {
        "",
        "localhost",
        "127.0.0.1",
        "::1",
        "host.docker.internal",
        "ollama",
        "ollama-svc",
    }:
        return
    if hostname.endswith(".svc") or hostname.endswith(".svc.cluster.local"):
        return
    raise LLMProviderError(
        "OLLAMA_API_KEY must be set when LLM_BASE_URL points to a hosted LLM endpoint"
    )


def _provider_error_from_response(exc: ResponseError, operation: str) -> LLMProviderError:
    status_code = getattr(exc, "status_code", None)
    if status_code == 401:
        return LLMProviderError(
            f"Ollama {operation} request was unauthorized; verify OLLAMA_API_KEY is set "
            "in the backend pod and valid for LLM_BASE_URL"
        )
    return LLMProviderError(f"Ollama {operation} request failed")
