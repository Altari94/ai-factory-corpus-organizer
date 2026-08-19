import json
from pathlib import Path


GOLDEN_CORPUS = Path(__file__).parents[1] / "evaluation" / "golden_corpus.v1.json"


def test_golden_corpus_is_versioned_and_evaluable() -> None:
    corpus = json.loads(GOLDEN_CORPUS.read_text(encoding="utf-8"))

    assert corpus["version"] == "1.0.0"
    assert corpus["status"] == "DRAFT_GROUND_TRUTH"
    assert corpus["ground_truth_schema"]["provenance_required"] is True
    assert len(corpus["cases"]) == 8
    assert all(len(case["sha256"]) == 64 for case in corpus["cases"])
    assert all("difficulty_tags" in case for case in corpus["cases"])
    assert all("manual_annotation" in case for case in corpus["cases"])
