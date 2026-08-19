"""Shared immutable-fixture helpers for matching and scoring tests."""

import json
from pathlib import Path
from typing import Any, cast

from research.evaluation.models import BenchmarkSong
from research.evaluation.prediction_models import SongPrediction
from research.evaluation.validation import load_benchmark

from .helpers import SYNTHETIC_FIXTURE

PERFECT_PREDICTION_FIXTURE = (
    Path(__file__).parent / "prediction_fixtures" / "perfect-prediction.json"
)


def gold_benchmark() -> BenchmarkSong:
    return load_benchmark(SYNTHETIC_FIXTURE)


def prediction_payload() -> dict[str, Any]:
    payload = json.loads(PERFECT_PREDICTION_FIXTURE.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def perfect_prediction() -> SongPrediction:
    return SongPrediction.model_validate(prediction_payload())
