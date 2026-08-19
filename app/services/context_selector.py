from collections.abc import Mapping, Sequence
from uuid import UUID

from app.domain.llm import (
    ContextSelectionConfig,
    ContextTask,
    ContextUnit,
    SelectedContext,
)


class ContextSelector:
    """Selects task-specific canonical context without changing its IDs or text."""

    def __init__(self, configurations: Mapping[ContextTask, ContextSelectionConfig]) -> None:
        self.configurations = configurations

    def select(
        self,
        task: ContextTask,
        units: Sequence[ContextUnit],
        anchor_unit_ids: Sequence[UUID],
    ) -> SelectedContext:
        configuration = self.configurations[task]
        ordered = sorted(units, key=lambda unit: (unit.document_id.hex, unit.sequence, str(unit.unit_id)))
        anchors = set(anchor_unit_ids)
        selected = [unit for unit in ordered if unit.unit_id in anchors]

        if configuration.include_adjacent_units and selected:
            documents = {unit.document_id for unit in selected}
            selected_ids = {unit.unit_id for unit in selected}
            for unit in ordered:
                if unit.document_id in documents and any(
                    abs(unit.sequence - anchor.sequence) <= 1 for anchor in selected
                ):
                    selected_ids.add(unit.unit_id)
            selected = [unit for unit in ordered if unit.unit_id in selected_ids]

        if not configuration.include_cross_document_units and selected:
            documents = {unit.document_id for unit in selected}
            selected = [unit for unit in selected if unit.document_id in documents]

        selected = selected[: configuration.max_units]
        selected = _fit_token_budget(selected, configuration.max_tokens)
        return SelectedContext(
            task=task,
            anchor_unit_ids=list(anchor_unit_ids),
            units=selected,
            configuration=configuration,
        )


def _fit_token_budget(units: list[ContextUnit], max_tokens: int) -> list[ContextUnit]:
    result: list[ContextUnit] = []
    used = 0
    for unit in units:
        tokens = _count_tokens(unit.text)
        if result and used + tokens > max_tokens:
            break
        result.append(unit)
        used += tokens
    return result


def _count_tokens(text: str) -> int:
    return len(text.split())
