"""Ollama-backed implementation of the generic LLM service."""

from typing import Any
from urllib.parse import urlparse

from langchain_ollama import ChatOllama, OllamaEmbeddings
from ollama import ResponseError

from ...config.settings import Settings
from ..errors import LLMInputError, LLMProviderError, LLMResponseValidationError
from ..schemas import (
    ColumnExpansionResult,
    EmbeddingBatchResult,
    EmbeddingResult,
)
from ..service import LLMService

DEFAULT_CHAT_MODEL = "deepseek-v4-flash"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

_COLUMN_EXPANSION_SYSTEM_PROMPT = (
    "You are a data analyst. Given CSV column names and sample rows, return a strict JSON object "
    "mapping each column name to a plain-English description of what that column represents. "
    "Include units or value encodings where evident (e.g. '0=female, 1=male'). "
    "Return only the JSON object with no markdown or extra keys."
)


class OllamaLLMService(LLMService):
    """LLM service that delegates column expansion and embeddings to Ollama."""

    def __init__(
        self,
        *,
        chat_client: Any,
        embeddings_client: Any,
        chat_model: str,
        embedding_model: str,
    ) -> None:
        self._chat_client = chat_client
        self._embeddings_client = embeddings_client
        self.chat_model = chat_model
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
                model=chat_model,
                base_url=base_url,
                format="json",
                client_kwargs=client_kwargs,
                async_client_kwargs=client_kwargs,
            ),
            embeddings_client=OllamaEmbeddings(
                model=embedding_model,
                base_url=embedding_base_url,
                client_kwargs=client_kwargs,
                async_client_kwargs=client_kwargs,
            ),
            chat_model=chat_model,
            embedding_model=embedding_model,
        )

    async def expand_column_names(
        self,
        column_names: list[str],
        sample_rows: list[list[str]],
    ) -> ColumnExpansionResult:
        """Return plain-English descriptions for CSV column names."""
        sample_lines = "\n".join(
            ", ".join(f"{col}: {val}" for col, val in zip(column_names, row))
            for row in sample_rows
        )
        human_prompt = (
            f"Column names: {', '.join(column_names)}\n"
            f"Sample rows:\n{sample_lines}"
        )
        last_error: Exception | None = None
        for attempt in range(2):
            if attempt > 0:
                human_prompt = (
                    "Your previous response was not valid JSON. "
                    "Return only the strict JSON object mapping column names to descriptions:\n\n"
                    + human_prompt
                )
            try:
                response = await self._chat_client.ainvoke(
                    [
                        ("system", _COLUMN_EXPANSION_SYSTEM_PROMPT),
                        ("human", human_prompt),
                    ]
                )
                content = getattr(response, "content", response)
                if not isinstance(content, str):
                    raise LLMResponseValidationError("Column expansion response was not text")
                import json
                raw = json.loads(content)
                if not isinstance(raw, dict):
                    raise ValueError("Expected a JSON object")
                return ColumnExpansionResult(
                    columns={str(k): str(v) for k, v in raw.items()}
                )
            except ResponseError as exc:
                last_error = _provider_error_from_response(exc, "column expansion")
            except Exception as exc:
                last_error = exc

        # Fallback: return raw column names as their own descriptions
        return ColumnExpansionResult(columns={col: col for col in column_names})

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
    return LLMProviderError(f"Ollama {operation} request failed (status {status_code})")
