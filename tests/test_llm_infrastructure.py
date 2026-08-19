import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.adapters.in_memory_llm import InMemoryLLMAdapter
from app.adapters.in_memory_llm_trace import InMemoryLLMTraceAdapter
from app.domain.llm import (
    ContextSelectionConfig,
    ContextTask,
    ContextUnit,
    LLMRequest,
    ModelProfile,
    PromptDefinition,
    SelectedContext,
)
from app.ports.llm import LLMPort, LLMTracePort
from app.services.chunk_builder import ChunkBuilder
from app.services.context_selector import ContextSelector
from app.services.execution_trace import ExecutionTraceService
from app.services.prompt_builder import PromptBuilder
from app.services.structured_output import RetryableStructuredOutputError, StructuredOutputValidator


UNIT_A = UUID("a3d9c3db-82cb-44a5-81f8-a192115b881a")
UNIT_B = UUID("bc1c185a-29cc-49cc-8b63-9b3f5646dcaa")
DOCUMENT_ID = UUID("731ba0b0-f5a6-4c6e-bf64-65f211e671b2")


def profile() -> ModelProfile:
    return ModelProfile(
        profile_id="test-small",
        provider="test",
        model_name="deterministic-test-model",
        context_window_tokens=32,
        max_output_tokens=8,
        reserved_output_tokens=8,
        chunk_target_tokens=4,
        chunk_max_tokens=8,
    )


def units() -> list[ContextUnit]:
    return [
        ContextUnit(unit_id=UNIT_A, document_id=DOCUMENT_ID, unit_type="SENTENCE", sequence=0, text="Alpha one."),
        ContextUnit(unit_id=UNIT_B, document_id=DOCUMENT_ID, unit_type="SENTENCE", sequence=1, text="Beta two."),
    ]


def test_model_profiles_are_configurable_and_budgets_are_validated() -> None:
    small = profile()
    large = small.model_copy(
        update={"profile_id": "test-large", "model_name": "larger", "chunk_max_tokens": 16, "chunk_target_tokens": 12}
    )

    assert small.model_name != large.model_name
    assert small.chunk_max_tokens != large.chunk_max_tokens
    invalid = small.model_dump()
    invalid.update({"chunk_target_tokens": 9, "chunk_max_tokens": 8})
    with pytest.raises(ValueError):
        ModelProfile(**invalid)


def test_context_selection_is_task_specific_and_keeps_canonical_ids() -> None:
    selector = ContextSelector(
        {
            ContextTask.BOUNDARY_JUDGE: ContextSelectionConfig(max_units=2, max_tokens=20),
            ContextTask.RELATION_JUDGE: ContextSelectionConfig(
                max_units=1, max_tokens=20, include_adjacent_units=False
            ),
        }
    )

    boundary = selector.select(ContextTask.BOUNDARY_JUDGE, units(), [UNIT_A])
    relation = selector.select(ContextTask.RELATION_JUDGE, units(), [UNIT_A])

    assert [unit.unit_id for unit in boundary.units] == [UNIT_A, UNIT_B]
    assert [unit.unit_id for unit in relation.units] == [UNIT_A]
    assert boundary.anchor_unit_ids == [UNIT_A]


def test_chunk_builder_respects_profile_and_preserves_long_unit_text() -> None:
    original = "One two three four five six seven eight nine ten."
    long_unit = ContextUnit(
        unit_id=UNIT_A,
        document_id=DOCUMENT_ID,
        unit_type="SENTENCE",
        sequence=0,
        text=original,
    )
    context = SelectedContext(
        task=ContextTask.BOUNDARY_JUDGE,
        anchor_unit_ids=[UNIT_A],
        units=[long_unit],
        configuration=ContextSelectionConfig(max_units=1, max_tokens=100),
    )

    chunks = ChunkBuilder().build(context, profile())
    fragments = [item for chunk in chunks for item in chunk.items]

    assert all(chunk.input_tokens <= profile().chunk_max_tokens for chunk in chunks)
    assert "".join(item.text for item in fragments) == original
    assert all(item.unit_id == UNIT_A for item in fragments)


def test_prompt_is_versioned_and_independent_of_llm_adapter() -> None:
    chunk = ChunkBuilder().build(
        SelectedContext(
            task=ContextTask.BOUNDARY_JUDGE,
            anchor_unit_ids=[UNIT_A],
            units=units()[:1],
            configuration=ContextSelectionConfig(max_units=1, max_tokens=20),
        ),
        profile(),
    )[0]
    prompt = PromptBuilder().build(
        PromptDefinition(
            prompt_id="boundary-judge",
            version="1.2.0",
            task=ContextTask.BOUNDARY_JUDGE,
            system_template="Return JSON only.",
            user_template="Judge this context: {context}. JSON example: {\"decision_type\": \"BOUNDARY\"}",
        ),
        chunk,
    )

    assert prompt.prompt_version == "1.2.0"
    assert str(UNIT_A) in prompt.user
    assert "decision_type" in prompt.user


def test_llm_port_can_be_exercised_without_real_api_call() -> None:
    adapter = InMemoryLLMAdapter(lambda _request: "{\"ok\": true}")
    assert isinstance(adapter, LLMPort)
    request = LLMRequest(
        request_id=uuid4(),
        profile=profile(),
        prompt=PromptBuilder().build(
            PromptDefinition(
                prompt_id="test",
                version="1.0.0",
                task=ContextTask.BOUNDARY_JUDGE,
                system_template="system",
                user_template="{context}",
            ),
            ChunkBuilder().build(
                SelectedContext(
                    task=ContextTask.BOUNDARY_JUDGE,
                    anchor_unit_ids=[UNIT_A],
                    units=units()[:1],
                    configuration=ContextSelectionConfig(max_units=1, max_tokens=20),
                ),
                profile(),
            )[0],
        ),
        attempt=1,
    )

    response = adapter.generate(request)

    assert response.raw_output == "{\"ok\": true}"
    assert len(adapter.requests) == 1


def test_structured_output_is_validated_and_references_canonical_ids() -> None:
    trace_id = uuid4()
    organizer_run_id = uuid4()
    response = InMemoryLLMAdapter(
        lambda _request: json.dumps(
            {
                "decision_type": "BOUNDARY",
                "left_unit_id": str(UNIT_A),
                "right_unit_id": str(UNIT_B),
                "boundary": "NEW_EPISODE",
                "confidence": 0.91,
            }
        )
    ).generate(
        LLMRequest(
            request_id=uuid4(),
            profile=profile(),
            prompt=PromptBuilder().build(
                PromptDefinition(
                    prompt_id="boundary",
                    version="1.0.0",
                    task=ContextTask.BOUNDARY_JUDGE,
                    system_template="system",
                    user_template="context",
                ),
                ChunkBuilder().build(
                    SelectedContext(
                        task=ContextTask.BOUNDARY_JUDGE,
                        anchor_unit_ids=[UNIT_A, UNIT_B],
                        units=units(),
                        configuration=ContextSelectionConfig(max_units=2, max_tokens=20),
                    ),
                    profile(),
                )[0],
            ),
            attempt=1,
        )
    )
    decision = StructuredOutputValidator().validate(
        response,
        task=ContextTask.BOUNDARY_JUDGE,
        organizer_run_id=organizer_run_id,
        trace_id=trace_id,
        prompt_id="boundary",
        prompt_version="1.0.0",
        canonical_unit_ids=[UNIT_A, UNIT_B],
    )

    assert decision.prompt_version == "1.0.0"
    assert set(decision.canonical_unit_ids) == {UNIT_A, UNIT_B}

    with pytest.raises(RetryableStructuredOutputError):
        StructuredOutputValidator().validate(
            response.model_copy(update={"raw_output": "not-json"}),
            task=ContextTask.BOUNDARY_JUDGE,
            organizer_run_id=organizer_run_id,
            trace_id=trace_id,
            prompt_id="boundary",
            prompt_version="1.0.0",
            canonical_unit_ids=[UNIT_A],
        )


def test_execution_trace_links_request_prompt_model_units_and_decision() -> None:
    request = LLMRequest(
        request_id=uuid4(),
        profile=profile(),
        prompt=PromptBuilder().build(
            PromptDefinition(
                prompt_id="relation",
                version="2.0.0",
                task=ContextTask.RELATION_JUDGE,
                system_template="system",
                user_template="context",
            ),
            ChunkBuilder().build(
                SelectedContext(
                    task=ContextTask.RELATION_JUDGE,
                    anchor_unit_ids=[UNIT_A],
                    units=units()[:1],
                    configuration=ContextSelectionConfig(max_units=1, max_tokens=20),
                ),
                profile(),
            )[0],
        ),
        attempt=1,
    )
    organizer_run_id = uuid4()
    trace_service = ExecutionTraceService()
    trace = trace_service.start(request, organizer_run_id)
    response = InMemoryLLMAdapter(lambda _request: "{}").generate(request)
    decision = uuid4()
    completed = trace_service.succeed(
        trace,
        response,
        type("Decision", (), {"decision_id": decision})(),
    )

    assert completed.prompt_version == "2.0.0"
    assert completed.model_profile_id == profile().profile_id
    assert completed.canonical_unit_ids == [UNIT_A]
    assert completed.structured_decision_id == decision


def test_trace_store_persists_trace_and_structured_decision() -> None:
    store = InMemoryLLMTraceAdapter()
    assert isinstance(store, LLMTracePort)
    trace = ExecutionTraceService().start(
        LLMRequest(
            request_id=uuid4(),
            profile=profile(),
            prompt=PromptBuilder().build(
                PromptDefinition(
                    prompt_id="boundary",
                    version="1.0.0",
                    task=ContextTask.BOUNDARY_JUDGE,
                    system_template="system",
                    user_template="context",
                ),
                ChunkBuilder().build(
                    SelectedContext(
                        task=ContextTask.BOUNDARY_JUDGE,
                        anchor_unit_ids=[UNIT_A],
                        units=units()[:1],
                        configuration=ContextSelectionConfig(max_units=1, max_tokens=20),
                    ),
                    profile(),
                )[0],
            ),
            attempt=1,
        ),
        uuid4(),
    )
    store.save_trace(trace)

    assert store.traces[trace.trace_id] == trace
