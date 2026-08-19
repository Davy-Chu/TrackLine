from research.evaluation.matching import match_versions
from research.evaluation.models import BenchmarkSong
from research.evaluation.prediction_models import SongPrediction

from .helpers import valid_payload
from .scoring_helpers import gold_benchmark, perfect_prediction, prediction_payload


def test_matches_exact_filename_and_external_identity() -> None:
    matches = match_versions(gold_benchmark(), perfect_prediction())
    by_prediction_id = {match.prediction_version_id: match for match in matches}

    assert by_prediction_id["prediction-early-demo"].method == "filename"
    assert by_prediction_id["prediction-early-demo"].gold_version_ids == ("version-early-demo",)
    assert by_prediction_id["prediction-official-release"].method == "external_id"
    assert by_prediction_id["prediction-official-release"].gold_version_ids == (
        "version-official-release",
    )


def test_matches_known_duplicate_candidate_to_merge_target() -> None:
    payload = prediction_payload()
    duplicate_candidate = payload["candidates"][1]
    payload["versions"] = [
        {
            "prediction_version_id": "prediction-upload-as-version",
            "display_label": duplicate_candidate["label"],
            "version_type": "official_release",
            "existence_confidence": "medium",
            "match_signals": duplicate_candidate["match_signals"],
            "contributors": [],
            "existence_evidence_ids": ["claim-duplicate-upload"],
        }
    ]
    payload["candidates"] = []
    payload["changes"] = []
    payload["relationships"] = []
    prediction = SongPrediction.model_validate(payload)

    match = match_versions(gold_benchmark(), prediction)[0]

    assert match.status == "matched"
    assert match.method == "candidate_merge"
    assert match.gold_version_ids == ("version-official-release",)
    assert match.matched_candidate_id == "candidate-duplicate-upload"


def test_matches_unique_alias_after_case_and_whitespace_normalization() -> None:
    payload = prediction_payload()
    payload["versions"][0]["match_signals"] = {
        "aliases": ["  EARLY   solo DEMO  "],
        "filenames": [],
        "external_ids": [],
    }
    prediction = SongPrediction.model_validate(payload)

    match = match_versions(gold_benchmark(), prediction)[0]

    assert match.status == "matched"
    assert match.method == "alias"
    assert match.gold_version_ids == ("version-early-demo",)


def test_reports_conflicting_strong_signals_as_possible_incorrect_merge() -> None:
    payload = prediction_payload()
    payload["versions"][0]["match_signals"]["external_ids"] = [
        {"provider": "synthetic-catalog", "value": "release-001"}
    ]
    prediction = SongPrediction.model_validate(payload)

    match = match_versions(gold_benchmark(), prediction)[0]

    assert match.status == "conflicting_strong_signals"
    assert match.gold_version_ids == (
        "version-early-demo",
        "version-official-release",
    )


def test_reports_alias_shared_by_gold_versions_as_ambiguous() -> None:
    gold_payload = valid_payload()
    gold_payload["versions"][1]["match_signals"]["aliases"] = [
        "Official Single",
        "Early Solo Demo",
    ]
    gold = BenchmarkSong.model_validate(gold_payload)
    prediction_payload_value = prediction_payload()
    prediction_payload_value["versions"][0]["match_signals"] = {
        "aliases": [" early   SOLO demo "],
        "filenames": [],
        "external_ids": [],
    }
    prediction = SongPrediction.model_validate(prediction_payload_value)

    match = match_versions(gold, prediction)[0]

    assert match.status == "ambiguous"
    assert match.gold_version_ids == (
        "version-early-demo",
        "version-official-release",
    )
