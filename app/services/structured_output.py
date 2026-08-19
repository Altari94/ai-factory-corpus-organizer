import json
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.domain.llm import (
    BoundaryDecision,
    ContextTask,
    LLMResponse,
    RelationDecision,
    StructuredDecision,
)


class RetryableStructuredOutputError(ValueError):
    """The model response is invalid and may be retried with the same task."""


class StructuredOutputValidator:
    def validate(
        self,
        response: LLMResponse,
        *,
        task: ContextTask,
        organizer_run_id: UUID,
        trace_id: UUID,
        prompt_id: str,
        prompt_version: str,
        canonical_unit_ids: list[UUID],
    ) -> StructuredDecision:
        try:
            payload = json.loads(response.raw_output)
            decision = (
                BoundaryDecision.model_validate(payload)
                if task == ContextTask.BOUNDARY_JUDGE
                else RelationDecision.model_validate(payload)
            )
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise RetryableStructuredOutputError("Invalid structured LLM output") from exc

        referenced_ids = _decision_unit_ids(decision)
        if not set(referenced_ids).issubset(set(canonical_unit_ids)):
            raise RetryableStructuredOutputError("Decision references unknown Canonical Unit IDs")

        return StructuredDecision(
            decision_id=uuid4(),
            organizer_run_id=organizer_run_id,
            trace_id=trace_id,
            task=task,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            model_profile_id=response.model_profile_id,
            canonical_unit_ids=canonical_unit_ids,
            decision=decision,
        )


def _decision_unit_ids(decision: BoundaryDecision | RelationDecision) -> list[UUID]:
    if isinstance(decision, BoundaryDecision):
        return [decision.left_unit_id, decision.right_unit_id]
    return [decision.from_unit_id, decision.to_unit_id]
