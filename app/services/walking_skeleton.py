from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid5

from app.domain.canonical import CanonicalDocument, CanonicalRun, CanonicalUnit
from app.domain.semantic import Episode, EpisodeStatus, OrganizerRun
from app.ports.canonical_read import CanonicalReadPort
from app.ports.semantic import SemanticWritePort


@dataclass(frozen=True)
class LoadedCanonicalSource:
    run: CanonicalRun
    document: CanonicalDocument
    units: list[CanonicalUnit]


class CorpusLoader:
    """Loads several sources through CanonicalReadPort only."""

    def __init__(self, canonical_reader: CanonicalReadPort) -> None:
        self.canonical_reader = canonical_reader

    def load(
        self, source_ids: list[UUID], schema_version: str | None = None
    ) -> list[LoadedCanonicalSource]:
        loaded: list[LoadedCanonicalSource] = []
        for source_id in source_ids:
            run = self.canonical_reader.get_current_successful_run(source_id, schema_version)
            if run is None:
                continue
            units = self.canonical_reader.get_units(run.run_id)
            if not units:
                continue
            document = self.canonical_reader.get_document(units[0].document_id)
            if document is not None:
                loaded.append(LoadedCanonicalSource(run, document, units))
        return loaded


class TrivialEpisodeDetector:
    """Walking skeleton: one canonical MESSAGE becomes one Episode."""

    def detect(
        self, organizer_run: OrganizerRun, sources: list[LoadedCanonicalSource]
    ) -> list[Episode]:
        episodes: list[Episode] = []
        for source in sources:
            messages = [unit for unit in source.units if unit.unit_type == "MESSAGE"]
            for message in messages:
                episodes.append(
                    Episode(
                        organizer_run_id=organizer_run.organizer_run_id,
                        episode_id=uuid5(
                            organizer_run.organizer_run_id, f"episode:{message.unit_id}"
                        ),
                        document_id=source.document.document_id,
                        start_unit_id=message.unit_id,
                        end_unit_id=message.unit_id,
                        sequence=message.sequence,
                        status=EpisodeStatus.CONFIRMED,
                    )
                )
        return episodes


class WalkingSkeletonPipeline:
    """First complete F0.4 path from Canonical Read Port to Semantic Store."""

    def __init__(
        self,
        canonical_reader: CanonicalReadPort,
        semantic_writer: SemanticWritePort,
    ) -> None:
        self.loader = CorpusLoader(canonical_reader)
        self.semantic_writer = semantic_writer
        self.detector = TrivialEpisodeDetector()

    def run(
        self,
        organizer_run: OrganizerRun,
        source_ids: list[UUID],
        schema_version: str | None = None,
    ) -> list[Episode]:
        sources = self.loader.load(source_ids, schema_version)
        self.semantic_writer.create_run(organizer_run)
        episodes = self.detector.detect(organizer_run, sources)
        self.semantic_writer.write_episodes(episodes)
        self.semantic_writer.complete_run(
            organizer_run.organizer_run_id, datetime.now(timezone.utc)
        )
        return episodes
