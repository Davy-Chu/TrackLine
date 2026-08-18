import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from research.evaluation.cli import main
from research.evaluation.models import BenchmarkSong
from research.evaluation.validation import BenchmarkLoadError, load_benchmark

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_FIXTURE = REPOSITORY_ROOT / "benchmarks" / "v1" / "development" / "synthetic-simple.json"
INVALID_JSON_FIXTURE = Path(__file__).parent / "fixtures" / "invalid-json.json"


def _valid_payload() -> dict[str, Any]:
    payload = json.loads(SYNTHETIC_FIXTURE.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def _validation_message(payload: dict[str, Any]) -> str:
    with pytest.raises(ValidationError) as captured:
        BenchmarkSong.model_validate(payload)
    return str(captured.value)


def test_loads_valid_synthetic_fixture() -> None:
    benchmark = load_benchmark(SYNTHETIC_FIXTURE)

    assert benchmark.schema_version == "1.0"
    assert benchmark.benchmark_song_id == "synthetic-song-001"
    assert len(benchmark.versions) == 2
    assert len(benchmark.candidate_expectations) == 2


def test_rejects_unknown_fields() -> None:
    payload = _valid_payload()
    payload["unexpected_field"] = True

    message = _validation_message(payload)

    assert "Extra inputs are not permitted" in message


def test_rejects_duplicate_version_ids() -> None:
    payload = _valid_payload()
    payload["versions"][1]["benchmark_version_id"] = "version-early-demo"

    message = _validation_message(payload)

    assert "duplicate version IDs: version-early-demo" in message


def test_rejects_unknown_evidence_reference() -> None:
    payload = _valid_payload()
    payload["versions"][0]["existence_evidence_ids"] = ["evidence-does-not-exist"]

    message = _validation_message(payload)

    assert "references unknown evidence: evidence-does-not-exist" in message


def test_rejects_relationship_to_unknown_version() -> None:
    payload = _valid_payload()
    payload["relationships"][0]["object_version_id"] = "version-does-not-exist"

    message = _validation_message(payload)

    assert "object_version_id references unknown version" in message


def test_rejects_relationship_self_edge() -> None:
    payload = _valid_payload()
    payload["relationships"][0]["object_version_id"] = "version-official-release"

    message = _validation_message(payload)

    assert "relationship-release-from-demo is a self-edge" in message


def test_rejects_relationship_cycle() -> None:
    payload = _valid_payload()
    reverse_relationship = copy.deepcopy(payload["relationships"][0])
    reverse_relationship["benchmark_relationship_id"] = "relationship-demo-from-release"
    reverse_relationship["subject_version_id"] = "version-early-demo"
    reverse_relationship["object_version_id"] = "version-official-release"
    payload["relationships"].append(reverse_relationship)

    message = _validation_message(payload)

    assert "relationships contain a cycle" in message


def test_merged_candidate_requires_target_version() -> None:
    payload = _valid_payload()
    payload["candidate_expectations"][1]["merge_target_version_id"] = None

    message = _validation_message(payload)

    assert "a merged candidate requires merge_target_version_id" in message


def test_loader_reports_invalid_json_location() -> None:
    with pytest.raises(BenchmarkLoadError) as captured:
        load_benchmark(INVALID_JSON_FIXTURE)

    assert "invalid JSON at line" in str(captured.value)
    assert "column" in str(captured.value)


def test_cli_validates_fixture_directory(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(SYNTHETIC_FIXTURE.parent)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[PASS]" in output
    assert "synthetic-song-001" in output
    assert "0 failed" in output
