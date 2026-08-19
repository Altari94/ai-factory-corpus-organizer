from uuid import UUID

from pydantic import BaseModel, Field


class E2ECheck(BaseModel):
    name: str
    passed: bool
    detail: str


class E2EAcceptanceReport(BaseModel):
    organizer_run_id: UUID
    accepted: bool
    checks: list[E2ECheck]


class RealCorpusGateRequest(BaseModel):
    """Explicit operator input; raw chat selection is never inferred by code."""

    organizer_run_id: UUID
    expected_source_ids: list[UUID] = Field(min_length=2)
