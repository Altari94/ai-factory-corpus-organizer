import json
from uuid import uuid4

import pytest

from app.adapters.in_memory_llm import InMemoryLLMAdapter
from app.adapters.in_memory_llm_trace import InMemoryLLMTraceAdapter
from app.domain.llm import ContextTask, ContextUnit, ModelProfile
from app.domain.semantic import Episode, EpisodeStatus
from app.services.productive_judges import ProductiveJudgeError, ProductiveSemanticJudges
from app.domain.discovery import TopicCluster
from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.domain.semantic import OrganizerRun
from app.services.discovery_persistence import DiscoveryPersistenceService
from datetime import datetime, timezone


def profile() -> ModelProfile:
    return ModelProfile(
        profile_id="semantic-test-v1",
        provider="test",
        model_name="deterministic-semantic-test",
        context_window_tokens=128,
        max_output_tokens=32,
        reserved_output_tokens=16,
        chunk_target_tokens=32,
        chunk_max_tokens=64,
    )


def episode(run_id, document_id, start, end, sequence):
    return Episode(
        organizer_run_id=run_id,
        episode_id=uuid4(),
        document_id=document_id,
        start_unit_id=start,
        end_unit_id=end,
        sequence=sequence,
        status=EpisodeStatus.CONFIRMED,
    )


def test_productive_judges_use_llm_port_and_persist_traces() -> None:
    run_id, document_id = uuid4(), uuid4()
    source_start, source_end, candidate_start, candidate_end = [uuid4() for _ in range(4)]
    source = episode(run_id, document_id, source_start, source_end, 0)
    candidate = episode(run_id, document_id, candidate_start, candidate_end, 1)
    cluster = TopicCluster(cluster_id=uuid4(), episode_ids=[source.episode_id, candidate.episode_id], algorithm_version="test")

    def response(request):
        if request.prompt.task == ContextTask.RELATION_JUDGE:
            return json.dumps({
                "decision_type": "RELATION",
                "from_unit_id": str(source_start),
                "to_unit_id": str(candidate_start),
                "relation_type": "SAME_THREAD",
                "confidence": 0.88,
            })
        if request.prompt.task == ContextTask.TOPIC_NAMING:
            return json.dumps({
                "decision_type": "TOPIC_NAMING",
                "cluster_id": str(cluster.cluster_id),
                "topic_name": "Second Brain",
                "topic_description": "Notes and workflows for a personal knowledge system.",
            })
        return json.dumps({
            "decision_type": "COHERENCE",
            "cluster_id": str(cluster.cluster_id),
            "verdict": "KEEP",
            "confidence": 0.81,
            "evidence_episode_ids": [str(source.episode_id)],
            "needs_more_evidence": False,
        })

    trace_store = InMemoryLLMTraceAdapter()
    judges = ProductiveSemanticJudges(InMemoryLLMAdapter(response), profile(), trace_store=trace_store)
    units = [
        ContextUnit(unit_id=source_start, document_id=document_id, unit_type="SENTENCE", sequence=0, text="Second Brain planning."),
        ContextUnit(unit_id=source_end, document_id=document_id, unit_type="SENTENCE", sequence=1, text="Keep the notes linked."),
        ContextUnit(unit_id=candidate_start, document_id=document_id, unit_type="SENTENCE", sequence=2, text="The same workflow continues."),
        ContextUnit(unit_id=candidate_end, document_id=document_id, unit_type="SENTENCE", sequence=3, text="Review the corpus."),
    ]

    relation = judges.judge_relation(source, candidate, units, run_id)
    named = judges.name_topic(cluster, ["Second Brain planning", "Second Brain review"], run_id)
    coherence = judges.judge_coherence(cluster, ["Second Brain planning", "Second Brain review"], run_id)

    assert relation.relation_type == "SAME_THREAD"
    assert set(relation.evidence_unit_ids) == {source_start, candidate_start}
    assert named.cluster_id == cluster.cluster_id
    assert named.label == "Second Brain"
    assert coherence.coherent is True
    assert len(trace_store.traces) == 3
    assert len(trace_store.decisions) == 3
    assert {trace.task for trace in trace_store.traces.values()} == {
        ContextTask.RELATION_JUDGE,
        ContextTask.TOPIC_NAMING,
        ContextTask.COHERENCE_JUDGE,
    }


def test_invalid_productive_output_is_rejected_and_trace_is_failed() -> None:
    run_id, document_id = uuid4(), uuid4()
    start, end = uuid4(), uuid4()
    source = episode(run_id, document_id, start, end, 0)
    candidate = episode(run_id, document_id, uuid4(), uuid4(), 1)
    trace_store = InMemoryLLMTraceAdapter()
    judges = ProductiveSemanticJudges(InMemoryLLMAdapter(lambda _request: "not-json"), profile(), trace_store=trace_store)

    with pytest.raises(ProductiveJudgeError):
        judges.judge_relation(
            source,
            candidate,
            [ContextUnit(unit_id=start, document_id=document_id, unit_type="SENTENCE", sequence=0, text="one")],
            run_id,
        )

    assert len(trace_store.traces) == 2
    assert all(trace.status.value == "FAILED" for trace in trace_store.traces.values())


def test_discovery_persistence_writes_a_complete_run_through_the_port() -> None:
    run_id, document_id = uuid4(), uuid4()
    start, end = uuid4(), uuid4()
    item = episode(run_id, document_id, start, end, 0)
    run = OrganizerRun(
        organizer_run_id=run_id,
        corpus_id=uuid4(),
        code_version="test",
        algorithm_version="test",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
    )
    writer = InMemorySemanticAdapter()
    DiscoveryPersistenceService(writer).persist(run, episodes=[item])

    assert writer.get_run(run_id) == run
    assert writer.get_episodes(run_id) == [item]
