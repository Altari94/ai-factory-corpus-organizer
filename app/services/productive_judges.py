"""Provider-neutral orchestration for the productive semantic judges.

The service knows only the LLMPort and domain contracts. OpenAI-specific
behavior remains in the adapter and can be replaced by InMemoryLLMAdapter in
tests.
"""

from collections.abc import Sequence
from uuid import UUID, uuid4

from app.domain.discovery import CoherenceDecision as DiscoveryCoherenceDecision
from app.domain.discovery import RelationDecision as DiscoveryRelationDecision
from app.domain.discovery import TopicCluster
from app.domain.llm import (
    CoherenceDecision,
    ContextSelectionConfig,
    ContextTask,
    ContextUnit,
    LLMRequest,
    ModelProfile,
    PromptDefinition,
    RelationDecision,
    SelectedContext,
    TopicNamingDecision,
)
from app.domain.semantic import Episode
from app.ports.llm import LLMPort, LLMProviderError, LLMTracePort
from app.services.chunk_builder import ChunkBuilder
from app.services.execution_trace import ExecutionTraceService
from app.services.prompt_builder import PromptBuilder
from app.services.structured_output import RetryableStructuredOutputError, StructuredOutputValidator


class ProductiveJudgeError(RuntimeError):
    """A provider result was unavailable or failed structured validation."""


class ProductiveSemanticJudges:
    def __init__(
        self,
        llm: LLMPort,
        profile: ModelProfile,
        *,
        trace_store: LLMTracePort | None = None,
        prompt_version: str = "semantic-judges-v1",
        max_structured_attempts: int = 2,
    ) -> None:
        self.llm = llm
        self.profile = profile
        self.trace_store = trace_store
        self.prompt_version = prompt_version
        self.max_structured_attempts = max(1, max_structured_attempts)
        self.trace_service = ExecutionTraceService()
        self.validator = StructuredOutputValidator()

    def judge_relation(
        self,
        source: Episode,
        candidate: Episode,
        units: Sequence[ContextUnit],
        organizer_run_id: UUID,
    ) -> DiscoveryRelationDecision:
        source_ids = [source.start_unit_id, source.end_unit_id, candidate.start_unit_id, candidate.end_unit_id]
        context = [unit for unit in units if unit.unit_id in source_ids]
        request, canonical_ids = self._request(ContextTask.RELATION_JUDGE, context, source_ids, "relation")
        response, decision = self._call(request, organizer_run_id, canonical_ids)
        if not isinstance(decision, RelationDecision):
            raise ProductiveJudgeError("Relation judge returned the wrong decision type")
        evidence = [decision.from_unit_id, decision.to_unit_id]
        return DiscoveryRelationDecision(
            from_episode_id=source.episode_id,
            to_episode_id=candidate.episode_id,
            relation_type=decision.relation_type,
            confidence=decision.confidence,
            evidence_unit_ids=evidence,
        )

    def name_topic(
        self,
        cluster: TopicCluster,
        representative_texts: Sequence[str],
        organizer_run_id: UUID,
    ) -> TopicCluster:
        context = self._cluster_context(cluster, representative_texts)
        request, canonical_ids = self._request(ContextTask.TOPIC_NAMING, context, cluster.episode_ids, "topic-naming")
        _, decision = self._call(request, organizer_run_id, canonical_ids)
        if not isinstance(decision, TopicNamingDecision) or decision.cluster_id != cluster.cluster_id:
            raise ProductiveJudgeError("Topic naming returned an invalid cluster identity")
        metadata = {**cluster.metadata, "prompt_version": self.prompt_version, "model_profile_id": self.profile.profile_id}
        return cluster.model_copy(update={"label": decision.topic_name, "metadata": {**metadata, "description": decision.topic_description}})

    def judge_coherence(
        self,
        cluster: TopicCluster,
        representative_texts: Sequence[str],
        organizer_run_id: UUID,
    ) -> DiscoveryCoherenceDecision:
        context = self._cluster_context(cluster, representative_texts)
        request, canonical_ids = self._request(ContextTask.COHERENCE_JUDGE, context, cluster.episode_ids, "coherence")
        _, decision = self._call(request, organizer_run_id, canonical_ids)
        if not isinstance(decision, CoherenceDecision) or decision.cluster_id != cluster.cluster_id:
            raise ProductiveJudgeError("Coherence judge returned an invalid cluster identity")
        evidence = [item for item in decision.evidence_episode_ids if item in cluster.episode_ids]
        if not evidence:
            raise ProductiveJudgeError("Coherence judge returned evidence outside the cluster")
        return DiscoveryCoherenceDecision(
            cluster_id=cluster.cluster_id,
            coherent=decision.verdict == "KEEP",
            confidence=decision.confidence,
            evidence_episode_ids=evidence,
            needs_more_evidence=decision.needs_more_evidence,
        )

    def _request(
        self,
        task: ContextTask,
        context: Sequence[ContextUnit],
        source_ids: Sequence[UUID],
        prompt_id: str,
    ) -> tuple[LLMRequest, list[UUID]]:
        definition = PromptDefinition(
            prompt_id=prompt_id,
            version=self.prompt_version,
            task=task,
            system_template=_system_prompt(task),
            user_template="{context}",
        )
        chunks = ChunkBuilder().build(
            SelectedContext(
                task=task,
                anchor_unit_ids=list(source_ids),
                units=list(context),
                configuration=ContextSelectionConfig(
                    max_units=max(1, len(context)), max_tokens=self.profile.chunk_max_tokens
                ),
            ),
            self.profile,
        )
        if len(chunks) != 1:
            raise ProductiveJudgeError(
                f"{task.value} context exceeds the configured model chunk limit; select fewer representatives"
            )
        prompt = PromptBuilder().build(definition, chunks[0])
        return LLMRequest(request_id=uuid4(), profile=self.profile, prompt=prompt, attempt=1), list(prompt.source_unit_ids)

    def _call(self, request: LLMRequest, organizer_run_id: UUID, canonical_ids: list[UUID]):
        last_error: Exception | None = None
        for attempt in range(1, self.max_structured_attempts + 1):
            current_request = request.model_copy(update={"attempt": attempt})
            trace = self.trace_service.start(current_request, organizer_run_id)
            try:
                response = self.llm.generate(current_request)
                structured = self.validator.validate(
                    response,
                    task=current_request.prompt.task,
                    organizer_run_id=organizer_run_id,
                    trace_id=trace.trace_id,
                    prompt_id=current_request.prompt.prompt_id,
                    prompt_version=current_request.prompt.prompt_version,
                    canonical_unit_ids=canonical_ids,
                )
            except (RetryableStructuredOutputError, ValueError, LLMProviderError) as exc:
                last_error = exc
                failed = self.trace_service.failed(trace, str(exc))
                if self.trace_store:
                    self.trace_store.save_trace(failed)
                if attempt < self.max_structured_attempts and isinstance(exc, RetryableStructuredOutputError):
                    continue
                raise ProductiveJudgeError(str(exc)) from exc
            completed = self.trace_service.succeed(trace, response, structured)
            if self.trace_store:
                self.trace_store.save_decision(structured)
                self.trace_store.save_trace(completed)
            return response, structured.decision
        raise ProductiveJudgeError(str(last_error or "LLM judge failed"))

    @staticmethod
    def _text_context(ids: Sequence[UUID], texts: Sequence[str]) -> list[ContextUnit]:
        return [ContextUnit(unit_id=ids[index], document_id=ids[index], unit_type="EPISODE", sequence=index, text=text) for index, text in enumerate(texts) if index < len(ids)]

    @staticmethod
    def _cluster_context(cluster: TopicCluster, texts: Sequence[str]) -> list[ContextUnit]:
        return [
            ContextUnit(
                unit_id=episode_id,
                document_id=episode_id,
                unit_type="EPISODE",
                sequence=index,
                text=f"Cluster ID: {cluster.cluster_id}\nEpisode ID: {episode_id}\nEvidence: {text}",
            )
            for index, (episode_id, text) in enumerate(zip(cluster.episode_ids, texts, strict=False))
        ]


def _system_prompt(task: ContextTask) -> str:
    if task == ContextTask.RELATION_JUDGE:
        return "Decide relation conservatively. Shared entity words alone are not enough for SAME_THREAD. Return JSON only."
    if task == ContextTask.TOPIC_NAMING:
        return "Name and describe the supplied cluster only. Do not change membership. Return JSON only."
    return "Judge cluster coherence from representative evidence. Be conservative and return JSON only."
