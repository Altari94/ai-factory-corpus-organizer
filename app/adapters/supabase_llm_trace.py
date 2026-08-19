from collections.abc import Sequence
from supabase import Client

from app.domain.llm import LLMExecutionTrace, StructuredDecision


class SupabaseLLMTraceAdapter:
    """Persists provider traces and validated decisions without exposing DB types to the core."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def save_trace(self, trace: LLMExecutionTrace) -> None:
        self.client.table("llm_execution_traces").upsert(_trace_dump(trace)).execute()

    def save_decision(self, decision: StructuredDecision) -> None:
        self.client.table("structured_decisions").upsert(_decision_dump(decision)).execute()


def _trace_dump(trace: LLMExecutionTrace) -> dict:
    return trace.model_dump(mode="json")


def _decision_dump(decision: StructuredDecision) -> dict:
    data = decision.model_dump(mode="json")
    data["decision"] = decision.decision.model_dump(mode="json")
    return data
