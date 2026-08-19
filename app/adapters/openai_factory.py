from dataclasses import dataclass

from app.adapters.openai_client import create_openai_client
from app.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.adapters.openai_llm import OpenAILLMAdapter
from app.config.settings import Settings


@dataclass(frozen=True)
class OpenAIProviderAdapters:
    llm: OpenAILLMAdapter
    embeddings: OpenAIEmbeddingAdapter


def build_openai_adapters(settings: Settings) -> OpenAIProviderAdapters:
    client = create_openai_client(
        settings.openai_api_key,
        timeout_seconds=settings.openai_timeout_seconds,
    )
    return OpenAIProviderAdapters(
        llm=OpenAILLMAdapter(
            client,
            max_retries=settings.openai_max_retries,
            retry_base_seconds=settings.openai_retry_base_seconds,
        ),
        embeddings=OpenAIEmbeddingAdapter(
            client,
            model=settings.openai_embedding_model,
        ),
    )
