import re
from collections.abc import Sequence
from uuid import UUID, uuid5

from app.domain.discovery import EntityExtractionResult, EntityMention
from app.domain.llm import ContextUnit
from app.domain.semantic import Episode


class HeuristicEntityExtractor:
    """Deterministic baseline; it discovers candidates without fixed categories."""

    def __init__(self, algorithm_version: str = "heuristic-entity-v1") -> None:
        self.algorithm_version = algorithm_version

    def extract(self, episode: Episode, units: Sequence[ContextUnit]) -> EntityExtractionResult:
        mentions: list[EntityMention] = []
        for unit in units:
            for match in re.finditer(r"\b[A-ZÄÖÜ][\wÄÖÜäöüß-]{2,}(?:\s+[A-ZÄÖÜ][\wÄÖÜäöüß-]{2,})*", unit.text):
                name = match.group(0).strip()
                entity_id = uuid5(episode.organizer_run_id, f"entity:{name.casefold()}")
                if not any(item.entity_id == entity_id and item.episode_id == episode.episode_id for item in mentions):
                    mentions.append(EntityMention(
                        entity_id=entity_id,
                        canonical_name=name,
                        episode_id=episode.episode_id,
                        evidence_unit_ids=[unit.unit_id],
                    ))
        return EntityExtractionResult(mentions=mentions, algorithm_version=self.algorithm_version)
