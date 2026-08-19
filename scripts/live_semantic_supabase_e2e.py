"""Run the F0.4.15a live semantic Supabase gate with synthetic data only.

The script creates three synthetic canonical documents under the existing
synthetic source, runs the productive OpenAI judges, persists all derived
objects, and repeats persistence in a second organizer run to verify history.
It intentionally never reads a user chat or prints credentials.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5

from app.adapters.openai_factory import build_openai_adapters
from app.adapters.semantic_factory import build_supabase_semantic_adapters
from app.adapters.supabase_embedding import SupabaseVectorAdapter
from app.config.settings import get_settings
from app.domain.discovery import SimilarEpisodeCandidate
from app.domain.embedding import EmbeddingInput, StoredEmbedding
from app.domain.llm import ContextUnit, ModelProfile
from app.domain.semantic import Episode, EpisodeStatus, OrganizerRun, OrganizerRunStatus
from app.services.derived_mapping import entities_for_run, relation_for_run, threads_for_run, topics_for_run
from app.services.discovery_persistence import DiscoveryPersistenceService
from app.services.episode_retrieval import InMemoryEpisodeRetriever
from app.services.entity_extraction import HeuristicEntityExtractor
from app.services.graph_projection import SemanticGraphProjector
from app.services.productive_judges import ProductiveSemanticJudges
from app.services.thread_reconstruction import ThreadReconstructor
from app.services.topic_clustering import SimilarityClusterer


PROJECT_SOURCE_ID = UUID("7720ab33-5482-4efc-97b5-667c08e7f34e")
PROFILE_ID = "text-embedding-3-small-f0.4.15a"
MODEL_PROFILE_ID = "gpt-5.6-luna-semantic-judge-v1"
PROMPT_VERSION = "semantic-judges-v1"


def main() -> None:
    settings = get_settings()
    openai = build_openai_adapters(settings)
    supabase = build_supabase_semantic_adapters(settings)
    vectors = SupabaseVectorAdapter(supabase.semantic.client)
    profile = ModelProfile(
        profile_id=MODEL_PROFILE_ID,
        provider="openai",
        model_name=settings.openai_llm_model,
        context_window_tokens=256,
        max_output_tokens=96,
        reserved_output_tokens=48,
        chunk_target_tokens=80,
        chunk_max_tokens=160,
    )

    documents, units = create_synthetic_canonical_corpus(supabase.semantic.client)
    first = run_semantic_pass(
        openai=openai,
        supabase=supabase,
        vectors=vectors,
        profile=profile,
        documents=documents,
        units=units,
        run_id=uuid4(),
    )
    second = clone_as_new_run(
        supabase=supabase,
        vectors=vectors,
        first=first,
        run_id=uuid4(),
    )
    validate_run(supabase, first, require_traces=True)
    validate_run(supabase, second, require_traces=False)

    print({
        "source_id": str(PROJECT_SOURCE_ID),
        "documents": len(documents),
        "canonical_units": len(units),
        "runs": [str(first["run"].organizer_run_id), str(second["run"].organizer_run_id)],
        "run_1": counts(first),
        "run_2": counts(second),
        "historical_runs_preserved": first["run"].organizer_run_id != second["run"].organizer_run_id,
    })


def create_synthetic_canonical_corpus(client):
    processing_run_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    client.table("processing_runs").insert({
        "run_id": str(processing_run_id),
        "source_id": str(PROJECT_SOURCE_ID),
        "processor_type": "synthetic-e2e",
        "processor_name": "F0.4.15a live gate",
        "processor_version": "1.0.0",
        "schema_version": "1.0.0",
        "started_at": now,
        "finished_at": now,
        "status": "SUCCEEDED",
        "configuration": {"synthetic": True, "gate": "F0.4.15a.7"},
    }).execute()

    chats = [
        ("Chat A", [
            "AI Factory Corpus Organizer defines canonical sources and semantic runs.",
            "The Corpus Organizer preserves provenance for every derived result.",
            "Palworld merchant spawning needs a stable schedule.",
        ]),
        ("Chat B", [
            "The Palworld merchant schedule continues with inventory reset rules.",
            "Palworld private play is about exploration and combat, not server tooling.",
            "Second Brain Obsidian notes should avoid duplicate knowledge.",
        ]),
        ("Chat C", [
            "The AI Factory Corpus Organizer should expose historical processing runs.",
            "Second Brain Obsidian review should link back to the original conversation.",
        ]),
    ]
    documents = []
    units = []
    for chat_index, (title, texts) in enumerate(chats):
        document_id = uuid4()
        client.table("canonical_documents").insert({
            "document_id": str(document_id),
            "source_id": str(PROJECT_SOURCE_ID),
            "schema_version": "1.0.0",
            "document_type": "SYNTHETIC_CHAT",
            "title": title,
            "language": "en",
            "source_native_id": f"f0.4.15a-chat-{chat_index + 1}",
            "metadata": {"synthetic": True, "gate": "F0.4.15a.7"},
        }).execute()
        documents.append(document_id)
        for sequence, text in enumerate(texts):
            unit_id = uuid4()
            units.append(ContextUnit(unit_id=unit_id, document_id=document_id, unit_type="MESSAGE", sequence=sequence, text=text))
            client.table("content_units").insert({
                "unit_id": str(unit_id),
                "document_id": str(document_id),
                "processing_run_id": str(processing_run_id),
                "unit_type": "MESSAGE",
                "sequence": sequence,
                "text": text,
                "schema_version": "1.0.0",
                "metadata": {"synthetic": True, "gate": "F0.4.15a.7"},
            }).execute()
    return documents, units


def run_semantic_pass(*, openai, supabase, vectors, profile, documents, units, run_id):
    run = OrganizerRun(
        organizer_run_id=run_id,
        corpus_id=PROJECT_SOURCE_ID,
        code_version="f0.4.15a-live-gate",
        algorithm_version="f0.4.15a",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
        configuration={"synthetic": True, "model": profile.model_name},
    )
    supabase.semantic.create_run(run)
    by_document = {document_id: [unit for unit in units if unit.document_id == document_id] for document_id in documents}
    episodes = []
    memberships = []
    for document_id, document_units in by_document.items():
        for index, unit in enumerate(document_units):
            episode_id = uuid5(run_id, f"episode:{document_id}:{unit.unit_id}")
            episodes.append(Episode(organizer_run_id=run_id, episode_id=episode_id, document_id=document_id, start_unit_id=unit.unit_id, end_unit_id=unit.unit_id, sequence=index, status=EpisodeStatus.CONFIRMED))
            from app.domain.episode_detection import EpisodeMembership
            memberships.append(EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit.unit_id, sequence=0))

    embedding_inputs = [EmbeddingInput(canonical_unit_id=episode.start_unit_id, text=next(unit.text for unit in units if unit.unit_id == episode.start_unit_id)) for episode in episodes]
    embedding_outputs = openai.embeddings.embed(PROFILE_ID, embedding_inputs)
    stored = [StoredEmbedding(embedding_id=uuid4(), organizer_run_id=run_id, canonical_unit_id=item.canonical_unit_id, profile_id=item.profile_id, model_version=item.model_version, dimensions=len(item.vector), vector=item.vector, created_at=datetime.now(timezone.utc), metadata={"synthetic": True, "gate": "F0.4.15a.7"}) for item in embedding_outputs]
    vectors.save(stored)
    retriever = InMemoryEpisodeRetriever()
    for episode, embedding in zip(episodes, stored, strict=True):
        retriever.add(episode.episode_id, embedding.embedding_id, embedding.vector, embedding.profile_id, embedding.model_version)
    candidates = [candidate for episode in episodes for candidate in retriever.similar_episodes(episode.episode_id, limit=1)]

    judges = ProductiveSemanticJudges(openai.llm, profile, trace_store=supabase.traces, prompt_version=PROMPT_VERSION)
    episode_units = {episode.episode_id: [unit for unit in units if unit.unit_id == episode.start_unit_id] for episode in episodes}
    relations = []
    for candidate in candidates:
        source = next(item for item in episodes if item.episode_id == candidate.source_episode_id)
        target = next(item for item in episodes if item.episode_id == candidate.candidate_episode_id)
        relation = judges.judge_relation(source, target, episode_units[source.episode_id] + episode_units[target.episode_id], run_id)
        relations.append(relation_for_run(run_id, relation))

    entity_extractor = HeuristicEntityExtractor()
    entity_result = [entity_extractor.extract(episode, episode_units[episode.episode_id]) for episode in episodes]
    all_entities = [mention for result in entity_result for mention in result.mentions]
    from app.domain.discovery import EntityExtractionResult
    entity_records, entity_links = entities_for_run(run_id, EntityExtractionResult(mentions=all_entities, algorithm_version="heuristic-entity-v1"))
    similarities = candidates
    clusters = SimilarityClusterer().cluster([episode.episode_id for episode in episodes], similarities, threshold=0.72)
    named_clusters = []
    coherence_decisions = []
    for cluster in clusters:
        texts = [next(unit.text for unit in units if unit.unit_id == next(item.start_unit_id for item in episodes if item.episode_id == episode_id)) for episode_id in cluster.episode_ids]
        named = judges.name_topic(cluster, texts, run_id)
        named_clusters.append(named)
        coherence_decisions.append(judges.judge_coherence(named, texts, run_id))
    topics, topic_links = topics_for_run(run_id, named_clusters)
    threads = ThreadReconstructor().reconstruct(relations, {episode.episode_id: (episode.document_id, episode.sequence) for episode in episodes})
    thread_records, thread_links = threads_for_run(run_id, threads)
    SemanticGraphProjector().project(episodes, entity_records, topics, relations, entity_links, topic_links)
    DiscoveryPersistenceService(supabase.semantic).persist(run, episodes=episodes, memberships=memberships, entities=entity_records, episode_entities=entity_links, topics=topics, episode_topics=topic_links, relations=relations, threads=thread_records, thread_episodes=thread_links, create_run=False)
    supabase.semantic.complete_run(run_id, datetime.now(timezone.utc))
    return {"run": run, "episodes": episodes, "memberships": memberships, "entities": entity_records, "entity_links": entity_links, "topics": topics, "topic_links": topic_links, "relations": relations, "threads": thread_records, "thread_links": thread_links, "embeddings": stored, "coherence": coherence_decisions}


def clone_as_new_run(*, supabase, vectors, first, run_id):
    run = first["run"].model_copy(update={"organizer_run_id": run_id, "started_at": datetime.now(timezone.utc), "finished_at": None, "status": OrganizerRunStatus.RUNNING})
    episodes = [item.model_copy(update={"organizer_run_id": run_id, "episode_id": uuid5(run_id, str(item.episode_id))}) for item in first["episodes"]]
    episode_map = {old.episode_id: new.episode_id for old, new in zip(first["episodes"], episodes, strict=True)}
    memberships = [item.model_copy(update={"organizer_run_id": run_id, "episode_id": episode_map[item.episode_id]}) for item in first["memberships"]]
    entities = [item.model_copy(update={"organizer_run_id": run_id, "entity_id": uuid5(run_id, str(item.entity_id))}) for item in first["entities"]]
    entity_map = {old.entity_id: new.entity_id for old, new in zip(first["entities"], entities, strict=True)}
    entity_links = [item.model_copy(update={"organizer_run_id": run_id, "link_id": uuid4(), "episode_id": episode_map[item.episode_id], "entity_id": entity_map[item.entity_id]}) for item in first["entity_links"]]
    topics = [item.model_copy(update={"organizer_run_id": run_id, "topic_id": uuid5(run_id, str(item.topic_id))}) for item in first["topics"]]
    topic_map = {old.topic_id: new.topic_id for old, new in zip(first["topics"], topics, strict=True)}
    topic_links = [item.model_copy(update={"organizer_run_id": run_id, "link_id": uuid4(), "episode_id": episode_map[item.episode_id], "topic_id": topic_map[item.topic_id]}) for item in first["topic_links"]]
    relations = [item.model_copy(update={"organizer_run_id": run_id, "relation_id": uuid4(), "from_episode_id": episode_map[item.from_episode_id], "to_episode_id": episode_map[item.to_episode_id]}) for item in first["relations"]]
    threads = [item.model_copy(update={"organizer_run_id": run_id, "thread_id": uuid5(run_id, str(item.thread_id))}) for item in first["threads"]]
    thread_map = {old.thread_id: new.thread_id for old, new in zip(first["threads"], threads, strict=True)}
    thread_links = [item.model_copy(update={"organizer_run_id": run_id, "link_id": uuid4(), "thread_id": thread_map[item.thread_id], "episode_id": episode_map[item.episode_id]}) for item in first["thread_links"]]
    embeddings = [item.model_copy(update={"embedding_id": uuid4(), "organizer_run_id": run_id}) for item in first["embeddings"]]
    supabase.semantic.create_run(run)
    vectors.save(embeddings)
    DiscoveryPersistenceService(supabase.semantic).persist(run, episodes=episodes, memberships=memberships, entities=entities, episode_entities=entity_links, topics=topics, episode_topics=topic_links, relations=relations, threads=threads, thread_episodes=thread_links, create_run=False)
    supabase.semantic.complete_run(run_id, datetime.now(timezone.utc))
    return {**first, "run": run, "episodes": episodes, "memberships": memberships, "entities": entities, "entity_links": entity_links, "topics": topics, "topic_links": topic_links, "relations": relations, "threads": threads, "thread_links": thread_links, "embeddings": embeddings}


def validate_run(supabase, result, *, require_traces: bool) -> None:
    run_id = result["run"].organizer_run_id
    stored_run = supabase.semantic.get_run(run_id)
    assert stored_run and stored_run.status.value == "SUCCEEDED"
    assert all(item.organizer_run_id == run_id for key in ("episodes", "entities", "topics", "relations", "threads") for item in result[key])
    assert all(item.evidence_unit_ids for item in result["relations"])
    membership_rows = supabase.semantic.client.table("episode_memberships").select("episode_id,canonical_unit_id").eq("organizer_run_id", str(run_id)).execute().data
    trace_rows = supabase.semantic.client.table("llm_execution_traces").select("task,status,request_id,input_tokens,output_tokens,latency_ms,retry_count").eq("organizer_run_id", str(run_id)).execute().data
    canonical_ids = {row["canonical_unit_id"] for row in membership_rows}
    assert canonical_ids
    assert all(str(evidence_id) in canonical_ids for item in result["relations"] for evidence_id in item.evidence_unit_ids)
    assert all(str(evidence_id) in canonical_ids for item in result["entity_links"] for evidence_id in item.evidence_unit_ids)
    assert all(topic.label and topic.description for topic in result["topics"])
    assert all(link.sequence >= 0 for link in result["thread_links"])
    assert len({(link.thread_id, link.episode_id) for link in result["thread_links"]}) == len(result["thread_links"])
    assert len(membership_rows) == len(result["memberships"])
    if require_traces:
        assert {row["task"] for row in trace_rows} >= {"RELATION_JUDGE", "TOPIC_NAMING", "COHERENCE_JUDGE"}
        assert all(row["status"] == "SUCCEEDED" for row in trace_rows)
        assert all(row["request_id"] and row["input_tokens"] is not None and row["output_tokens"] is not None for row in trace_rows)
        assert all(row["latency_ms"] is not None and row["retry_count"] >= 0 for row in trace_rows)


def counts(result) -> dict[str, int]:
    return {key: len(result[key]) for key in ("episodes", "entities", "topics", "relations", "threads", "embeddings")}


if __name__ == "__main__":
    main()
