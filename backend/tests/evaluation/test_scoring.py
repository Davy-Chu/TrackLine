import copy

import pytest

from research.evaluation.prediction_models import SongPrediction
from research.evaluation.scoring import evaluate_song

from .scoring_helpers import gold_benchmark, perfect_prediction, prediction_payload


def test_perfect_prediction_scores_all_supported_metrics() -> None:
    report = evaluate_song(gold_benchmark(), perfect_prediction())

    assert report.versions.precision == 1.0
    assert report.versions.recall == 1.0
    assert report.duplicate_rate.value == 0.0
    assert report.incorrect_merge_rate.value == 0.0
    assert report.fan_edit_false_positive_rate.value == 0.0
    assert report.fan_edit_encounter_coverage.value == 1.0
    assert report.contributors.f1 == 1.0
    assert report.evidence_coverage.value == 1.0
    assert report.differences.f1 == 1.0
    assert report.relationships.f1 == 1.0
    assert report.relationship_certainty_accuracy.value == 1.0
    assert report.diagnostics.indeterminate_gold_item_count == 1


def test_invented_version_lowers_precision() -> None:
    payload = prediction_payload()
    invented = copy.deepcopy(payload["versions"][0])
    invented["prediction_version_id"] = "prediction-invented-version"
    invented["display_label"] = "Invented version"
    invented["match_signals"] = {
        "aliases": ["Invented version"],
        "filenames": [],
        "external_ids": [],
    }
    invented["contributors"] = []
    payload["versions"].append(invented)

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.versions.true_positives == 2
    assert report.versions.false_positives == 1
    assert report.versions.precision == pytest.approx(2 / 3)
    assert report.diagnostics.unmatched_prediction_version_ids == ["prediction-invented-version"]


def test_missed_version_lowers_recall_and_difference_relationship_recall() -> None:
    payload = prediction_payload()
    payload["versions"] = [payload["versions"][1]]
    payload["changes"] = []
    payload["relationships"] = []

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.versions.true_positives == 1
    assert report.versions.false_negatives == 1
    assert report.versions.recall == 0.5
    assert report.differences.recall == 0.0
    assert report.relationships.recall == 0.0


def test_second_prediction_for_same_gold_version_counts_as_duplicate() -> None:
    payload = prediction_payload()
    duplicate = copy.deepcopy(payload["versions"][1])
    duplicate["prediction_version_id"] = "prediction-release-duplicate"
    payload["versions"].append(duplicate)

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.versions.true_positives == 2
    assert report.versions.false_positives == 1
    assert report.duplicate_rate.numerator == 1
    assert report.duplicate_rate.denominator == 3
    assert report.duplicate_rate.value == pytest.approx(1 / 3)
    assert report.diagnostics.duplicate_prediction_version_ids == ["prediction-release-duplicate"]


def test_version_combining_distinct_gold_signals_counts_as_incorrect_merge() -> None:
    payload = prediction_payload()
    payload["versions"][0]["match_signals"]["external_ids"] = [
        {"provider": "synthetic-catalog", "value": "release-001"}
    ]

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.incorrect_merge_rate.numerator == 1
    assert report.incorrect_merge_rate.denominator == 2
    assert report.incorrect_merge_rate.value == 0.5
    assert report.diagnostics.conflicting_prediction_version_ids == ["prediction-early-demo"]


def test_explicit_merge_to_wrong_version_counts_as_incorrect_merge() -> None:
    payload = prediction_payload()
    payload["candidates"][1]["merge_target_prediction_version_id"] = "prediction-early-demo"

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.incorrect_merge_rate.numerator == 1
    assert report.incorrect_merge_rate.denominator == 1
    assert report.incorrect_merge_rate.value == 1.0


def test_promoted_fan_edit_trips_safety_metric() -> None:
    payload = prediction_payload()
    fan_candidate = payload["candidates"][0]
    payload["versions"].append(
        {
            "prediction_version_id": "prediction-promoted-fan-edit",
            "display_label": fan_candidate["label"],
            "version_type": "alternate_mix",
            "existence_confidence": "medium",
            "match_signals": fan_candidate["match_signals"],
            "contributors": [],
            "existence_evidence_ids": ["claim-fan-edit"],
        }
    )

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.fan_edit_false_positive_rate.numerator == 1
    assert report.fan_edit_false_positive_rate.denominator == 1
    assert report.fan_edit_false_positive_rate.value == 1.0
    assert report.fan_edit_encounter_coverage.value == 1.0


def test_fan_edit_merged_into_canonical_version_trips_safety_metric() -> None:
    payload = prediction_payload()
    payload["candidates"][0]["decision"] = "merged"
    payload["candidates"][0]["merge_target_prediction_version_id"] = "prediction-official-release"

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.fan_edit_false_positive_rate.value == 1.0
    assert report.incorrect_merge_rate.numerator == 1


def test_wrong_contributor_role_gets_no_partial_credit() -> None:
    payload = prediction_payload()
    payload["versions"][1]["contributors"][1]["role"] = "other"

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.contributors.true_positives == 2
    assert report.contributors.false_positives == 1
    assert report.contributors.false_negatives == 1
    assert report.contributors.f1 == pytest.approx(2 / 3)


def test_missing_evidence_reduces_attachment_coverage() -> None:
    payload = prediction_payload()
    payload["relationships"][0]["evidence_ids"] = []

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.evidence_coverage.numerator == 8
    assert report.evidence_coverage.denominator == 9
    assert report.evidence_coverage.value == pytest.approx(8 / 9)


def test_difference_detail_mismatch_gets_no_partial_credit() -> None:
    payload = prediction_payload()
    payload["changes"][0]["detail"] = "A different unsupported description."

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.differences.true_positives == 0
    assert report.differences.false_positives == 1
    assert report.differences.false_negatives == 1


def test_invented_relationship_is_false_positive_and_misses_gold_edge() -> None:
    payload = prediction_payload()
    relationship = payload["relationships"][0]
    relationship["subject_prediction_version_id"] = "prediction-early-demo"
    relationship["object_prediction_version_id"] = "prediction-official-release"

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.relationships.true_positives == 0
    assert report.relationships.false_positives == 1
    assert report.relationships.false_negatives == 1
    assert report.relationship_certainty_accuracy.value is None


def test_wrong_certainty_does_not_change_edge_accuracy() -> None:
    payload = prediction_payload()
    payload["relationships"][0]["certainty"] = "possible"

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.relationships.f1 == 1.0
    assert report.relationship_certainty_accuracy.value == 0.0


def test_relationships_collapsing_to_same_gold_edge_keep_duplicate_false_positive() -> None:
    payload = prediction_payload()
    duplicate_version = copy.deepcopy(payload["versions"][1])
    duplicate_version["prediction_version_id"] = "prediction-release-duplicate"
    payload["versions"].append(duplicate_version)
    duplicate_relationship = copy.deepcopy(payload["relationships"][0])
    duplicate_relationship["prediction_relationship_id"] = "prediction-duplicate-relationship"
    duplicate_relationship["subject_prediction_version_id"] = "prediction-release-duplicate"
    payload["relationships"].append(duplicate_relationship)

    report = evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))

    assert report.relationships.true_positives == 1
    assert report.relationships.false_positives == 1
    assert report.relationships.false_negatives == 0


def test_operational_failure_has_zero_version_recall_and_preserves_cost() -> None:
    payload = prediction_payload()
    payload["run_status"] = "failed"
    payload["outcome"] = None
    payload["failure_reason"] = "Synthetic provider failure"
    payload["source_count"] = 0
    payload["versions"] = []
    payload["candidates"] = []
    payload["changes"] = []
    payload["relationships"] = []
    prediction = SongPrediction.model_validate(payload)

    report = evaluate_song(gold_benchmark(), prediction)

    assert report.operational_success is False
    assert report.versions.precision is None
    assert report.versions.recall == 0.0
    assert report.cost_usd == prediction.cost_usd
    assert report.differences.recall == 0.0
    assert report.relationships.recall == 0.0


def test_rejects_prediction_for_different_benchmark_song() -> None:
    payload = prediction_payload()
    payload["benchmark_song_id"] = "synthetic-song-other"

    with pytest.raises(ValueError, match="benchmark_song_id mismatch"):
        evaluate_song(gold_benchmark(), SongPrediction.model_validate(payload))
