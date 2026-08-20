from uuid import UUID

from app.domain.semantic_snapshot import SemanticSnapshot, SemanticSnapshotObject
from app.ports.semantic import SemanticReadPort


class SemanticSnapshotNotFoundError(LookupError):
    pass


class SemanticSnapshotBuilder:
    """Projects the semantic contract without exposing persistence tables."""

    def __init__(self, reader: SemanticReadPort) -> None:
        self.reader = reader

    def build(self, organizer_run_id: UUID) -> SemanticSnapshot:
        if self.reader.get_run(organizer_run_id) is None:
            raise SemanticSnapshotNotFoundError(f"Organizer run {organizer_run_id} was not found")
        episodes = self.reader.get_episodes(organizer_run_id)
        topic_memberships = self.reader.get_episode_topics(organizer_run_id)
        thread_memberships = self.reader.get_thread_episodes(organizer_run_id)
        entity_mentions = self.reader.get_episode_entities(organizer_run_id)
        entities = self.reader.get_entities(organizer_run_id)
        entity_names = {item.entity_id: item.canonical_name for item in entities}

        def episode_keywords(episode_id: UUID) -> str | None:
            names = sorted({entity_names[link.entity_id] for link in entity_mentions if link.episode_id == episode_id and link.entity_id in entity_names})
            return ", ".join(names[:12]) or None

        def thread_keywords(thread_id: UUID) -> str | None:
            episode_ids = {link.episode_id for link in thread_memberships if link.thread_id == thread_id}
            names = sorted({entity_names[link.entity_id] for link in entity_mentions if link.episode_id in episode_ids and link.entity_id in entity_names})
            return ", ".join(names[:12]) or None

        return SemanticSnapshot(
            organizer_run_id=organizer_run_id,
            topics=[
                SemanticSnapshotObject(
                    object_id=item.topic_id, object_type="TOPIC", label=item.label,
                    description=item.description,
                    episode_ids=[link.episode_id for link in topic_memberships if link.topic_id == item.topic_id],
                ) for item in self.reader.get_topics(organizer_run_id)
            ],
            threads=[
                SemanticSnapshotObject(
                    object_id=item.thread_id, object_type="THREAD", label=item.label,
                    description=item.description or thread_keywords(item.thread_id),
                    episode_ids=[link.episode_id for link in thread_memberships if link.thread_id == item.thread_id],
                ) for item in self.reader.get_threads(organizer_run_id)
            ],
            entities=[
                SemanticSnapshotObject(
                    object_id=item.entity_id, object_type="ENTITY", label=item.canonical_name,
                    episode_ids=[link.episode_id for link in entity_mentions if link.entity_id == item.entity_id],
                    evidence_unit_ids=[unit_id for link in entity_mentions if link.entity_id == item.entity_id for unit_id in link.evidence_unit_ids],
                ) for item in entities
            ],
            episodes=[
                SemanticSnapshotObject(
                    object_id=item.episode_id, object_type="EPISODE", label=episode_keywords(item.episode_id), episode_ids=[item.episode_id],
                    evidence_unit_ids=[item.start_unit_id, item.end_unit_id], document_id=item.document_id, sequence=item.sequence,
                ) for item in episodes
            ],
            relations=[
                SemanticSnapshotObject(
                    object_id=item.relation_id, object_type=f"RELATION:{item.relation_type}",
                    episode_ids=[item.from_episode_id, item.to_episode_id], evidence_unit_ids=item.evidence_unit_ids,
                ) for item in self.reader.get_episode_relations(organizer_run_id)
            ],
        )
