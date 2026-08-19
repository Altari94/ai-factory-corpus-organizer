import re
from collections.abc import Sequence
from uuid import uuid4

from app.domain.episode_detection import BoundaryCandidate, BoundaryCandidateConfig
from app.domain.llm import ContextUnit


class BoundaryCandidateDetector:
    """Algorithmic shortlist; unremarkable boundaries never reach the LLM."""

    def __init__(self, configuration: BoundaryCandidateConfig) -> None:
        self.configuration = configuration

    def detect(self, units: Sequence[ContextUnit]) -> list[BoundaryCandidate]:
        ordered = sorted(units, key=lambda unit: (unit.document_id.hex, unit.sequence, str(unit.unit_id)))
        candidates: list[BoundaryCandidate] = []
        for left, right in zip(ordered, ordered[1:]):
            if left.document_id != right.document_id:
                continue
            signals = {
                "speaker_change": float(bool(left.speaker and right.speaker and left.speaker != right.speaker)),
                "lexical_shift": _lexical_shift(left.text, right.text),
                "sequence_gap": min(abs(right.sequence - left.sequence - 1), 1),
            }
            score = (
                signals["speaker_change"] * self.configuration.speaker_change_weight
                + signals["lexical_shift"] * self.configuration.lexical_shift_weight
                + signals["sequence_gap"] * self.configuration.sequence_gap_weight
            )
            if score < self.configuration.threshold:
                continue
            candidates.append(
                BoundaryCandidate(
                    candidate_id=uuid4(),
                    left_unit_id=left.unit_id,
                    right_unit_id=right.unit_id,
                    score=min(score, 1.0),
                    threshold=self.configuration.threshold,
                    signals=signals,
                    evidence_unit_ids=[left.unit_id, right.unit_id],
                )
            )
        return candidates


def _lexical_shift(left: str, right: str) -> float:
    left_words = set(re.findall(r"\w+", left.lower()))
    right_words = set(re.findall(r"\w+", right.lower()))
    if not left_words or not right_words:
        return 1.0
    overlap = len(left_words & right_words) / len(left_words | right_words)
    return 1.0 - overlap

