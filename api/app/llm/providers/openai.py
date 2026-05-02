"""OpenAI-backed implementation of the generic LLM service."""

from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import ValidationError

from ...config.settings import Settings
from ..errors import LLMInputError, LLMProviderError, LLMSummaryValidationError
from ..schemas import EmbeddingBatchResult, EmbeddingResult, SummaryResult, TextSummary
from ..service import LLMService

DEFAULT_SUMMARY_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

_SUMMARY_SYSTEM_PROMPT = (
    "Summarize the provided text as strict JSON only. The JSON object must contain "
    'exactly these keys: "title" (string), "summary" (string), and '
    '"keywords" (array of strings). Do not include markdown or extra keys.'
)

class OpenAILLMService(LLMService):
    """LLM service that delegates summaries and embeddings to OpenAI."""

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
    def from_settings(cls, settings: Settings) -> "OpenAILLMService":
        """Build the OpenAI clients from application settings."""
        api_key_secret = getattr(settings, "openai_api_key", None)
        if api_key_secret is None:
            raise LLMProviderError("OPENAI_API_KEY must be set when LLM_PROVIDER is openai")
        api_key = api_key_secret.get_secret_value()

        summary_model = getattr(settings, "llm_chat_model", DEFAULT_SUMMARY_MODEL)
        embedding_model = getattr(settings, "llm_embedding_model", DEFAULT_EMBEDDING_MODEL)

        return cls(
            chat_client=ChatOpenAI(
                model=summary_model,
                api_key=api_key,
                model_kwargs={"response_format": {"type": "json_object"}},
            ),
            embeddings_client=OpenAIEmbeddings(
                model=embedding_model,
                api_key=api_key,
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
            "OpenAI returned malformed summary JSON after retry"
        ) from last_error

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
        except Exception as exc:
            raise LLMProviderError("OpenAI summary request failed") from exc

        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise LLMSummaryValidationError("OpenAI summary response was not text")
        return content


def _require_text(text: str) -> str:
    clean_text = text.strip()
    if not clean_text:
        raise LLMInputError("Text cannot be empty")
    return clean_text
