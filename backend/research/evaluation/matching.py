"""Deterministic pairing of prediction identities with benchmark identities."""

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from research.evaluation.models import BenchmarkSong, MatchSignals
from research.evaluation.prediction_models import SongPrediction

MatchMethod = Literal["external_id", "filename", "alias", "candidate_merge", "none"]
MatchStatus = Literal[
    "matched",
    "unmatched",
    "ambiguous",
    "conflicting_strong_signals",
]


@dataclass(frozen=True)
class SignalMatch:
    """Result of matching one signal collection against one identity index."""

    status: MatchStatus
    method: MatchMethod
    matched_ids: tuple[str, ...]


@dataclass(frozen=True)
class VersionMatch:
    """Pairing result for one predicted canonical Version."""

    prediction_version_id: str
    status: MatchStatus
    method: MatchMethod
    gold_version_ids: tuple[str, ...]
    matched_candidate_id: str | None = None


@dataclass(frozen=True)
class _SignalIndex:
    external_ids: dict[tuple[str, str], set[str]]
    filenames: dict[str, set[str]]
    aliases: dict[str, set[str]]


def match_versions(
    gold: BenchmarkSong,
    prediction: SongPrediction,
) -> tuple[VersionMatch, ...]:
    """Match every predicted Version to zero, one, or several gold Versions."""

    version_index = _build_index(
        (version.benchmark_version_id, version.match_signals) for version in gold.versions
    )
    merged_candidates = [
        candidate
        for candidate in gold.candidate_expectations
        if candidate.expected_decision == "merged" and candidate.merge_target_version_id is not None
    ]
    candidate_index = _build_index(
        (candidate.benchmark_candidate_id, candidate.match_signals)
        for candidate in merged_candidates
    )
    merge_targets = {
        candidate.benchmark_candidate_id: candidate.merge_target_version_id
        for candidate in merged_candidates
    }

    matches: list[VersionMatch] = []
    for predicted_version in prediction.versions:
        direct = match_signals(predicted_version.match_signals, version_index)
        if direct.status != "unmatched":
            matches.append(
                VersionMatch(
                    prediction_version_id=predicted_version.prediction_version_id,
                    status=direct.status,
                    method=direct.method,
                    gold_version_ids=direct.matched_ids,
                )
            )
            continue

        candidate_match = match_signals(predicted_version.match_signals, candidate_index)
        if candidate_match.status == "matched":
            candidate_id = candidate_match.matched_ids[0]
            target_id = merge_targets[candidate_id]
            if target_id is None:  # Kept explicit for type safety around fixture data.
                raise ValueError(f"merged benchmark candidate {candidate_id} has no target")
            matches.append(
                VersionMatch(
                    prediction_version_id=predicted_version.prediction_version_id,
                    status="matched",
                    method="candidate_merge",
                    gold_version_ids=(target_id,),
                    matched_candidate_id=candidate_id,
                )
            )
        else:
            matches.append(
                VersionMatch(
                    prediction_version_id=predicted_version.prediction_version_id,
                    status=candidate_match.status,
                    method=("candidate_merge" if candidate_match.status != "unmatched" else "none"),
                    gold_version_ids=(),
                )
            )

    return tuple(matches)


def match_gold_candidates(signals: MatchSignals, gold: BenchmarkSong) -> SignalMatch:
    """Match signals to all gold candidate expectations for safety evaluation."""

    candidate_index = _build_index(
        (candidate.benchmark_candidate_id, candidate.match_signals)
        for candidate in gold.candidate_expectations
    )
    return match_signals(signals, candidate_index)


def match_signals(signals: MatchSignals, index: _SignalIndex) -> SignalMatch:
    """Apply the versioned exact-signal precedence rules."""

    external_matches = _lookup_many(
        index.external_ids,
        (
            (normalize_text(identity.provider), normalize_text(identity.value))
            for identity in signals.external_ids
        ),
    )
    filename_matches = _lookup_many(
        index.filenames,
        (normalize_text(filename) for filename in signals.filenames),
    )
    strong_matches = external_matches | filename_matches
    if len(strong_matches) > 1:
        return SignalMatch(
            status="conflicting_strong_signals",
            method="external_id" if external_matches else "filename",
            matched_ids=tuple(sorted(strong_matches)),
        )
    if strong_matches:
        return SignalMatch(
            status="matched",
            method="external_id" if external_matches else "filename",
            matched_ids=tuple(strong_matches),
        )

    alias_matches = _lookup_many(
        index.aliases,
        (normalize_text(alias) for alias in signals.aliases),
    )
    if len(alias_matches) > 1:
        return SignalMatch(
            status="ambiguous",
            method="alias",
            matched_ids=tuple(sorted(alias_matches)),
        )
    if alias_matches:
        return SignalMatch(
            status="matched",
            method="alias",
            matched_ids=tuple(alias_matches),
        )
    return SignalMatch(status="unmatched", method="none", matched_ids=())


def normalize_text(value: str) -> str:
    """Normalize only Unicode, case, and whitespace; do not perform fuzzy matching."""

    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(normalized.split())


def _build_index(items: Iterable[tuple[str, MatchSignals]]) -> _SignalIndex:
    external_ids: dict[tuple[str, str], set[str]] = {}
    filenames: dict[str, set[str]] = {}
    aliases: dict[str, set[str]] = {}

    for item_id, signals in items:
        for identity in signals.external_ids:
            key = (normalize_text(identity.provider), normalize_text(identity.value))
            external_ids.setdefault(key, set()).add(item_id)
        for filename in signals.filenames:
            filenames.setdefault(normalize_text(filename), set()).add(item_id)
        for alias in signals.aliases:
            aliases.setdefault(normalize_text(alias), set()).add(item_id)

    return _SignalIndex(
        external_ids=external_ids,
        filenames=filenames,
        aliases=aliases,
    )


def _lookup_many[K](index: dict[K, set[str]], keys: Iterable[K]) -> set[str]:
    matches: set[str] = set()
    for key in keys:
        matches.update(index.get(key, set()))
    return matches
