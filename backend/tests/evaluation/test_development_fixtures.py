"""Checks for the first source-backed development benchmark slice."""

from hashlib import sha256
from pathlib import Path

import pytest

from research.evaluation.validation import find_benchmark_files, load_benchmark

from .helpers import REPOSITORY_ROOT, SYNTHETIC_FIXTURE

DEVELOPMENT_DIRECTORY = REPOSITORY_ROOT / "benchmarks" / "v1" / "development"
REAL_DRAFT_FIXTURES = (
    DEVELOPMENT_DIRECTORY / "nights.json",
    DEVELOPMENT_DIRECTORY / "not-real-molly.json",
    DEVELOPMENT_DIRECTORY / "sky-city.json",
)


@pytest.mark.parametrize("fixture", REAL_DRAFT_FIXTURES, ids=lambda path: path.stem)
def test_real_development_fixture_is_validation_only_draft(fixture: Path) -> None:
    benchmark = load_benchmark(fixture)

    assert benchmark.annotation.status == "draft"
    assert benchmark.annotation.notes is not None
    assert "validation-only" in benchmark.annotation.notes.casefold()
    assert benchmark.indeterminate_items


def test_development_directory_contains_selected_slice() -> None:
    assert find_benchmark_files(DEVELOPMENT_DIRECTORY) == sorted(
        [SYNTHETIC_FIXTURE, *REAL_DRAFT_FIXTURES]
    )


@pytest.mark.parametrize("fixture", REAL_DRAFT_FIXTURES, ids=lambda path: path.stem)
def test_manual_source_hashes_cover_retained_excerpts(fixture: Path) -> None:
    benchmark = load_benchmark(fixture)

    for source in benchmark.sources:
        retained_text = "\n".join(evidence.excerpt for evidence in source.evidence)
        expected_hash = f"sha256:{sha256(retained_text.encode('utf-8')).hexdigest()}"
        assert source.content_hash == expected_hash, source.source_id
