"""Builds the F0.6 read model from F0.4 and F0.3 ports only."""

from collections import defaultdict
from uuid import UUID

from app.domain.corpus_read import (
    CorpusCatalogue, CorpusSlice, ContentUnitView, EntityView, EpisodeView,
    SourceReference, ThreadView, TopicDetail, TopicNode,
)
from app.domain.semantic import Episode, OrganizerRun, Topic
from app.ports.canonical_read import CanonicalReadPort
from app.ports.corpus_read import CorpusReadPort
from app.ports.semantic import SemanticReadPort


class CorpusReadService(CorpusReadPort):
    """Provider-neutral projection; no Supabase or OpenAI dependency."""

    def __init__(self, semantic_reader: SemanticReadPort, canonical_reader: CanonicalReadPort) -> None:
        self.semantic_reader = semantic_reader
        self.canonical_reader = canonical_reader

    def _require_run(self, run_id: UUID) -> OrganizerRun:
        run = self.semantic_reader.get_run(run_id)
        if run is None:
            raise LookupError(f"Organizer run not found: {run_id}")
        return run

    def _topic_maps(self, run_id: UUID):
        topics = self.semantic_reader.get_topics(run_id)
        links = self.semantic_reader.get_episode_topics(run_id)
        by_id = {topic.topic_id: topic for topic in topics}
        episodes_by_topic: dict[UUID, list[UUID]] = defaultdict(list)
        for link in links:
            episodes_by_topic[link.topic_id].append(link.episode_id)
        children: dict[UUID, list[UUID]] = defaultdict(list)
        for topic in topics:
            if topic.parent_topic_id in by_id:
                children[topic.parent_topic_id].append(topic.topic_id)
        return topics, by_id, episodes_by_topic, children

    def list_topics(self, run_id: UUID) -> list[TopicNode]:
        self._require_run(run_id)
        topics, _, episodes_by_topic, children = self._topic_maps(run_id)
        return [self._topic_node(topic, episodes_by_topic, children) for topic in sorted(topics, key=lambda item: (item.label.casefold(), str(item.topic_id)))]

    def get_topic(self, run_id: UUID, topic_id: UUID) -> TopicDetail | None:
        self._require_run(run_id)
        topics, by_id, episodes_by_topic, children = self._topic_maps(run_id)
        topic = by_id.get(topic_id)
        if topic is None:
            return None
        episode_ids = list(dict.fromkeys(episodes_by_topic[topic_id]))
        episode_entities = self.semantic_reader.get_episode_entities(run_id)
        thread_links = self.semantic_reader.get_thread_episodes(run_id)
        episode_set = set(episode_ids)
        return TopicDetail(
            **self._topic_node(topic, episodes_by_topic, children).model_dump(),
            episode_ids=episode_ids,
            entity_ids=sorted({link.entity_id for link in episode_entities if link.episode_id in episode_set}, key=str),
            thread_ids=sorted({link.thread_id for link in thread_links if link.episode_id in episode_set}, key=str),
        )

    def get_topic_children(self, run_id: UUID, topic_id: UUID) -> list[TopicNode]:
        self._require_run(run_id)
        topics, by_id, episodes_by_topic, children = self._topic_maps(run_id)
        return [self._topic_node(by_id[child_id], episodes_by_topic, children) for child_id in children.get(topic_id, [])]

    def get_topic_ancestors(self, run_id: UUID, topic_id: UUID) -> list[TopicNode]:
        self._require_run(run_id)
        _, by_id, episodes_by_topic, children = self._topic_maps(run_id)
        result: list[TopicNode] = []
        current = by_id.get(topic_id)
        while current and current.parent_topic_id in by_id:
            current = by_id[current.parent_topic_id]
            result.append(self._topic_node(current, episodes_by_topic, children))
        return list(reversed(result))

    def get_topic_episodes(self, run_id: UUID, topic_id: UUID) -> list[EpisodeView]:
        detail = self.get_topic(run_id, topic_id)
        if detail is None:
            return []
        return [episode for episode_id in detail.episode_ids if (episode := self.get_episode(run_id, episode_id)) is not None]

    def get_episode(self, run_id: UUID, episode_id: UUID) -> EpisodeView | None:
        self._require_run(run_id)
        episode = next((item for item in self.semantic_reader.get_episodes(run_id) if item.episode_id == episode_id), None)
        if episode is None:
            return None
        memberships = sorted((item for item in self.semantic_reader.get_episode_memberships(run_id) if item.episode_id == episode_id), key=lambda item: (item.sequence, str(item.canonical_unit_id)))
        topic_ids = sorted({item.topic_id for item in self.semantic_reader.get_episode_topics(run_id) if item.episode_id == episode_id}, key=str)
        thread_ids = sorted({item.thread_id for item in self.semantic_reader.get_thread_episodes(run_id) if item.episode_id == episode_id}, key=str)
        units: list[ContentUnitView] = []
        provenance: dict[tuple[UUID, UUID], SourceReference] = {}
        for membership in memberships:
            unit = self.canonical_reader.get_unit(membership.canonical_unit_id)
            if unit is None:
                raise LookupError(f"Canonical unit not found: {membership.canonical_unit_id}")
            document = self.canonical_reader.get_document(unit.document_id)
            if document is None:
                raise LookupError(f"Canonical document not found: {unit.document_id}")
            units.append(ContentUnitView(content_unit_id=unit.unit_id, source_id=document.source_id, document_id=unit.document_id, episode_id=episode_id, sequence=unit.sequence, original_timestamp=unit.original_timestamp, source_title=document.title, speaker=unit.speaker, role=unit.role, original_text=unit.text, source_locator=unit.source_locator or unit.source_native_id, topic_ids=topic_ids, thread_ids=thread_ids))
            provenance[(document.source_id, document.document_id)] = SourceReference(source_id=document.source_id, document_id=document.document_id, source_title=document.title)
        timestamp = next((unit.original_timestamp for unit in units if unit.original_timestamp is not None), None)
        return EpisodeView(episode_id=episode.episode_id, document_id=episode.document_id, sequence=episode.sequence, timestamp=timestamp, topic_ids=topic_ids, thread_ids=thread_ids, content_units=units, provenance=list(provenance.values()))

    def get_thread(self, run_id: UUID, thread_id: UUID) -> ThreadView | None:
        self._require_run(run_id)
        thread = next((item for item in self.semantic_reader.get_threads(run_id) if item.thread_id == thread_id), None)
        if thread is None:
            return None
        links = sorted((item for item in self.semantic_reader.get_thread_episodes(run_id) if item.thread_id == thread_id), key=lambda item: (item.sequence, str(item.episode_id)))
        return ThreadView(thread_id=thread.thread_id, label=thread.label, description=thread.description, episode_ids=[link.episode_id for link in links])

    def get_entity(self, run_id: UUID, entity_id: UUID) -> EntityView | None:
        self._require_run(run_id)
        entity = next((item for item in self.semantic_reader.get_entities(run_id) if item.entity_id == entity_id), None)
        if entity is None:
            return None
        links = [item for item in self.semantic_reader.get_episode_entities(run_id) if item.entity_id == entity_id]
        return EntityView(entity_id=entity.entity_id, canonical_name=entity.canonical_name, entity_type=entity.entity_type, episode_ids=sorted({link.episode_id for link in links}, key=str), evidence_unit_ids=sorted({unit_id for link in links for unit_id in link.evidence_unit_ids}, key=str))

    def get_corpus_slice(self, run_id: UUID, topic_id: UUID, include_descendants: bool = True) -> CorpusSlice:
        selected = [topic_id]
        if include_descendants:
            queue = [topic_id]
            while queue:
                children = [topic.topic_id for topic in self.get_topic_children(run_id, queue.pop(0))]
                selected.extend(child for child in children if child not in selected)
                queue.extend(children)
        episode_ids: list[UUID] = []
        for selected_topic in selected:
            detail = self.get_topic(run_id, selected_topic)
            if detail:
                episode_ids.extend(detail.episode_ids)
        episodes = [self.get_episode(run_id, episode_id) for episode_id in dict.fromkeys(episode_ids)]
        ordered = sorted((episode for episode in episodes if episode is not None), key=lambda item: (item.timestamp is None, item.timestamp, str(item.document_id), item.sequence, str(item.episode_id)))
        provenance = [source for episode in ordered for source in episode.provenance]
        unique_provenance = list({(item.source_id, item.document_id): item for item in provenance}.values())
        return CorpusSlice(organizer_run_id=run_id, selected_topic_ids=[topic_id], included_topic_ids=selected, episodes=ordered, provenance=unique_provenance)

    def get_catalogue(self, run_id: UUID) -> CorpusCatalogue:
        return CorpusCatalogue(organizer_run_id=run_id, topics=self.list_topics(run_id))

    @staticmethod
    def _topic_node(topic: Topic, episodes_by_topic, children) -> TopicNode:
        return TopicNode(topic_id=topic.topic_id, label=topic.label, description=topic.description, parent_topic_id=topic.parent_topic_id, child_topic_ids=sorted(children.get(topic.topic_id, []), key=str), episode_count=len(set(episodes_by_topic.get(topic.topic_id, []))))
