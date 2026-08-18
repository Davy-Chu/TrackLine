import copy
from pathlib import Path

import pytest

from research.evaluation.cli import main
from research.evaluation.validation import (
    BenchmarkLoadError,
    find_benchmark_files,
    load_benchmark,
)

from .helpers import (
    INVALID_JSON_FIXTURE,
    REPOSITORY_ROOT,
    SYNTHETIC_FIXTURE,
    valid_payload,
    validation_message,
)

INVALID_STRUCTURE_FIXTURE = Path(__file__).parent / "fixtures" / "invalid-structure.json"
INVALID_FIXTURE_DIRECTORY = INVALID_JSON_FIXTURE.parent
HELD_OUT_DIRECTORY = REPOSITORY_ROOT / "benchmarks" / "v1" / "held-out"
MISSING_FIXTURE = INVALID_FIXTURE_DIRECTORY / "does-not-exist.json"
BENCHMARK_README = REPOSITORY_ROOT / "benchmarks" / "README.md"


def test_loads_valid_synthetic_fixture() -> None:
    benchmark = load_benchmark(SYNTHETIC_FIXTURE)

    assert benchmark.schema_version == "1.0"
    assert benchmark.benchmark_song_id == "synthetic-song-001"
    assert len(benchmark.versions) == 2
    assert len(benchmark.candidate_expectations) == 2


def test_rejects_unknown_fields() -> None:
    payload = valid_payload()
    payload["unexpected_field"] = True

    message = validation_message(payload)

    assert "Extra inputs are not permitted" in message


def test_rejects_duplicate_version_ids() -> None:
    payload = valid_payload()
    payload["versions"][1]["benchmark_version_id"] = "version-early-demo"

    message = validation_message(payload)

    assert "duplicate version IDs: version-early-demo" in message


def test_rejects_unknown_evidence_reference() -> None:
    payload = valid_payload()
    payload["versions"][0]["existence_evidence_ids"] = ["evidence-does-not-exist"]

    message = validation_message(payload)

    assert "references unknown evidence: evidence-does-not-exist" in message


def test_rejects_relationship_to_unknown_version() -> None:
    payload = valid_payload()
    payload["relationships"][0]["object_version_id"] = "version-does-not-exist"

    message = validation_message(payload)

    assert "object_version_id references unknown version" in message


def test_rejects_relationship_self_edge() -> None:
    payload = valid_payload()
    payload["relationships"][0]["object_version_id"] = "version-official-release"

    message = validation_message(payload)

    assert "relationship-release-from-demo is a self-edge" in message


def test_rejects_relationship_cycle() -> None:
    payload = valid_payload()
    reverse_relationship = copy.deepcopy(payload["relationships"][0])
    reverse_relationship["benchmark_relationship_id"] = "relationship-demo-from-release"
    reverse_relationship["subject_version_id"] = "version-early-demo"
    reverse_relationship["object_version_id"] = "version-official-release"
    payload["relationships"].append(reverse_relationship)

    message = validation_message(payload)

    assert "relationships contain a cycle" in message


def test_merged_candidate_requires_target_version() -> None:
    payload = valid_payload()
    payload["candidate_expectations"][1]["merge_target_version_id"] = None

    message = validation_message(payload)

    assert "a merged candidate requires merge_target_version_id" in message


def test_loader_reports_invalid_json_location() -> None:
    with pytest.raises(BenchmarkLoadError) as captured:
        load_benchmark(INVALID_JSON_FIXTURE)

    assert "invalid JSON at line" in str(captured.value)
    assert "column" in str(captured.value)


def test_loader_wraps_contract_validation_errors() -> None:
    with pytest.raises(BenchmarkLoadError) as captured:
        load_benchmark(INVALID_STRUCTURE_FIXTURE)

    assert "benchmark_song_id" in str(captured.value)
    assert "Field required" in str(captured.value)


def test_loader_reports_missing_file() -> None:
    with pytest.raises(BenchmarkLoadError) as captured:
        load_benchmark(MISSING_FIXTURE)

    assert str(MISSING_FIXTURE) in str(captured.value)


def test_finds_single_json_fixture() -> None:
    assert find_benchmark_files(SYNTHETIC_FIXTURE) == [SYNTHETIC_FIXTURE]


def test_finds_directory_fixtures_in_stable_order() -> None:
    fixture_files = find_benchmark_files(INVALID_FIXTURE_DIRECTORY)

    assert fixture_files == sorted([INVALID_JSON_FIXTURE, INVALID_STRUCTURE_FIXTURE])


def test_file_discovery_rejects_missing_path() -> None:
    with pytest.raises(BenchmarkLoadError, match="path does not exist"):
        find_benchmark_files(MISSING_FIXTURE)


def test_file_discovery_rejects_non_json_file() -> None:
    with pytest.raises(BenchmarkLoadError, match="must use the .json extension"):
        find_benchmark_files(BENCHMARK_README)


def test_file_discovery_rejects_directory_without_json() -> None:
    with pytest.raises(BenchmarkLoadError, match="contains no JSON benchmark fixtures"):
        find_benchmark_files(HELD_OUT_DIRECTORY)


def test_cli_validates_fixture_directory(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(SYNTHETIC_FIXTURE.parent)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[PASS]" in output
    assert "synthetic-song-001" in output
    assert "0 failed" in output


def test_cli_validates_single_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(SYNTHETIC_FIXTURE)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[PASS]" in output
    assert "Validated 1 fixture(s); 0 failed" in output


def test_cli_reports_every_invalid_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(INVALID_FIXTURE_DIRECTORY)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert output.count("[FAIL]") == 2
    assert "invalid JSON at line" in output
    assert "benchmark_song_id" in output
    assert "Validated 2 fixture(s); 2 failed" in output


def test_cli_reports_invalid_input_path(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(MISSING_FIXTURE)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "[FAIL]" in output
    assert "path does not exist" in output
