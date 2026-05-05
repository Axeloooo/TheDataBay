"""OpenAI-backed implementation of the generic LLM service."""

from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ...config.settings import Settings
from ..errors import LLMInputError, LLMProviderError, LLMResponseValidationError
from ..schemas import (
    ColumnExpansionResult,
    EmbeddingBatchResult,
    EmbeddingResult,
)
from ..service import LLMService

DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

_COLUMN_EXPANSION_SYSTEM_PROMPT = (
    "You are a data analyst. Given CSV column names and sample rows, return a strict JSON object "
    "mapping each column name to a plain-English description of what that column represents. "
    "Include units or value encodings where evident (e.g. '0=female, 1=male'). "
    "Return only the JSON object with no markdown or extra keys."
)

class OpenAILLMService(LLMService):
    """LLM service that delegates column expansion and embeddings to OpenAI."""

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
    def from_settings(cls, settings: Settings) -> "OpenAILLMService":
        """Build the OpenAI clients from application settings."""
        api_key_secret = getattr(settings, "openai_api_key", None)
        if api_key_secret is None:
            raise LLMProviderError("OPENAI_API_KEY must be set when LLM_PROVIDER is openai")
        api_key = api_key_secret.get_secret_value()

        chat_model = getattr(settings, "llm_chat_model", DEFAULT_CHAT_MODEL)
        embedding_model = getattr(settings, "llm_embedding_model", DEFAULT_EMBEDDING_MODEL)

        return cls(
            chat_client=ChatOpenAI(
                model=chat_model,
                api_key=api_key,
                model_kwargs={"response_format": {"type": "json_object"}},
            ),
            embeddings_client=OpenAIEmbeddings(
                model=embedding_model,
                api_key=api_key,
            ),
            chat_model=chat_model,
            embedding_model=embedding_model,
        )

    async def expand_column_names(
        self,
        column_names: list[str],
        sample_rows: list[list[str]],
    ) -> ColumnExpansionResult:
        """Return plain-English descriptions for CSV column names using gpt-4o-mini."""
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
            except Exception as exc:
                last_error = exc

        # Fallback: return raw column names as their own descriptions
        return ColumnExpansionResult(columns={col: col for col in column_names})

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        clean_text = _require_text(text)
        try:
            vector = await self._embeddings_client.aembed_query(clean_text)
        except Exception as exc:
            raise LLMProviderError("OpenAI embedding request failed") from exc

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
        except Exception as exc:
            raise LLMProviderError("OpenAI batch embedding request failed") from exc

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
