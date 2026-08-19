from decimal import Decimal

from pydantic import ValidationError

from research.evaluation.prediction_models import SongPrediction

from .scoring_helpers import perfect_prediction, prediction_payload


def _prediction_validation_message(payload: dict[str, object]) -> str:
    try:
        SongPrediction.model_validate(payload)
    except ValidationError as error:
        return str(error)
    raise AssertionError("prediction payload unexpectedly passed validation")


def test_loads_complete_prediction_snapshot() -> None:
    prediction = perfect_prediction()

    assert prediction.run_status == "completed"
    assert prediction.outcome == "lineage_found"
    assert prediction.cost_usd == Decimal("0.05")
    assert len(prediction.versions) == 2


def test_completed_prediction_requires_outcome() -> None:
    payload = prediction_payload()
    payload["outcome"] = None

    message = _prediction_validation_message(payload)

    assert "a completed prediction requires an outcome" in message


def test_failed_prediction_requires_reason_and_no_results() -> None:
    payload = prediction_payload()
    payload["run_status"] = "failed"
    payload["outcome"] = None
    payload["failure_reason"] = None

    message = _prediction_validation_message(payload)

    assert "a failed prediction requires failure_reason" in message
    assert "cannot publish partial result collections" in message


def test_merged_candidate_target_must_exist() -> None:
    payload = prediction_payload()
    payload["candidates"][1]["merge_target_prediction_version_id"] = "prediction-missing"

    message = _prediction_validation_message(payload)

    assert "has unknown merge target prediction-missing" in message


def test_change_endpoints_must_exist() -> None:
    payload = prediction_payload()
    payload["changes"][0]["from_prediction_version_id"] = "prediction-missing"

    message = _prediction_validation_message(payload)

    assert "references unknown predicted version: prediction-missing" in message


def test_prediction_evidence_may_be_empty_for_coverage_scoring() -> None:
    payload = prediction_payload()
    payload["versions"][0]["existence_evidence_ids"] = []

    prediction = SongPrediction.model_validate(payload)

    assert prediction.versions[0].existence_evidence_ids == []
