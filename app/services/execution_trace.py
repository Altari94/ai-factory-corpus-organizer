from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.llm import (
    ContextTask,
    LLMExecutionStatus,
    LLMExecutionTrace,
    LLMRequest,
    LLMResponse,
    StructuredDecision,
)


class ExecutionTraceService:
    def start(self, request: LLMRequest, organizer_run_id: UUID) -> LLMExecutionTrace:
        return LLMExecutionTrace(
            trace_id=uuid4(),
            organizer_run_id=organizer_run_id,
            task=request.prompt.task,
            model_profile_id=request.profile.profile_id,
            model_name=request.profile.model_name,
            prompt_id=request.prompt.prompt_id,
            prompt_version=request.prompt.prompt_version,
            request_id=request.request_id,
            attempt=request.attempt,
            canonical_unit_ids=request.prompt.source_unit_ids,
            started_at=datetime.now(timezone.utc),
            status=LLMExecutionStatus.STARTED,
        )

    def succeed(
        self,
        trace: LLMExecutionTrace,
        response: LLMResponse,
        decision: StructuredDecision,
    ) -> LLMExecutionTrace:
        return trace.model_copy(
            update={
                "finished_at": datetime.now(timezone.utc),
                "status": LLMExecutionStatus.SUCCEEDED,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "retry_count": response.retry_count,
                "raw_output": response.raw_output,
                "structured_decision_id": decision.decision_id,
            }
        )

    def retryable_failure(
        self, trace: LLMExecutionTrace, response: LLMResponse, error: str
    ) -> LLMExecutionTrace:
        return trace.model_copy(
            update={
                "finished_at": datetime.now(timezone.utc),
                "status": LLMExecutionStatus.RETRYABLE_FAILURE,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "raw_output": response.raw_output,
                "error": error,
            }
        )

    def failed(self, trace: LLMExecutionTrace, error: str) -> LLMExecutionTrace:
        return trace.model_copy(
            update={
                "finished_at": datetime.now(timezone.utc),
                "status": LLMExecutionStatus.FAILED,
                "error": error,
            }
        )
