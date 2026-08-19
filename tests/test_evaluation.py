from app.services.evaluation import compare_snapshots, evaluate_relations, snapshot


def test_same_thread_precision_is_measured_separately_from_all_relations() -> None:
    result = evaluate_relations(
        {"a:b": "SAME_THREAD", "a:c": "RELATED"},
        {"a:b": "SAME_THREAD", "a:c": "SAME_THREAD"},
    )

    assert result.same_thread.precision == 0.5
    assert result.all_relations.precision == 0.5


def test_regression_gate_rejects_false_thread_merges() -> None:
    common = dict(
        expected_boundaries={"b"}, actual_boundaries={"b"},
        expected_relations={"a:b": "SAME_THREAD"},
        expected_topics={"factory": {"a", "b"}}, actual_topics={"candidate": {"a", "b"}},
    )
    baseline = snapshot("baseline", actual_relations={"a:b": "SAME_THREAD"}, **common)
    candidate = snapshot("candidate", actual_relations={"a:b": "SAME_THREAD", "a:c": "SAME_THREAD"}, **common)

    report = compare_snapshots(baseline, candidate)

    assert report.accepted is False
    assert "same-thread precision regressed" in report.regressions
