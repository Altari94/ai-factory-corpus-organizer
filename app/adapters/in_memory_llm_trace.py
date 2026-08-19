from uuid import UUID

from app.domain.llm import LLMExecutionTrace, StructuredDecision


class InMemoryLLMTraceAdapter:
    """Run-local trace store for tests; a durable adapter can implement the same port later."""

    def __init__(self) -> None:
        self.traces: dict[UUID, LLMExecutionTrace] = {}
        self.decisions: dict[UUID, StructuredDecision] = {}

    def save_trace(self, trace: LLMExecutionTrace) -> None:
        self.traces[trace.trace_id] = trace

    def save_decision(self, decision: StructuredDecision) -> None:
        self.decisions[decision.decision_id] = decision
