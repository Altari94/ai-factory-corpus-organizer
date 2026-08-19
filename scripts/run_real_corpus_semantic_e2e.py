"""Run a bounded, productive semantic E2E pass for explicit source IDs.

This operational script reads only the canonical contract from Supabase.  It
never reads local raw files and deliberately prints counts/IDs rather than chat
content.  The windowed episode baseline is versioned in the organizer run so
that a later, evaluated boundary model can be compared without overwriting it.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5

from app.adapters.openai_factory import build_openai_adapters
from app.adapters.semantic_factory import build_supabase_semantic_adapters
from app.adapters.supabase_embedding import SupabaseVectorAdapter
from app.config.settings import get_settings
from app.domain.discovery import EntityExtractionResult
from app.domain.embedding import EmbeddingInput, StoredEmbedding
from app.domain.episode_detection import EpisodeMembership
from app.domain.llm import ContextUnit, ModelProfile
from app.domain.semantic import Episode, EpisodeStatus, OrganizerRun
from app.services.derived_mapping import entities_for_run, relation_for_run, threads_for_run, topics_for_run
from app.services.discovery_persistence import DiscoveryPersistenceService
from app.services.episode_retrieval import InMemoryEpisodeRetriever
from app.services.entity_extraction import HeuristicEntityExtractor
from app.services.productive_judges import ProductiveSemanticJudges
from app.services.thread_reconstruction import ThreadReconstructor
from app.services.topic_clustering import SimilarityClusterer


EMBEDDING_PROFILE_ID = "text-embedding-3-small-f0.4.18"
MODEL_PROFILE_ID = "gpt-5.6-luna-semantic-judge-v1"
WINDOW_SIZE = 25
RELATION_JUDGE_LIMIT = 36
REPRESENTATIVES_PER_CLUSTER = 4


def main(arguments: list[str]) -> None:
    if len(arguments) < 2:
        raise SystemExit("usage: run_real_corpus_semantic_e2e.py <source-id> <source-id> [...]")
    source_ids = [UUID(value) for value in arguments]
    settings = get_settings()
    openai = build_openai_adapters(settings)
    supabase = build_supabase_semantic_adapters(settings)
    vectors = SupabaseVectorAdapter(supabase.semantic.client)
    units = load_message_units(supabase.semantic.client, source_ids)
    if not units:
        raise RuntimeError("No successful canonical MESSAGE units were found for the selected sources")

    run_id = uuid4()
    corpus_id = uuid5(UUID(int=0), "real-corpus:" + ",".join(sorted(str(item) for item in source_ids)))
    profile = ModelProfile(
        profile_id=MODEL_PROFILE_ID,
        provider="openai",
        model_name=settings.openai_llm_model,
        context_window_tokens=512,
        max_output_tokens=128,
        reserved_output_tokens=64,
        chunk_target_tokens=240,
        chunk_max_tokens=384,
    )
    run = OrganizerRun(
        organizer_run_id=run_id,
        corpus_id=corpus_id,
        code_version="f0.4.18-real-e2e",
        algorithm_version="windowed-episodes-v1+embedding-retrieval-v1",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
        configuration={
            "purpose": "F0.4.18 real corpus technical acceptance",
            "source_ids": [str(item) for item in source_ids],
            "episode_window_size": WINDOW_SIZE,
            "relation_judge_limit": RELATION_JUDGE_LIMIT,
            "representatives_per_cluster": REPRESENTATIVES_PER_CLUSTER,
            "model": profile.model_name,
            "embedding_model": settings.openai_embedding_model,
        },
    )
    supabase.semantic.create_run(run)
    try:
        episodes, memberships = build_windowed_episodes(run_id, units)
        text_by_unit = {unit.unit_id: unit.text for unit in units}
        episode_units = episode_evidence_units(episodes, units)

        embedded = openai.embeddings.embed(
            EMBEDDING_PROFILE_ID,
            [EmbeddingInput(canonical_unit_id=episode.start_unit_id, text=text_by_unit[episode.start_unit_id]) for episode in episodes],
        )
        stored_embeddings = [
            StoredEmbedding(
                embedding_id=uuid4(), organizer_run_id=run_id,
                canonical_unit_id=item.canonical_unit_id, profile_id=item.profile_id,
                model_version=item.model_version, dimensions=len(item.vector), vector=item.vector,
                created_at=datetime.now(timezone.utc),
                metadata={"acceptance_run": True, "episode_id": str(episode.episode_id)},
            )
            for episode, item in zip(episodes, embedded, strict=True)
        ]
        vectors.save(stored_embeddings)
        candidates = retrieve_candidates(episodes, stored_embeddings)

        judges = ProductiveSemanticJudges(openai.llm, profile, trace_store=supabase.traces)
        episode_by_id = {episode.episode_id: episode for episode in episodes}
        relations = []
        for candidate in candidates[:RELATION_JUDGE_LIMIT]:
            relation = judges.judge_relation(
                episode_by_id[candidate.source_episode_id],
                episode_by_id[candidate.candidate_episode_id],
                episode_units[candidate.source_episode_id] + episode_units[candidate.candidate_episode_id],
                run_id,
            )
            relations.append(relation_for_run(run_id, relation))

        extraction = HeuristicEntityExtractor()
        mentions = [mention for episode in episodes for mention in extraction.extract(episode, episode_units[episode.episode_id]).mentions]
        entities, entity_links = entities_for_run(run_id, EntityExtractionResult(mentions=mentions, algorithm_version="heuristic-entity-v1"))

        clusters = SimilarityClusterer().cluster([item.episode_id for item in episodes], candidates, threshold=0.72)
        named_clusters = []
        coherence_count = 0
        for cluster in clusters:
            representatives = cluster.episode_ids[:REPRESENTATIVES_PER_CLUSTER]
            texts = [episode_units[item][0].text for item in representatives]
            representative_cluster = cluster.model_copy(update={"episode_ids": representatives})
            if len(cluster.episode_ids) > 1:
                named = judges.name_topic(representative_cluster, texts, run_id).model_copy(update={"episode_ids": cluster.episode_ids})
                judges.judge_coherence(representative_cluster, texts, run_id)
                coherence_count += 1
            else:
                named = cluster.model_copy(update={"label": "Unassigned", "metadata": {"description": "Singleton episode; no LLM topic label requested."}})
            named_clusters.append(named)
        topics, topic_links = topics_for_run(run_id, named_clusters)
        threads = ThreadReconstructor().reconstruct(relations, {item.episode_id: (item.document_id, item.sequence) for item in episodes})
        thread_records, thread_links = threads_for_run(run_id, threads)
        DiscoveryPersistenceService(supabase.semantic).persist(
            run, episodes=episodes, memberships=memberships, entities=entities,
            episode_entities=entity_links, topics=topics, episode_topics=topic_links,
            relations=relations, threads=thread_records, thread_episodes=thread_links,
            create_run=False,
        )
        supabase.semantic.complete_run(run_id, datetime.now(timezone.utc))
    except Exception as error:
        supabase.semantic.fail_run(run_id, datetime.now(timezone.utc), f"{type(error).__name__}: {error}")
        raise
    print({
        "organizer_run_id": str(run_id), "source_count": len(source_ids),
        "canonical_message_units": len(units), "episodes": len(episodes),
        "embeddings": len(stored_embeddings), "retrieval_candidates": len(candidates),
        "llm_relation_decisions": len(relations), "topics": len(topics),
        "llm_coherence_decisions": coherence_count, "threads": len(thread_records),
    })


def load_message_units(client, source_ids: list[UUID]) -> list[ContextUnit]:
    result: list[ContextUnit] = []
    for source_id in source_ids:
        runs = client.table("processing_runs").select("run_id,schema_version,finished_at").eq("source_id", str(source_id)).eq("status", "SUCCEEDED").order("finished_at", desc=True).limit(1).execute().data
        if not runs:
            raise RuntimeError(f"No successful canonical run for source {source_id}")
        run = runs[0]
        rows = client.table("content_units").select("unit_id,document_id,unit_type,sequence,text").eq("processing_run_id", run["run_id"]).eq("unit_type", "MESSAGE").order("sequence").execute().data
        if not rows:
            raise RuntimeError(f"No canonical MESSAGE units for source {source_id}")
        result.extend(ContextUnit(unit_id=UUID(row["unit_id"]), document_id=UUID(row["document_id"]), unit_type=row["unit_type"], sequence=row["sequence"], text=row["text"]) for row in rows)
    return result


def build_windowed_episodes(run_id: UUID, units: list[ContextUnit]) -> tuple[list[Episode], list[EpisodeMembership]]:
    by_document: dict[UUID, list[ContextUnit]] = defaultdict(list)
    for unit in units:
        by_document[unit.document_id].append(unit)
    episodes, memberships = [], []
    for document_id, document_units in by_document.items():
        for sequence, start in enumerate(range(0, len(document_units), WINDOW_SIZE)):
            window = document_units[start:start + WINDOW_SIZE]
            episode_id = uuid5(run_id, f"windowed-episode:{document_id}:{window[0].unit_id}:{window[-1].unit_id}")
            episodes.append(Episode(organizer_run_id=run_id, episode_id=episode_id, document_id=document_id, start_unit_id=window[0].unit_id, end_unit_id=window[-1].unit_id, sequence=sequence, status=EpisodeStatus.CONFIRMED))
            memberships.extend(EpisodeMembership(organizer_run_id=run_id, episode_id=episode_id, canonical_unit_id=unit.unit_id, sequence=index) for index, unit in enumerate(window))
    return episodes, memberships


def episode_evidence_units(episodes: list[Episode], units: list[ContextUnit]) -> dict[UUID, list[ContextUnit]]:
    texts = {unit.unit_id: unit for unit in units}
    return {
        episode.episode_id: [_excerpt(texts[episode.start_unit_id]), _excerpt(texts[episode.end_unit_id])]
        if episode.start_unit_id != episode.end_unit_id
        else [_excerpt(texts[episode.start_unit_id])]
        for episode in episodes
    }


def _excerpt(unit: ContextUnit) -> ContextUnit:
    """Bound LLM context only; canonical text remains untouched in Supabase."""
    limit = 240
    text = unit.text if len(unit.text) <= limit else unit.text[: limit - 1].rstrip() + "…"
    return unit.model_copy(update={"text": text})


def retrieve_candidates(episodes: list[Episode], embeddings: list[StoredEmbedding]):
    retriever = InMemoryEpisodeRetriever()
    for episode, embedding in zip(episodes, embeddings, strict=True):
        retriever.add(episode.episode_id, embedding.embedding_id, embedding.vector, embedding.profile_id, embedding.model_version)
    seen, result = set(), []
    for episode in episodes:
        for candidate in retriever.similar_episodes(episode.episode_id, limit=2):
            key = tuple(sorted((candidate.source_episode_id, candidate.candidate_episode_id), key=str))
            if key not in seen:
                seen.add(key)
                result.append(candidate)
    return sorted(result, key=lambda item: item.similarity_score, reverse=True)


if __name__ == "__main__":
    main(sys.argv[1:])
