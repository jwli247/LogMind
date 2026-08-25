from functools import cache

from langchain_openai import OpenAIEmbeddings

from core import settings


@cache
def get_embedding_model() -> OpenAIEmbeddings:
    if settings.EMBEDDING_PROVIDER != "openai-compatible":
        raise ValueError("Only openai-compatible embedding provider is currently supported")

    if not settings.EMBEDDING_API_KEY or not settings.EMBEDDING_BASE_URL or not settings.EMBEDDING_MODEL:
        raise ValueError(
            "EMBEDDING_API_KEY, EMBEDDING_BASE_URL and EMBEDDING_MODEL must be configured"
        )

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
        check_embedding_ctx_length=False,
    )