from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.adapters.openai_client import create_openai_client
from app.adapters.openai_embedding import OpenAIEmbeddingAdapter
from app.adapters.openai_factory import build_openai_adapters
from app.adapters.openai_llm import OpenAILLMAdapter
from app.config.settings import Settings
from app.domain.embedding import EmbeddingInput
from app.domain.llm import ContextTask, LLMRequest, ModelProfile, PromptDefinition
from app.services.prompt_builder import PromptBuilder


UNIT_ID = uuid4()


def profile() -> ModelProfile:
    return ModelProfile(
        profile_id="openai-boundary-v1",
        provider="openai",
        model_name="gpt-test",
        context_window_tokens=64,
        max_output_tokens=16,
        reserved_output_tokens=8,
        chunk_target_tokens=8,
        chunk_max_tokens=16,
    )


def request() -> LLMRequest:
    prompt = PromptBuilder().build(
        PromptDefinition(
            prompt_id="boundary-judge",
            version="1.0.0",
            task=ContextTask.BOUNDARY_JUDGE,
            system_template="Return JSON.",
            user_template="Judge this: {context}",
        ),
        SimpleNamespace(
            source_unit_ids=[UNIT_ID],
            items=[SimpleNamespace(unit_id=UNIT_ID, text="context")],
        ),
    )
    return LLMRequest(request_id=uuid4(), profile=profile(), prompt=prompt, attempt=1)


def test_openai_client_requires_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_openai_client(None)


def test_provider_factory_requires_key_and_builds_both_adapters() -> None:
    settings = Settings(openai_api_key="test-key")
    adapters = build_openai_adapters(settings)

    assert isinstance(adapters.llm, OpenAILLMAdapter)
    assert isinstance(adapters.embeddings, OpenAIEmbeddingAdapter)


def test_llm_adapter_uses_responses_structured_output_and_usage() -> None:
    captured: dict[str, object] = {}

    class Responses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                id="resp_123",
                output_text='{"decision_type":"BOUNDARY"}',
                usage=SimpleNamespace(input_tokens=12, output_tokens=5),
            )

    response = OpenAILLMAdapter(SimpleNamespace(responses=Responses())).generate(request())

    assert response.provider_request_id == "resp_123"
    assert response.input_tokens == 12
    assert captured["model"] == "gpt-test"
    assert captured["text"]["format"]["type"] == "json_schema"
    assert captured["text"]["format"]["strict"] is True


def test_llm_adapter_does_not_retry_unknown_programming_errors() -> None:
    calls = 0

    class Responses:
        def create(self, **_kwargs):
            nonlocal calls
            calls += 1
            raise RuntimeError("simulated transient error")

    # Non-SDK errors are not retried because they are programming/configuration errors.
    with pytest.raises(RuntimeError, match="simulated transient error"):
        OpenAILLMAdapter(SimpleNamespace(responses=Responses()), max_retries=2, sleep=lambda _seconds: None).generate(request())
    assert calls == 1


def test_embedding_adapter_validates_dimensions_and_preserves_ids() -> None:
    class Embeddings:
        def create(self, **_kwargs):
            return SimpleNamespace(
                model="text-embedding-test-v1",
                data=[
                    SimpleNamespace(index=0, embedding=[0.1, 0.2, 0.3]),
                    SimpleNamespace(index=1, embedding=[0.4, 0.5, 0.6]),
                ],
            )

    other_id = uuid4()
    outputs = OpenAIEmbeddingAdapter(
        SimpleNamespace(embeddings=Embeddings()),
        model="text-embedding-test",
        expected_dimensions=3,
    ).embed(
        "embedding-v1",
        [EmbeddingInput(canonical_unit_id=UNIT_ID, text="one"), EmbeddingInput(canonical_unit_id=other_id, text="two")],
    )

    assert [output.canonical_unit_id for output in outputs] == [UNIT_ID, other_id]
    assert all(output.model_version == "text-embedding-test-v1" for output in outputs)
