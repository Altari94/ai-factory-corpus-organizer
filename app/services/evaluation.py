from collections.abc import Mapping, Sequence

from app.domain.evaluation import (
    BoundaryEvaluation,
    EvaluationSnapshot,
    PrecisionRecall,
    RegressionPolicy,
    RegressionReport,
    RelationEvaluation,
    TopicQualityEvaluation,
)


def precision_recall(expected: set[str], actual: set[str]) -> PrecisionRecall:
    true_positive = len(expected & actual)
    false_positive = len(actual - expected)
    false_negative = len(expected - actual)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PrecisionRecall(
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def evaluate_boundaries(expected_new_episode_unit_ids: set[str], actual_new_episode_unit_ids: set[str]) -> BoundaryEvaluation:
    return BoundaryEvaluation(metrics=precision_recall(expected_new_episode_unit_ids, actual_new_episode_unit_ids))


def evaluate_relations(
    expected_relations: Mapping[str, str], actual_relations: Mapping[str, str]
) -> RelationEvaluation:
    expected_all = {f"{key}:{value}" for key, value in expected_relations.items()}
    actual_all = {f"{key}:{value}" for key, value in actual_relations.items()}
    expected_thread = {key for key, value in expected_relations.items() if value == "SAME_THREAD"}
    actual_thread = {key for key, value in actual_relations.items() if value == "SAME_THREAD"}
    return RelationEvaluation(
        same_thread=precision_recall(expected_thread, actual_thread),
        all_relations=precision_recall(expected_all, actual_all),
    )


def evaluate_topics(
    expected_topics: Mapping[str, set[str]], actual_topics: Mapping[str, set[str]]
) -> TopicQualityEvaluation:
    expected_episode_ids = set().union(*expected_topics.values()) if expected_topics else set()
    actual_episode_ids = set().union(*actual_topics.values()) if actual_topics else set()
    jaccards = []
    for expected_members in expected_topics.values():
        best = max((_jaccard(expected_members, actual_members) for actual_members in actual_topics.values()), default=0.0)
        jaccards.append(best)
    return TopicQualityEvaluation(
        matched_episode_count=len(expected_episode_ids & actual_episode_ids),
        expected_episode_count=len(expected_episode_ids),
        assignment_coverage=len(expected_episode_ids & actual_episode_ids) / len(expected_episode_ids) if expected_episode_ids else 1.0,
        mean_topic_jaccard=sum(jaccards) / len(jaccards) if jaccards else 1.0,
        unassigned_episode_count=len(expected_episode_ids - actual_episode_ids),
    )


def compare_snapshots(
    baseline: EvaluationSnapshot,
    candidate: EvaluationSnapshot,
    policy: RegressionPolicy | None = None,
) -> RegressionReport:
    policy = policy or RegressionPolicy()
    regressions = []
    if candidate.relation.same_thread.precision < policy.min_same_thread_precision:
        regressions.append("same-thread precision is below the required minimum")
    if candidate.relation.same_thread.precision < baseline.relation.same_thread.precision - policy.max_precision_drop:
        regressions.append("same-thread precision regressed")
    if candidate.boundary.metrics.f1 < baseline.boundary.metrics.f1 - policy.max_f1_drop:
        regressions.append("boundary F1 regressed")
    if candidate.topic_quality.mean_topic_jaccard < baseline.topic_quality.mean_topic_jaccard - policy.max_f1_drop:
        regressions.append("topic quality regressed")
    return RegressionReport(
        baseline_version=baseline.version,
        candidate_version=candidate.version,
        accepted=not regressions,
        regressions=regressions,
    )


def snapshot(
    version: str,
    *,
    expected_boundaries: set[str],
    actual_boundaries: set[str],
    expected_relations: Mapping[str, str],
    actual_relations: Mapping[str, str],
    expected_topics: Mapping[str, set[str]],
    actual_topics: Mapping[str, set[str]],
) -> EvaluationSnapshot:
    return EvaluationSnapshot(
        version=version,
        boundary=evaluate_boundaries(expected_boundaries, actual_boundaries),
        relation=evaluate_relations(expected_relations, actual_relations),
        topic_quality=evaluate_topics(expected_topics, actual_topics),
    )


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0
