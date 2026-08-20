from uuid import UUID

from pydantic import BaseModel, Field


class IntegrityCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class IntegrityReport(BaseModel):
    organizer_run_id: UUID
    checks: list[IntegrityCheck] = Field(default_factory=list)
    sample_episode_id: UUID | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)
