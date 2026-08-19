from collections.abc import Sequence
from uuid import UUID

from app.domain.discovery import RelationDecision
from app.domain.llm import ContextUnit
from app.domain.semantic import Episode


class HeuristicRelationJudge:
    """Offline baseline; shared entity words alone never create SAME_THREAD."""

    def judge(self, source: Episode, candidate: Episode, units: Sequence[ContextUnit]) -> RelationDecision:
        source_text = " ".join(unit.text.casefold() for unit in units if unit.unit_id == source.start_unit_id or unit.unit_id == source.end_unit_id)
        candidate_text = " ".join(unit.text.casefold() for unit in units if unit.unit_id == candidate.start_unit_id or unit.unit_id == candidate.end_unit_id)
        source_words = set(source_text.split())
        candidate_words = set(candidate_text.split())
        overlap = len(source_words & candidate_words) / max(1, len(source_words | candidate_words))
        relation = "SAME_THREAD" if overlap >= 0.25 else "UNCERTAIN"
        evidence = [item.unit_id for item in units if item.unit_id in {source.start_unit_id, source.end_unit_id, candidate.start_unit_id, candidate.end_unit_id}]
        return RelationDecision(
            from_episode_id=source.episode_id,
            to_episode_id=candidate.episode_id,
            relation_type=relation,
            confidence=min(1.0, overlap + 0.25),
            evidence_unit_ids=evidence or [source.start_unit_id],
        )
