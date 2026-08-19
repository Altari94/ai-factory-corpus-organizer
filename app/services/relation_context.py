from collections.abc import Sequence
from uuid import UUID

from app.domain.llm import ContextSelectionConfig, ContextTask, ContextUnit
from app.services.context_selector import ContextSelector


class RelationContextSelector:
    def __init__(self, selector: ContextSelector) -> None:
        self.selector = selector

    def select(self, source_unit_ids: Sequence[UUID], candidate_unit_ids: Sequence[UUID], units: Sequence[ContextUnit]):
        return self.selector.select(
            ContextTask.RELATION_JUDGE,
            units,
            [*source_unit_ids, *candidate_unit_ids],
        )
