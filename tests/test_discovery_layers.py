from uuid import uuid4

from app.domain.discovery import SimilarEpisodeCandidate
from app.domain.llm import ContextUnit
from app.domain.semantic import Episode, EpisodeRelation, EpisodeStatus
from app.services.coherence import HeuristicCoherenceJudge, RepresentativeContextSelector
from app.services.entity_extraction import HeuristicEntityExtractor
from app.services.graph_projection import SemanticGraphProjector
from app.services.hierarchical_clustering import RecursiveClusterer
from app.services.episode_retrieval import InMemoryEpisodeRetriever
from app.services.thread_reconstruction import ThreadReconstructor
from app.services.topic_clustering import SimilarityClusterer
from app.services.topic_naming import VersionedTopicNamer


def episodes():
    run_id, doc_id = uuid4(), uuid4()
    units = [uuid4() for _ in range(4)]
    return [
        Episode(organizer_run_id=run_id, episode_id=uuid4(), document_id=doc_id, start_unit_id=units[0], end_unit_id=units[1], sequence=0, status=EpisodeStatus.CONFIRMED),
        Episode(organizer_run_id=run_id, episode_id=uuid4(), document_id=doc_id, start_unit_id=units[2], end_unit_id=units[3], sequence=1, status=EpisodeStatus.CONFIRMED),
    ], units


def test_entity_extraction_is_open_ended_and_keeps_evidence() -> None:
    items, unit_ids = episodes()
    result = HeuristicEntityExtractor().extract(
        items[0],
        [ContextUnit(unit_id=unit_ids[0], document_id=items[0].document_id, unit_type="MESSAGE", sequence=0, text="Obsidian links remain stable.")],
    )
    assert result.mentions[0].canonical_name == "Obsidian"
    assert result.mentions[0].evidence_unit_ids == [unit_ids[0]]


def test_episode_retrieval_and_clustering_are_versioned() -> None:
    items, _ = episodes()
    retriever = InMemoryEpisodeRetriever()
    embedding_ids = [uuid4(), uuid4()]
    retriever.add(items[0].episode_id, embedding_ids[0], [1.0, 0.0], "profile-v1", "model-v1")
    retriever.add(items[1].episode_id, embedding_ids[1], [0.9, 0.1], "profile-v1", "model-v1")
    candidates = retriever.similar_episodes(items[0].episode_id, limit=1)
    assert candidates[0].similarity_score > 0.9
    clusters = SimilarityClusterer().cluster([item.episode_id for item in items], candidates + [candidates[0].model_copy(update={"source_episode_id": items[1].episode_id, "candidate_episode_id": items[0].episode_id})], threshold=0.8)
    assert len(clusters) == 1
    assert clusters[0].algorithm_version == "similarity-components-v1"


def test_graph_projection_and_thread_reconstruction_are_database_independent() -> None:
    items, _ = episodes()
    relation = EpisodeRelation(
        organizer_run_id=items[0].organizer_run_id, relation_id=uuid4(),
        from_episode_id=items[0].episode_id, to_episode_id=items[1].episode_id,
        relation_type="SAME_THREAD", confidence=0.8,
        evidence_unit_ids=[items[0].start_unit_id],
    )
    graph = SemanticGraphProjector().project(items, [], [], [relation], [], [])
    assert len(graph.nodes) == 2
    assert graph.edges[0].edge_type == "SAME_THREAD"
    threads = ThreadReconstructor().reconstruct([relation], {item.episode_id: (item.document_id, item.sequence) for item in items})
    assert len(threads) == 1
    assert [item.sequence for item in threads[0].components] == [0, 1]


def test_topic_naming_is_separate_from_cluster_identity_and_coherence_is_bounded() -> None:
    items, _ = episodes()
    cluster = SimilarityClusterer().cluster([item.episode_id for item in items], [], threshold=0.9)[0]
    cluster = cluster.model_copy(update={"episode_ids": [item.episode_id for item in items]})
    named = VersionedTopicNamer().name(cluster, ["Second Brain planning", "Second Brain review"])
    assert named.cluster_id == cluster.cluster_id
    assert named.label
    texts = RepresentativeContextSelector().select(named, {item.episode_id: "Second Brain planning" for item in items}, max_items=1)
    decision = HeuristicCoherenceJudge().judge(named, texts)
    assert decision.needs_more_evidence is True


def test_recursive_clustering_has_configurable_stop_depth() -> None:
    items, _ = episodes()
    clusters = RecursiveClusterer().cluster([item.episode_id for item in items], [], threshold=0.9, max_depth=0)
    assert all(cluster.metadata["depth"] == 0 for cluster in clusters)
