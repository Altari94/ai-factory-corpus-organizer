from openai import OpenAI


def create_openai_client(api_key: str | None, *, timeout_seconds: float = 60.0) -> OpenAI:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
    return OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
