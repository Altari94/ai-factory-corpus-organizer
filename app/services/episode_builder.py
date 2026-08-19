from collections.abc import Sequence
from uuid import UUID, uuid5

from app.domain.episode_detection import EpisodeBuildResult, EpisodeMembership
from app.domain.llm import BoundaryDecision, ContextUnit
from app.domain.semantic import Episode, EpisodeStatus


class EpisodeBuilder:
    """Builds ordered, non-overlapping episode spans from confirmed boundaries."""

    def build(
        self,
        organizer_run_id: UUID,
        units: Sequence[ContextUnit],
        decisions: Sequence[BoundaryDecision],
    ) -> EpisodeBuildResult:
        ordered = sorted(
            [unit for unit in units if unit.unit_type == "MESSAGE"],
            key=lambda unit: (unit.document_id.hex, unit.sequence, str(unit.unit_id)),
        )
        new_episode_starts = {
            decision.right_unit_id
            for decision in decisions
            if decision.boundary == "NEW_EPISODE"
        }
        episodes: list[Episode] = []
        memberships: list[EpisodeMembership] = []
        current: list[ContextUnit] = []
        previous_document = None

        def flush() -> None:
            if not current:
                return
            episode_id = uuid5(
                organizer_run_id,
                f"episode:{current[0].document_id}:{current[0].unit_id}:{current[-1].unit_id}",
            )
            episode = Episode(
                organizer_run_id=organizer_run_id,
                episode_id=episode_id,
                document_id=current[0].document_id,
                start_unit_id=current[0].unit_id,
                end_unit_id=current[-1].unit_id,
                sequence=len([item for item in episodes if item.document_id == current[0].document_id]),
                status=EpisodeStatus.CONFIRMED,
            )
            episodes.append(episode)
            memberships.extend(
                EpisodeMembership(
                    organizer_run_id=organizer_run_id,
                    episode_id=episode_id,
                    canonical_unit_id=unit.unit_id,
                    sequence=index,
                )
                for index, unit in enumerate(current)
            )
            current.clear()

        for unit in ordered:
            if previous_document is not None and unit.document_id != previous_document:
                flush()
            if unit.unit_id in new_episode_starts:
                flush()
            current.append(unit)
            previous_document = unit.document_id
        flush()
        return EpisodeBuildResult(episodes=episodes, memberships=memberships)

