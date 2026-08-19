from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelProfile(BaseModel):
    """Provider/model capabilities; budgets are configuration, not domain constants."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    provider: str
    model_name: str
    context_window_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    reserved_output_tokens: int = Field(gt=0)
    chunk_target_tokens: int = Field(gt=0)
    chunk_max_tokens: int = Field(gt=0)
    tokenizer: str = "whitespace-v1"
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def budgets_fit_profile(self) -> "ModelProfile":
        if self.reserved_output_tokens >= self.context_window_tokens:
            raise ValueError("reserved output must fit inside the context window")
        if self.chunk_target_tokens > self.chunk_max_tokens:
            raise ValueError("chunk target must not exceed chunk maximum")
        if self.chunk_max_tokens > self.context_window_tokens - self.reserved_output_tokens:
            raise ValueError("chunk maximum must leave room for reserved output")
        return self


class ContextTask(StrEnum):
    BOUNDARY_JUDGE = "BOUNDARY_JUDGE"
    RELATION_JUDGE = "RELATION_JUDGE"


class ContextSelectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_units: int = Field(gt=0)
    max_tokens: int = Field(gt=0)
    include_adjacent_units: bool = True
    include_parent_units: bool = False
    include_cross_document_units: bool = False


class ContextUnit(BaseModel):
    """Canonical content carried into a task-specific context."""

    model_config = ConfigDict(frozen=True)

    unit_id: UUID
    document_id: UUID
    unit_type: str
    sequence: int = Field(ge=0)
    text: str
    parent_unit_id: UUID | None = None
    speaker: str | None = None


class SelectedContext(BaseModel):
    task: ContextTask
    anchor_unit_ids: list[UUID]
    units: list[ContextUnit]
    configuration: ContextSelectionConfig


class ChunkItem(BaseModel):
    unit_id: UUID
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class ContextChunk(BaseModel):
    chunk_id: UUID
    chunk_index: int = Field(ge=0)
    items: list[ChunkItem]
    input_tokens: int = Field(ge=0)
    source_unit_ids: list[UUID]


class PromptDefinition(BaseModel):
    prompt_id: str
    version: str
    task: ContextTask
    system_template: str
    user_template: str


class BuiltPrompt(BaseModel):
    prompt_id: str
    prompt_version: str
    task: ContextTask
    system: str
    user: str
    source_unit_ids: list[UUID]


class LLMRequest(BaseModel):
    request_id: UUID
    profile: ModelProfile
    prompt: BuiltPrompt
    attempt: int = Field(ge=1)


class LLMResponse(BaseModel):
    request_id: UUID
    model_profile_id: str
    model_name: str
    raw_output: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    provider_request_id: str | None = None


class BoundaryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_type: Literal["BOUNDARY"] = "BOUNDARY"
    left_unit_id: UUID
    right_unit_id: UUID
    boundary: Literal["SAME_EPISODE", "NEW_EPISODE", "UNCERTAIN"]
    confidence: float = Field(ge=0, le=1)


class RelationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_type: Literal["RELATION"] = "RELATION"
    from_unit_id: UUID
    to_unit_id: UUID
    relation_type: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class StructuredDecision(BaseModel):
    """Validated result with model and prompt provenance attached."""

    decision_id: UUID
    organizer_run_id: UUID
    trace_id: UUID
    task: ContextTask
    prompt_id: str
    prompt_version: str
    model_profile_id: str
    canonical_unit_ids: list[UUID]
    decision: BoundaryDecision | RelationDecision


class LLMExecutionStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    FAILED = "FAILED"


class LLMExecutionTrace(BaseModel):
    trace_id: UUID
    organizer_run_id: UUID
    task: ContextTask
    model_profile_id: str
    model_name: str
    prompt_id: str
    prompt_version: str
    request_id: UUID
    attempt: int = Field(ge=1)
    canonical_unit_ids: list[UUID]
    started_at: datetime
    finished_at: datetime | None = None
    status: LLMExecutionStatus
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    raw_output: str | None = None
    structured_decision_id: UUID | None = None
    error: str | None = None
