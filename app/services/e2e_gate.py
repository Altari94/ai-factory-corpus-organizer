from collections.abc import Mapping
from uuid import UUID

from app.domain.e2e import E2EAcceptanceReport, E2ECheck
from app.ports.semantic import SemanticReadPort


class EndToEndAcceptanceGate:
    """Read-only invariant checker for a completed organizer run."""

    def __init__(self, semantic_reader: SemanticReadPort) -> None:
        self.semantic_reader = semantic_reader

    def validate(
        self,
        organizer_run_id: UUID,
        *,
        canonical_unit_to_source: Mapping[UUID, UUID],
        expected_source_ids: set[UUID],
    ) -> E2EAcceptanceReport:
        run = self.semantic_reader.get_run(organizer_run_id)
        episodes = self.semantic_reader.get_episodes(organizer_run_id)
        relations = self.semantic_reader.get_episode_relations(organizer_run_id)
        episode_entities = self.semantic_reader.get_episode_entities(organizer_run_id)
        topics = self.semantic_reader.get_topics(organizer_run_id)
        episode_topics = self.semantic_reader.get_episode_topics(organizer_run_id)
        threads = self.semantic_reader.get_threads(organizer_run_id)
        thread_episodes = self.semantic_reader.get_thread_episodes(organizer_run_id)
        episode_ids = {episode.episode_id for episode in episodes}
        all_evidence = [unit_id for relation in relations for unit_id in relation.evidence_unit_ids]
        all_evidence.extend(unit_id for link in episode_entities for unit_id in link.evidence_unit_ids)
        source_ids = {canonical_unit_to_source.get(episode.start_unit_id) for episode in episodes}
        source_ids.discard(None)
        checks = [
            E2ECheck(name="run_succeeded", passed=bool(run and run.status.value == "SUCCEEDED"), detail="Organizer run must be succeeded."),
            E2ECheck(name="multiple_sources", passed=expected_source_ids.issubset(source_ids), detail="All explicitly selected sources are represented."),
            E2ECheck(name="episode_provenance", passed=all(episode.start_unit_id in canonical_unit_to_source and episode.end_unit_id in canonical_unit_to_source for episode in episodes), detail="Every episode resolves to canonical units and a source."),
            E2ECheck(
                name="relation_evidence",
                passed=all(relation.evidence_unit_ids for relation in relations)
                and all(link.evidence_unit_ids for link in episode_entities)
                and all(unit_id in canonical_unit_to_source for unit_id in all_evidence),
                detail="All relation/entity evidence is present and resolves to canonical units.",
            ),
            E2ECheck(name="topic_memberships", passed=all(link.episode_id in episode_ids for link in episode_topics) and bool(topics), detail="Topics reference existing episodes."),
            E2ECheck(name="thread_order", passed=all(link.episode_id in episode_ids and link.sequence >= 0 for link in thread_episodes) and len({(link.thread_id, link.episode_id) for link in thread_episodes}) == len(thread_episodes), detail="Thread memberships are ordered and unique."),
            E2ECheck(name="threads_available", passed=bool(threads), detail="At least one reconstructed thread exists."),
        ]
        return E2EAcceptanceReport(
            organizer_run_id=organizer_run_id,
            accepted=all(check.passed for check in checks),
            checks=checks,
        )
