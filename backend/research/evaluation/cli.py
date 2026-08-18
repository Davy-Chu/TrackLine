"""Command-line entry point for benchmark fixture validation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from research.evaluation.validation import (
    BenchmarkLoadError,
    find_benchmark_files,
    load_benchmark,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Trackline benchmark v1 fixtures")
    parser.add_argument("path", type=Path, help="JSON fixture or directory of fixtures")
    arguments = parser.parse_args(argv)

    try:
        fixture_files = find_benchmark_files(arguments.path)
    except BenchmarkLoadError as error:
        print(f"[FAIL] {error}")
        return 1

    failures = 0
    for fixture_path in fixture_files:
        try:
            benchmark = load_benchmark(fixture_path)
        except BenchmarkLoadError as error:
            failures += 1
            print(f"[FAIL] {error}")
        else:
            print(
                f"[PASS] {fixture_path} "
                f"({benchmark.benchmark_song_id}, {len(benchmark.versions)} versions)"
            )

    print(f"Validated {len(fixture_files)} fixture(s); {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
