from uuid import UUID, uuid4

from app.domain.episode_detection import BoundaryCandidate, BoundaryContext, BoundaryJudgeResult
from app.domain.llm import LLMRequest, ModelProfile, PromptDefinition
from app.ports.llm import LLMPort
from app.services.execution_trace import ExecutionTraceService
from app.services.prompt_builder import PromptBuilder
from app.services.structured_output import StructuredOutputValidator


class LLMBoundaryJudge:
    def __init__(
        self,
        llm: LLMPort,
        prompt_builder: PromptBuilder,
        validator: StructuredOutputValidator,
        trace_service: ExecutionTraceService,
    ) -> None:
        self.llm = llm
        self.prompt_builder = prompt_builder
        self.validator = validator
        self.trace_service = trace_service

    def judge(
        self,
        candidate: BoundaryCandidate,
        context: BoundaryContext,
        profile: ModelProfile,
        prompt_definition: PromptDefinition,
        organizer_run_id: UUID,
        attempt: int = 1,
    ) -> BoundaryJudgeResult:
        if not context.chunks:
            raise ValueError("boundary context must contain at least one chunk")
        candidate_chunk = next(
            (
                chunk
                for chunk in context.chunks
                if candidate.left_unit_id in chunk.source_unit_ids
                and candidate.right_unit_id in chunk.source_unit_ids
            ),
            None,
        )
        if candidate_chunk is None:
            raise ValueError("boundary candidate units must share one model context chunk")
        prompt = self.prompt_builder.build(prompt_definition, candidate_chunk)
        request = LLMRequest(request_id=uuid4(), profile=profile, prompt=prompt, attempt=attempt)
        trace = self.trace_service.start(request, organizer_run_id)
        response = self.llm.generate(request)
        try:
            decision = self.validator.validate(
                response,
                task=prompt.task,
                organizer_run_id=organizer_run_id,
                trace_id=trace.trace_id,
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.prompt_version,
                canonical_unit_ids=context.canonical_unit_ids,
            )
        except ValueError as error:
            self.trace_service.retryable_failure(trace, response, str(error))
            raise
        completed_trace = self.trace_service.succeed(trace, response, decision)
        return BoundaryJudgeResult(decision=decision.decision, trace=completed_trace)
