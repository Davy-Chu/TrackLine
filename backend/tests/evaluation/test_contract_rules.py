"""Exhaustive tests for custom benchmark contract rules."""

import copy
from typing import Any

import pytest

from .helpers import valid_payload, validation_message

JsonPath = tuple[str | int, ...]


def _get_path(payload: dict[str, Any], path: JsonPath) -> Any:
    current: Any = payload
    for part in path:
        current = current[part]
    return current


def _set_path(payload: dict[str, Any], path: JsonPath, value: Any) -> None:
    parent = _get_path(payload, path[:-1])
    parent[path[-1]] = value


@pytest.mark.parametrize(
    ("path", "value"),
    [
        pytest.param(("schema_version",), "2.0", id="schema-version"),
        pytest.param(("split",), "training", id="benchmark-split"),
        pytest.param(("versions", 0, "version_type"), "remix", id="version-type"),
        pytest.param(
            ("versions", 0, "existence_confidence"),
            "low",
            id="canonical-existence-confidence",
        ),
        pytest.param(
            ("versions", 0, "contributors", 0, "role"),
            "songwriter",
            id="contributor-role",
        ),
        pytest.param(
            ("candidate_expectations", 0, "expected_decision"),
            "promoted",
            id="candidate-decision",
        ),
        pytest.param(("changes", 0, "category"), "tempo_changed", id="change-category"),
        pytest.param(
            ("relationships", 0, "relationship_type"),
            "sampled_from",
            id="relationship-type",
        ),
        pytest.param(
            ("relationships", 0, "certainty"),
            "unknown",
            id="relationship-certainty",
        ),
    ],
)
def test_rejects_unsupported_controlled_values(path: JsonPath, value: str) -> None:
    payload = valid_payload()
    _set_path(payload, path, value)

    message = validation_message(payload)

    assert "Input should be" in message


def test_rejects_invalid_identifier_format() -> None:
    payload = valid_payload()
    payload["benchmark_song_id"] = "Uppercase IDs are not valid"

    message = validation_message(payload)

    assert "String should match pattern" in message


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(("annotation", "annotated_at"), id="annotation-time"),
        pytest.param(("sources", 0, "retrieved_at"), id="retrieval-time"),
    ],
)
def test_requires_timezone_aware_timestamps(path: JsonPath) -> None:
    payload = valid_payload()
    _set_path(payload, path, "2026-08-18T00:00:00")

    message = validation_message(payload)

    assert "must include a timezone" in message


def test_rejects_invalid_source_url() -> None:
    payload = valid_payload()
    payload["sources"][0]["url"] = "not-a-url"

    message = validation_message(payload)

    assert "URL" in message


def test_rejects_invalid_source_content_hash() -> None:
    payload = valid_payload()
    payload["sources"][0]["content_hash"] = "sha256:not-a-real-hash"

    message = validation_message(payload)

    assert "String should match pattern" in message


@pytest.mark.parametrize(
    ("path", "value"),
    [
        pytest.param(("song_work", "artists"), [], id="song-work-artists"),
        pytest.param(("sources",), [], id="sources"),
        pytest.param(("versions",), [], id="versions"),
        pytest.param(("sources", 0, "evidence"), [], id="source-evidence"),
    ],
)
def test_requires_nonempty_core_collections(path: JsonPath, value: list[object]) -> None:
    payload = valid_payload()
    _set_path(payload, path, value)

    message = validation_message(payload)

    assert "List should have at least 1 item" in message


@pytest.mark.parametrize(
    ("field", "values"),
    [
        pytest.param(
            "artists",
            ["The Example Artist", "the example artist"],
            id="artists",
        ),
        pytest.param("aliases", ["Static Signal", "static signal"], id="song-aliases"),
    ],
)
def test_rejects_case_insensitive_duplicate_song_names(
    field: str,
    values: list[str],
) -> None:
    payload = valid_payload()
    payload["song_work"][field] = values

    message = validation_message(payload)

    assert "values must be unique" in message


def test_match_signals_require_at_least_one_exact_signal() -> None:
    payload = valid_payload()
    payload["versions"][0]["match_signals"] = {
        "aliases": [],
        "filenames": [],
        "external_ids": [],
    }

    message = validation_message(payload)

    assert "at least one alias, filename, or external ID is required" in message


@pytest.mark.parametrize(
    ("field", "values", "expected"),
    [
        pytest.param(
            "aliases",
            ["Early Solo Demo", "early solo demo"],
            "aliases contain repeated values",
            id="aliases",
        ),
        pytest.param(
            "filenames",
            ["Signal Demo.wav", "signal demo.wav"],
            "filenames contain repeated values",
            id="filenames",
        ),
    ],
)
def test_match_signals_reject_duplicate_text_values(
    field: str,
    values: list[str],
    expected: str,
) -> None:
    payload = valid_payload()
    payload["versions"][0]["match_signals"][field] = values

    message = validation_message(payload)

    assert expected in message


def test_match_signals_reject_duplicate_external_ids() -> None:
    payload = valid_payload()
    external_id = {"provider": "Synthetic Catalog", "value": "Release-001"}
    payload["versions"][0]["match_signals"] = {
        "aliases": [],
        "filenames": [],
        "external_ids": [external_id, {"provider": "synthetic catalog", "value": "release-001"}],
    }

    message = validation_message(payload)

    assert "external_ids contain repeated provider/value pairs" in message


@pytest.mark.parametrize(
    ("collection", "id_field", "label"),
    [
        pytest.param("sources", "source_id", "source", id="source"),
        pytest.param(
            "candidate_expectations",
            "benchmark_candidate_id",
            "candidate",
            id="candidate",
        ),
        pytest.param("changes", "benchmark_change_id", "change", id="change"),
        pytest.param(
            "relationships",
            "benchmark_relationship_id",
            "relationship",
            id="relationship",
        ),
        pytest.param(
            "indeterminate_items",
            "benchmark_indeterminate_id",
            "indeterminate item",
            id="indeterminate-item",
        ),
    ],
)
def test_rejects_duplicate_entity_ids(collection: str, id_field: str, label: str) -> None:
    payload = valid_payload()
    duplicate = copy.deepcopy(payload[collection][0])
    duplicated_id = duplicate[id_field]
    payload[collection].append(duplicate)

    message = validation_message(payload)

    assert f"duplicate {label} IDs: {duplicated_id}" in message


def test_rejects_duplicate_evidence_ids() -> None:
    payload = valid_payload()
    duplicate = copy.deepcopy(payload["sources"][0]["evidence"][0])
    payload["sources"][0]["evidence"].append(duplicate)

    message = validation_message(payload)

    assert "duplicate evidence IDs: evidence-demo-existed" in message


def test_canonical_version_and_candidate_ids_must_not_overlap() -> None:
    payload = valid_payload()
    payload["candidate_expectations"][0]["benchmark_candidate_id"] = "version-early-demo"

    message = validation_message(payload)

    assert "canonical versions and noncanonical candidates share IDs" in message


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(("versions", 0, "existence_evidence_ids"), id="version-existence"),
        pytest.param(
            ("versions", 0, "contributors", 0, "evidence_ids"),
            id="contributor",
        ),
        pytest.param(("candidate_expectations", 0, "evidence_ids"), id="candidate"),
        pytest.param(("changes", 0, "evidence_ids"), id="change"),
        pytest.param(("relationships", 0, "evidence_ids"), id="relationship"),
        pytest.param(("indeterminate_items", 0, "evidence_ids"), id="indeterminate-item"),
    ],
)
def test_rejects_duplicate_evidence_references(path: JsonPath) -> None:
    payload = valid_payload()
    evidence_ids = _get_path(payload, path)
    _set_path(payload, path, [evidence_ids[0], evidence_ids[0]])

    message = validation_message(payload)

    assert "evidence references must be unique" in message


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(("versions", 0, "existence_evidence_ids"), id="version-existence"),
        pytest.param(
            ("versions", 0, "contributors", 0, "evidence_ids"),
            id="contributor",
        ),
        pytest.param(("candidate_expectations", 0, "evidence_ids"), id="candidate"),
        pytest.param(("changes", 0, "evidence_ids"), id="change"),
        pytest.param(("relationships", 0, "evidence_ids"), id="relationship"),
        pytest.param(("indeterminate_items", 0, "evidence_ids"), id="indeterminate-item"),
    ],
)
def test_rejects_unknown_evidence_for_every_supported_owner(path: JsonPath) -> None:
    payload = valid_payload()
    _set_path(payload, path, ["evidence-does-not-exist"])

    message = validation_message(payload)

    assert "references unknown evidence: evidence-does-not-exist" in message


def test_rejects_duplicate_contributor_role_on_same_version() -> None:
    payload = valid_payload()
    duplicate = copy.deepcopy(payload["versions"][0]["contributors"][0])
    duplicate["name"] = duplicate["name"].lower()
    payload["versions"][0]["contributors"].append(duplicate)

    message = validation_message(payload)

    assert "has repeated contributor/role pairs" in message


def test_merged_candidate_requires_duplicate_or_same_audio_reason() -> None:
    payload = valid_payload()
    payload["candidate_expectations"][1]["reason"] = "fan_edit"

    message = validation_message(payload)

    assert "a merged candidate requires a duplicate or same-audio reason" in message


def test_nonmerged_candidate_must_not_have_merge_target() -> None:
    payload = valid_payload()
    payload["candidate_expectations"][0]["merge_target_version_id"] = "version-official-release"

    message = validation_message(payload)

    assert "only a merged candidate may have merge_target_version_id" in message


def test_other_candidate_reason_requires_detail() -> None:
    payload = valid_payload()
    payload["candidate_expectations"][0]["reason"] = "other"
    payload["candidate_expectations"][0]["reason_detail"] = None

    message = validation_message(payload)

    assert "reason_detail is required when reason is other" in message


def test_merged_candidate_target_must_be_known_version() -> None:
    payload = valid_payload()
    payload["candidate_expectations"][1]["merge_target_version_id"] = "version-does-not-exist"

    message = validation_message(payload)

    assert "has unknown merge target version-does-not-exist" in message


@pytest.mark.parametrize("field", ["from_version_id", "to_version_id"])
def test_change_version_references_must_exist(field: str) -> None:
    payload = valid_payload()
    payload["changes"][0][field] = "version-does-not-exist"

    message = validation_message(payload)

    assert f"{field} references unknown version" in message


def test_change_cannot_compare_version_to_itself() -> None:
    payload = valid_payload()
    payload["changes"][0]["to_version_id"] = "version-early-demo"

    message = validation_message(payload)

    assert "change-full-production compares a version to itself" in message


def test_relationship_subject_version_must_exist() -> None:
    payload = valid_payload()
    payload["relationships"][0]["subject_version_id"] = "version-does-not-exist"

    message = validation_message(payload)

    assert "subject_version_id references unknown version" in message


def test_rejects_duplicate_relationship_edge_with_different_id() -> None:
    payload = valid_payload()
    duplicate = copy.deepcopy(payload["relationships"][0])
    duplicate["benchmark_relationship_id"] = "relationship-duplicate-edge"
    payload["relationships"].append(duplicate)

    message = validation_message(payload)

    assert "relationships contain repeated subject/type/object edges" in message
