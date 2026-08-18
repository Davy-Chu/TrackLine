"""Shared deterministic data helpers for benchmark evaluation tests."""

import json
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from research.evaluation.models import BenchmarkSong

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_FIXTURE = REPOSITORY_ROOT / "benchmarks" / "v1" / "development" / "synthetic-simple.json"
INVALID_JSON_FIXTURE = Path(__file__).parent / "fixtures" / "invalid-json.json"


def valid_payload() -> dict[str, Any]:
    payload = json.loads(SYNTHETIC_FIXTURE.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def validation_message(payload: dict[str, Any]) -> str:
    try:
        BenchmarkSong.model_validate(payload)
    except ValidationError as error:
        return str(error)
    raise AssertionError("payload unexpectedly passed validation")
