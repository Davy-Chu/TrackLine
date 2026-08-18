"""Load and validate Trackline benchmark fixture files."""

import json
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from research.evaluation.models import BenchmarkSong


class BenchmarkLoadError(ValueError):
    """A benchmark file could not be read or did not satisfy the v1 contract."""

    def __init__(self, path: Path, details: tuple[str, ...]) -> None:
        self.path = path
        self.details = details
        super().__init__(self.__str__())

    def __str__(self) -> str:
        rendered = "\n  - ".join(self.details)
        return f"{self.path}:\n  - {rendered}"


def load_benchmark(path: Path) -> BenchmarkSong:
    """Load one JSON fixture and validate its fields and cross-references."""

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise BenchmarkLoadError(path, (str(error),)) from error

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        detail = f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        raise BenchmarkLoadError(path, (detail,)) from error

    try:
        return BenchmarkSong.model_validate(payload)
    except ValidationError as error:
        details = tuple(_render_pydantic_error(item) for item in error.errors(include_url=False))
        raise BenchmarkLoadError(path, details) from error


def find_benchmark_files(path: Path) -> list[Path]:
    """Return JSON fixtures below a file or directory in stable order."""

    if not path.exists():
        raise BenchmarkLoadError(path, ("path does not exist",))
    if path.is_file():
        if path.suffix.casefold() != ".json":
            raise BenchmarkLoadError(path, ("fixture file must use the .json extension",))
        return [path]

    files = sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file())
    if not files:
        raise BenchmarkLoadError(path, ("directory contains no JSON benchmark fixtures",))
    return files


def _render_pydantic_error(error: Mapping[str, object]) -> str:
    location_value = error.get("loc", ())
    if isinstance(location_value, tuple):
        location = ".".join(str(part) for part in location_value)
    else:
        location = str(location_value)
    message = str(error.get("msg", "validation failed"))
    return f"{location}: {message}" if location else message
