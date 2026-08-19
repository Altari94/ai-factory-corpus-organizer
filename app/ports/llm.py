from typing import Protocol, runtime_checkable

from app.domain.llm import LLMExecutionTrace, LLMRequest, LLMResponse, StructuredDecision


class LLMProviderError(RuntimeError):
    """Provider failure after bounded retries; never becomes a semantic decision."""


@runtime_checkable
class LLMPort(Protocol):
    """Provider-neutral boundary; no vendor client leaks into the domain."""

    def generate(self, request: LLMRequest) -> LLMResponse: ...


@runtime_checkable
class LLMTracePort(Protocol):
    def save_trace(self, trace: LLMExecutionTrace) -> None: ...

    def save_decision(self, decision: StructuredDecision) -> None: ...
