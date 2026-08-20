from uuid import UUID

from app.domain.integrity import IntegrityCheck, IntegrityReport
from app.ports.canonical_read import CanonicalReadPort
from app.ports.semantic import SemanticReadPort


class OrganizerIntegrityService:
    """Checks derived-object and provenance invariants for one immutable run."""

    def __init__(self, semantic_reader: SemanticReadPort, canonical_reader: CanonicalReadPort) -> None:
        self.semantic_reader = semantic_reader
        self.canonical_reader = canonical_reader

    def validate(self, run_id: UUID, sample_episode_id: UUID | None = None) -> IntegrityReport:
        run = self.semantic_reader.get_run(run_id)
        episodes = self.semantic_reader.get_episodes(run_id)
        memberships = self.semantic_reader.get_episode_memberships(run_id)
        episode_ids = {item.episode_id for item in episodes}
        topic_links = self.semantic_reader.get_episode_topics(run_id)
        topics = self.semantic_reader.get_topics(run_id)
        topic_ids = {item.topic_id for item in topics}
        entity_links = self.semantic_reader.get_episode_entities(run_id)
        entities = self.semantic_reader.get_entities(run_id)
        entity_ids = {item.entity_id for item in entities}
        relations = self.semantic_reader.get_episode_relations(run_id)
        threads = self.semantic_reader.get_threads(run_id)
        thread_ids = {item.thread_id for item in threads}
        thread_links = self.semantic_reader.get_thread_episodes(run_id)
        referenced_unit_ids = {item.canonical_unit_id for item in memberships}
        referenced_unit_ids.update(item.start_unit_id for item in episodes)
        referenced_unit_ids.update(item.end_unit_id for item in episodes)
        referenced_unit_ids.update(unit_id for item in entity_links for unit_id in item.evidence_unit_ids)
        referenced_unit_ids.update(unit_id for item in relations for unit_id in item.evidence_unit_ids)
        canonical_units = {item.unit_id: item for item in self.canonical_reader.get_units_by_ids(list(referenced_unit_ids))}

        checks = [
            IntegrityCheck(name="run_exists", passed=run is not None, detail="Organizer run exists."),
            IntegrityCheck(name="episode_memberships", passed=all(link.episode_id in episode_ids and link.canonical_unit_id in canonical_units for link in memberships), detail="Episode memberships resolve to episodes and canonical units."),
            IntegrityCheck(name="episode_boundaries", passed=all(self._episode_boundary_resolves(item, canonical_units) for item in episodes), detail="Episode boundaries resolve to canonical units in the episode document."),
            IntegrityCheck(name="topic_memberships", passed=all(link.topic_id in topic_ids and link.episode_id in episode_ids for link in topic_links), detail="Topic memberships resolve to topics and episodes."),
            IntegrityCheck(name="entity_mentions", passed=all(link.entity_id in entity_ids and link.episode_id in episode_ids and set(link.evidence_unit_ids).issubset(canonical_units) for link in entity_links), detail="Entity mentions resolve to entities, episodes and evidence."),
            IntegrityCheck(name="relations", passed=all(item.from_episode_id in episode_ids and item.to_episode_id in episode_ids and set(item.evidence_unit_ids).issubset(canonical_units) for item in relations), detail="Relations resolve to episodes and evidence."),
            IntegrityCheck(name="thread_memberships", passed=all(link.thread_id in thread_ids and link.episode_id in episode_ids for link in thread_links) and len({(link.thread_id, link.episode_id) for link in thread_links}) == len(thread_links), detail="Thread memberships are connected and unique."),
            IntegrityCheck(name="topic_hierarchy", passed=self._topic_hierarchy_is_acyclic(topics), detail="Topic parent relationships contain no cycle."),
        ]
        sample = sample_episode_id or (episodes[0].episode_id if episodes else None)
        if sample:
            episode = next((item for item in episodes if item.episode_id == sample), None)
            sample_units = [item for item in memberships if item.episode_id == sample]
            round_trip = bool(episode and sample_units and all(self.canonical_reader.get_unit(item.canonical_unit_id) is not None for item in sample_units) and self.canonical_reader.get_document(episode.document_id) is not None)
            checks.append(IntegrityCheck(name="provenance_round_trip", passed=round_trip, detail="Sample episode resolves to canonical units, document and source reference."))
        return IntegrityReport(organizer_run_id=run_id, checks=checks, sample_episode_id=sample)

    @staticmethod
    def _topic_hierarchy_is_acyclic(topics) -> bool:
        parents = {topic.topic_id: topic.parent_topic_id for topic in topics}
        for topic_id in parents:
            seen = set()
            current = topic_id
            while current is not None:
                if current in seen:
                    return False
                seen.add(current)
                current = parents.get(current)
        return True

    def _episode_boundary_resolves(self, episode, canonical_units) -> bool:
        start = canonical_units.get(episode.start_unit_id)
        end = canonical_units.get(episode.end_unit_id)
        return bool(start and end and start.document_id == episode.document_id and end.document_id == episode.document_id)
