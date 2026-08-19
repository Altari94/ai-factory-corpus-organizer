from app.domain.episode_detection import BoundaryCandidate, BoundaryContext
from app.domain.llm import ContextTask, ContextUnit, ModelProfile
from app.services.chunk_builder import ChunkBuilder
from app.services.context_selector import ContextSelector


class BoundaryContextBuilder:
    def __init__(self, selector: ContextSelector, chunk_builder: ChunkBuilder) -> None:
        self.selector = selector
        self.chunk_builder = chunk_builder

    def build(
        self,
        candidate: BoundaryCandidate,
        units: list[ContextUnit],
        profile: ModelProfile,
    ) -> BoundaryContext:
        selected = self.selector.select(
            ContextTask.BOUNDARY_JUDGE,
            units,
            [candidate.left_unit_id, candidate.right_unit_id],
        )
        chunks = self.chunk_builder.build(selected, profile)
        selected_ids = {unit.unit_id for unit in selected.units}
        required_ids = {candidate.left_unit_id, candidate.right_unit_id}
        if not required_ids.issubset(selected_ids):
            raise ValueError("boundary context selection must retain both candidate units")
        return BoundaryContext(
            candidate_id=candidate.candidate_id,
            chunks=chunks,
            canonical_unit_ids=[unit.unit_id for unit in selected.units],
        )
