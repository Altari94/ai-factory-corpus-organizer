from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.adapters.in_memory_embedding import InMemoryEmbeddingAdapter, InMemoryVectorStore
from app.adapters.in_memory_llm import InMemoryLLMAdapter
from app.domain.embedding import EmbeddingInput, SimilarityQuery, StoredEmbedding
from app.domain.episode_detection import BoundaryCandidateConfig
from app.domain.llm import (
    BoundaryDecision,
    ContextSelectionConfig,
    ContextTask,
    ContextUnit,
    ModelProfile,
    PromptDefinition,
)
from app.services.boundary_candidates import BoundaryCandidateDetector
from app.services.boundary_context import BoundaryContextBuilder
from app.services.boundary_judge import LLMBoundaryJudge
from app.services.chunk_builder import ChunkBuilder
from app.services.context_selector import ContextSelector
from app.services.episode_builder import EpisodeBuilder
from app.services.execution_trace import ExecutionTraceService
from app.services.prompt_builder import PromptBuilder
from app.services.structured_output import StructuredOutputValidator


UNIT_A = UUID("a3d9c3db-82cb-44a5-81f8-a192115b881a")
UNIT_B = UUID("bc1c185a-29cc-49cc-8b63-9b3f5646dcaa")
UNIT_C = UUID("27ef4e29-fccd-4fe3-b8c0-07a4e1f97b45")
DOCUMENT_ID = UUID("731ba0b0-f5a6-4c6e-bf64-65f211e671b2")


def embedding_profile() -> ModelProfile:
    return ModelProfile(
        profile_id="embedding-test",
        provider="test",
        model_name="embedding-test",
        context_window_tokens=32,
        max_output_tokens=8,
        reserved_output_tokens=8,
        chunk_target_tokens=8,
        chunk_max_tokens=16,
    )


def message_units() -> list[ContextUnit]:
    return [
        ContextUnit(unit_id=UNIT_A, document_id=DOCUMENT_ID, unit_type="MESSAGE", sequence=0, text="We plan the harbour.", speaker="user"),
        ContextUnit(unit_id=UNIT_B, document_id=DOCUMENT_ID, unit_type="MESSAGE", sequence=1, text="The harbour plan is ready.", speaker="assistant"),
        ContextUnit(unit_id=UNIT_C, document_id=DOCUMENT_ID, unit_type="MESSAGE", sequence=2, text="Now we discuss pricing for the market.", speaker="user"),
    ]


def test_embedding_model_is_exchangeable_and_versions_are_searchable() -> None:
    adapter = InMemoryEmbeddingAdapter(dimensions=8)
    outputs = adapter.embed(
        "model-a",
        [EmbeddingInput(canonical_unit_id=UNIT_A, text="harbour plan")],
    )
    store = InMemoryVectorStore()
    now = datetime.now(timezone.utc)
    store.save(
        [
            StoredEmbedding(
                embedding_id=uuid4(),
                organizer_run_id=uuid4(),
                canonical_unit_id=UNIT_A,
                profile_id="model-a",
                model_version="1",
                dimensions=8,
                vector=outputs[0].vector,
                created_at=now,
            ),
            StoredEmbedding(
                embedding_id=uuid4(),
                organizer_run_id=uuid4(),
                canonical_unit_id=UNIT_A,
                profile_id="model-a",
                model_version="2",
                dimensions=8,
                vector=outputs[0].vector,
                created_at=now,
            ),
        ]
    )

    results = store.similarity_search(SimilarityQuery(profile_id="model-a", vector=outputs[0].vector, limit=10))

    assert len(results) == 2
    assert {result.model_version for result in results} == {"1", "2"}
    assert results[0].similarity >= results[1].similarity


def test_boundary_candidates_are_explainable_and_thresholded() -> None:
    detector = BoundaryCandidateDetector(
        BoundaryCandidateConfig(
            threshold=0.5,
            speaker_change_weight=0.4,
            lexical_shift_weight=0.6,
            sequence_gap_weight=0.0,
        )
    )

    candidates = detector.detect(message_units())

    assert candidates
    assert all(candidate.score >= candidate.threshold for candidate in candidates)
    assert all(candidate.evidence_unit_ids == [candidate.left_unit_id, candidate.right_unit_id] for candidate in candidates)
    assert all("lexical_shift" in candidate.signals for candidate in candidates)


def test_boundary_context_is_bounded_and_keeps_candidate_ids() -> None:
    candidate = BoundaryCandidateDetector(
        BoundaryCandidateConfig(threshold=0.1, speaker_change_weight=0.5, lexical_shift_weight=0.5, sequence_gap_weight=0)
    ).detect(message_units())[0]
    profile = embedding_profile()
    context = BoundaryContextBuilder(
        ContextSelector({ContextTask.BOUNDARY_JUDGE: ContextSelectionConfig(max_units=3, max_tokens=20)}),
        ChunkBuilder(),
    ).build(candidate, message_units(), profile)

    assert candidate.left_unit_id in context.canonical_unit_ids
    assert candidate.right_unit_id in context.canonical_unit_ids
    assert all(chunk.input_tokens <= profile.chunk_max_tokens for chunk in context.chunks)


def test_boundary_judge_accepts_uncertain_and_stores_prompt_model_trace() -> None:
    candidate = BoundaryCandidateDetector(
        BoundaryCandidateConfig(threshold=0.1, speaker_change_weight=0.5, lexical_shift_weight=0.5, sequence_gap_weight=0)
    ).detect(message_units())[0]
    profile = embedding_profile()
    context = BoundaryContextBuilder(
        ContextSelector({ContextTask.BOUNDARY_JUDGE: ContextSelectionConfig(max_units=3, max_tokens=20)}),
        ChunkBuilder(),
    ).build(candidate, message_units(), profile)
    llm = InMemoryLLMAdapter(
        lambda _request: (
            '{"decision_type":"BOUNDARY","left_unit_id":"'
            + str(candidate.left_unit_id)
            + '","right_unit_id":"'
            + str(candidate.right_unit_id)
            + '","boundary":"UNCERTAIN","confidence":0.51}'
        )
    )
    result = LLMBoundaryJudge(llm, PromptBuilder(), StructuredOutputValidator(), ExecutionTraceService()).judge(
        candidate,
        context,
        profile,
        PromptDefinition(
            prompt_id="boundary-judge",
            version="1.0.0",
            task=ContextTask.BOUNDARY_JUDGE,
            system_template="Return structured JSON.",
            user_template="Judge: {context}",
        ),
        uuid4(),
    )

    assert result.decision.boundary == "UNCERTAIN"
    assert result.trace.prompt_version == "1.0.0"
    assert result.trace.model_profile_id == profile.profile_id
    assert set(result.trace.canonical_unit_ids).issubset(set(context.canonical_unit_ids))
    assert {candidate.left_unit_id, candidate.right_unit_id}.issubset(
        set(result.trace.canonical_unit_ids)
    )


def test_episode_builder_preserves_all_message_units_once_in_order() -> None:
    units = message_units()
    decision = BoundaryDecision(
        left_unit_id=UNIT_B,
        right_unit_id=UNIT_C,
        boundary="NEW_EPISODE",
        confidence=0.9,
    )
    result = EpisodeBuilder().build(uuid4(), units, [decision])
    memberships = result.memberships

    assert len(result.episodes) == 2
    assert [episode.sequence for episode in result.episodes] == [0, 1]
    assert [membership.canonical_unit_id for membership in memberships] == [UNIT_A, UNIT_B, UNIT_C]
    assert len({membership.canonical_unit_id for membership in memberships}) == 3
    assert all(episode.document_id == DOCUMENT_ID for episode in result.episodes)
