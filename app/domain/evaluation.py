from pydantic import BaseModel, Field


class PrecisionRecall(BaseModel):
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)


class BoundaryEvaluation(BaseModel):
    metrics: PrecisionRecall


class RelationEvaluation(BaseModel):
    same_thread: PrecisionRecall
    all_relations: PrecisionRecall


class TopicQualityEvaluation(BaseModel):
    matched_episode_count: int = Field(ge=0)
    expected_episode_count: int = Field(ge=0)
    assignment_coverage: float = Field(ge=0, le=1)
    mean_topic_jaccard: float = Field(ge=0, le=1)
    unassigned_episode_count: int = Field(ge=0)


class EvaluationSnapshot(BaseModel):
    version: str
    boundary: BoundaryEvaluation
    relation: RelationEvaluation
    topic_quality: TopicQualityEvaluation


class RegressionPolicy(BaseModel):
    min_same_thread_precision: float = Field(default=0.9, ge=0, le=1)
    max_precision_drop: float = Field(default=0.0, ge=0, le=1)
    max_f1_drop: float = Field(default=0.05, ge=0, le=1)


class RegressionReport(BaseModel):
    baseline_version: str
    candidate_version: str
    accepted: bool
    regressions: list[str]
