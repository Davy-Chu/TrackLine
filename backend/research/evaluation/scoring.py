"""Deterministic per-song scoring for Trackline benchmark predictions."""

from collections import Counter, defaultdict
from collections.abc import Hashable, Iterable
from decimal import Decimal
from typing import Literal

from pydantic import Field

from research.evaluation.matching import (
    VersionMatch,
    match_gold_candidates,
    match_versions,
    normalize_text,
)
from research.evaluation.models import BenchmarkSong, Identifier, StrictModel
from research.evaluation.prediction_models import PredictionOutcome, SongPrediction


class ClassificationMetric(StrictModel):
    """Raw classification counts plus derived precision, recall, and F1."""

    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    precision: float | None
    recall: float | None
    f1: float | None


class RateMetric(StrictModel):
    """An auditable numerator/denominator rate."""

    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    value: float | None


class EvaluationDiagnostics(StrictModel):
    """Pairing details needed to explain a score rather than only display it."""

    unmatched_prediction_version_ids: list[Identifier]
    ambiguous_prediction_version_ids: list[Identifier]
    conflicting_prediction_version_ids: list[Identifier]
    duplicate_prediction_version_ids: list[Identifier]
    indeterminate_gold_item_count: int = Field(ge=0)


class SongEvaluationReport(StrictModel):
    """Versioned deterministic score report for one SongWork prediction."""

    metric_contract_version: Literal["1.0"] = "1.0"
    benchmark_song_id: Identifier
    run_id: Identifier
    operational_success: bool
    outcome: PredictionOutcome | None
    latency_ms: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0)
    source_count: int = Field(ge=0)
    versions: ClassificationMetric
    duplicate_rate: RateMetric
    incorrect_merge_rate: RateMetric
    fan_edit_false_positive_rate: RateMetric
    fan_edit_encounter_coverage: RateMetric
    contributors: ClassificationMetric
    evidence_coverage: RateMetric
    differences: ClassificationMetric
    relationships: ClassificationMetric
    relationship_certainty_accuracy: RateMetric
    diagnostics: EvaluationDiagnostics


def evaluate_song(
    gold: BenchmarkSong,
    prediction: SongPrediction,
) -> SongEvaluationReport:
    """Score one immutable prediction snapshot against one gold fixture."""

    if gold.annotation.status == "draft":
        raise ValueError(
            "draft benchmark fixtures are validation-only and cannot be scored"
        )

    if gold.benchmark_song_id != prediction.benchmark_song_id:
        raise ValueError(
            "benchmark_song_id mismatch: "
            f"gold={gold.benchmark_song_id}, prediction={prediction.benchmark_song_id}"
        )

    version_matches = match_versions(gold, prediction)
    match_by_prediction_id = {match.prediction_version_id: match for match in version_matches}
    single_match_map = {
        match.prediction_version_id: match.gold_version_ids[0]
        for match in version_matches
        if match.status == "matched" and len(match.gold_version_ids) == 1
    }
    matched_groups: dict[str, list[VersionMatch]] = defaultdict(list)
    for match in version_matches:
        if match.status == "matched" and len(match.gold_version_ids) == 1:
            matched_groups[match.gold_version_ids[0]].append(match)

    representatives: dict[str, str] = {}
    duplicate_prediction_ids: list[str] = []
    for gold_version_id, matches in matched_groups.items():
        ordered = sorted(matches, key=_representative_sort_key)
        representatives[gold_version_id] = ordered[0].prediction_version_id
        duplicate_prediction_ids.extend(match.prediction_version_id for match in ordered[1:])

    version_true_positives = len(matched_groups)
    version_metric = _classification_metric(
        true_positives=version_true_positives,
        false_positives=len(prediction.versions) - version_true_positives,
        false_negatives=len(gold.versions) - version_true_positives,
    )
    duplicate_rate = _rate_metric(
        numerator=len(duplicate_prediction_ids),
        denominator=len(prediction.versions),
    )

    incorrect_merges, scorable_merges = _score_incorrect_merges(
        gold,
        prediction,
        version_matches,
        match_by_prediction_id,
    )
    fan_edit_false_positive_rate, fan_edit_coverage = _score_fan_edits(gold, prediction)
    contributor_metric = _score_contributors(gold, prediction, representatives)
    evidence_coverage = _score_evidence_coverage(prediction)
    difference_metric = _score_differences(gold, prediction, single_match_map)
    relationship_metric, relationship_certainty = _score_relationships(
        gold,
        prediction,
        single_match_map,
    )

    return SongEvaluationReport(
        benchmark_song_id=gold.benchmark_song_id,
        run_id=prediction.run_id,
        operational_success=prediction.run_status == "completed",
        outcome=prediction.outcome,
        latency_ms=prediction.latency_ms,
        cost_usd=prediction.cost_usd,
        source_count=prediction.source_count,
        versions=version_metric,
        duplicate_rate=duplicate_rate,
        incorrect_merge_rate=_rate_metric(incorrect_merges, scorable_merges),
        fan_edit_false_positive_rate=fan_edit_false_positive_rate,
        fan_edit_encounter_coverage=fan_edit_coverage,
        contributors=contributor_metric,
        evidence_coverage=evidence_coverage,
        differences=difference_metric,
        relationships=relationship_metric,
        relationship_certainty_accuracy=relationship_certainty,
        diagnostics=EvaluationDiagnostics(
            unmatched_prediction_version_ids=sorted(
                match.prediction_version_id
                for match in version_matches
                if match.status == "unmatched"
            ),
            ambiguous_prediction_version_ids=sorted(
                match.prediction_version_id
                for match in version_matches
                if match.status == "ambiguous"
            ),
            conflicting_prediction_version_ids=sorted(
                match.prediction_version_id
                for match in version_matches
                if match.status == "conflicting_strong_signals"
            ),
            duplicate_prediction_version_ids=sorted(duplicate_prediction_ids),
            indeterminate_gold_item_count=len(gold.indeterminate_items),
        ),
    )


def _score_incorrect_merges(
    gold: BenchmarkSong,
    prediction: SongPrediction,
    version_matches: tuple[VersionMatch, ...],
    match_by_prediction_id: dict[str, VersionMatch],
) -> tuple[int, int]:
    conflicting_versions = sum(
        match.status == "conflicting_strong_signals" for match in version_matches
    )
    incorrect = conflicting_versions
    scorable = conflicting_versions
    gold_candidates = {
        candidate.benchmark_candidate_id: candidate for candidate in gold.candidate_expectations
    }

    for candidate in prediction.candidates:
        if candidate.decision != "merged":
            continue
        candidate_match = match_gold_candidates(candidate.match_signals, gold)
        if candidate_match.status != "matched":
            continue

        scorable += 1
        gold_candidate = gold_candidates[candidate_match.matched_ids[0]]
        expected_target = gold_candidate.merge_target_version_id
        target_id = candidate.merge_target_prediction_version_id
        target_match = match_by_prediction_id.get(target_id) if target_id is not None else None
        target_is_correct = (
            gold_candidate.expected_decision == "merged"
            and expected_target is not None
            and target_match is not None
            and target_match.status == "matched"
            and target_match.gold_version_ids == (expected_target,)
        )
        if not target_is_correct:
            incorrect += 1

    return incorrect, scorable


def _score_fan_edits(
    gold: BenchmarkSong,
    prediction: SongPrediction,
) -> tuple[RateMetric, RateMetric]:
    known_fan_edits = {
        candidate.benchmark_candidate_id
        for candidate in gold.candidate_expectations
        if candidate.reason == "fan_edit"
    }
    encountered: set[str] = set()
    promoted: set[str] = set()

    for version in prediction.versions:
        candidate_match = match_gold_candidates(version.match_signals, gold)
        if candidate_match.status == "matched":
            candidate_id = candidate_match.matched_ids[0]
            if candidate_id in known_fan_edits:
                encountered.add(candidate_id)
                promoted.add(candidate_id)

    for candidate in prediction.candidates:
        candidate_match = match_gold_candidates(candidate.match_signals, gold)
        if candidate_match.status == "matched":
            candidate_id = candidate_match.matched_ids[0]
            if candidate_id in known_fan_edits:
                encountered.add(candidate_id)
                if candidate.decision == "merged":
                    promoted.add(candidate_id)

    return (
        _rate_metric(len(promoted), len(encountered)),
        _rate_metric(len(encountered), len(known_fan_edits)),
    )


def _score_contributors(
    gold: BenchmarkSong,
    prediction: SongPrediction,
    representatives: dict[str, str],
) -> ClassificationMetric:
    gold_by_id = {version.benchmark_version_id: version for version in gold.versions}
    prediction_by_id = {version.prediction_version_id: version for version in prediction.versions}
    gold_keys: list[tuple[str, str, str]] = []
    predicted_keys: list[tuple[str, str, str]] = []

    for gold_version_id, prediction_version_id in representatives.items():
        gold_keys.extend(
            (gold_version_id, normalize_text(contributor.name), contributor.role)
            for contributor in gold_by_id[gold_version_id].contributors
        )
        predicted_keys.extend(
            (gold_version_id, normalize_text(contributor.name), contributor.role)
            for contributor in prediction_by_id[prediction_version_id].contributors
        )
    return _counter_metric(gold_keys, predicted_keys)


def _score_evidence_coverage(prediction: SongPrediction) -> RateMetric:
    assertion_evidence = [
        *(version.existence_evidence_ids for version in prediction.versions),
        *(
            contributor.evidence_ids
            for version in prediction.versions
            for contributor in version.contributors
        ),
        *(candidate.evidence_ids for candidate in prediction.candidates),
        *(change.evidence_ids for change in prediction.changes),
        *(relationship.evidence_ids for relationship in prediction.relationships),
    ]
    supported = sum(bool(evidence_ids) for evidence_ids in assertion_evidence)
    return _rate_metric(supported, len(assertion_evidence))


def _score_differences(
    gold: BenchmarkSong,
    prediction: SongPrediction,
    version_map: dict[str, str],
) -> ClassificationMetric:
    gold_keys = [
        (
            change.from_version_id,
            change.to_version_id,
            change.category,
            normalize_text(change.detail),
        )
        for change in gold.changes
    ]
    predicted_keys: list[tuple[str, ...]] = []
    for change in prediction.changes:
        from_version_id = version_map.get(change.from_prediction_version_id)
        to_version_id = version_map.get(change.to_prediction_version_id)
        if from_version_id is None or to_version_id is None:
            predicted_keys.append(("unmatched-change", change.prediction_change_id))
        else:
            predicted_keys.append(
                (
                    from_version_id,
                    to_version_id,
                    change.category,
                    normalize_text(change.detail),
                )
            )
    return _counter_metric(gold_keys, predicted_keys)


def _score_relationships(
    gold: BenchmarkSong,
    prediction: SongPrediction,
    version_map: dict[str, str],
) -> tuple[ClassificationMetric, RateMetric]:
    gold_certainties = {
        (
            relationship.subject_version_id,
            relationship.relationship_type,
            relationship.object_version_id,
        ): relationship.certainty
        for relationship in gold.relationships
    }
    predicted_edges: list[tuple[str, tuple[str, str, str], str]] = []
    unmatched_keys: list[tuple[str, ...]] = []
    for relationship in prediction.relationships:
        subject_id = version_map.get(relationship.subject_prediction_version_id)
        object_id = version_map.get(relationship.object_prediction_version_id)
        if subject_id is None or object_id is None:
            unmatched_keys.append(
                ("unmatched-relationship", relationship.prediction_relationship_id)
            )
        else:
            predicted_edges.append(
                (
                    relationship.prediction_relationship_id,
                    (subject_id, relationship.relationship_type, object_id),
                    relationship.certainty,
                )
            )

    gold_keys = list(gold_certainties)
    predicted_keys: list[tuple[str, ...]] = [
        *(edge_key for _, edge_key, _ in predicted_edges),
        *unmatched_keys,
    ]
    metric = _counter_metric(gold_keys, predicted_keys)
    predicted_by_key: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for prediction_id, edge_key, certainty in predicted_edges:
        predicted_by_key[edge_key].append((prediction_id, certainty))

    matched_certainties = 0
    correct_certainties = 0
    for edge_key, gold_certainty in gold_certainties.items():
        candidates = sorted(predicted_by_key.get(edge_key, []))
        if candidates:
            matched_certainties += 1
            correct_certainties += candidates[0][1] == gold_certainty
    return metric, _rate_metric(correct_certainties, matched_certainties)


def _counter_metric(
    gold_items: Iterable[Hashable],
    predicted_items: Iterable[Hashable],
) -> ClassificationMetric:
    gold_counts: Counter[Hashable] = Counter(gold_items)
    predicted_counts: Counter[Hashable] = Counter(predicted_items)
    true_positives = sum((gold_counts & predicted_counts).values())
    return _classification_metric(
        true_positives=true_positives,
        false_positives=sum(predicted_counts.values()) - true_positives,
        false_negatives=sum(gold_counts.values()) - true_positives,
    )


def _classification_metric(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> ClassificationMetric:
    precision = _optional_ratio(true_positives, true_positives + false_positives)
    recall = _optional_ratio(true_positives, true_positives + false_negatives)
    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return ClassificationMetric(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _rate_metric(numerator: int, denominator: int) -> RateMetric:
    return RateMetric(
        numerator=numerator,
        denominator=denominator,
        value=_optional_ratio(numerator, denominator),
    )


def _optional_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _representative_sort_key(match: VersionMatch) -> tuple[int, str]:
    method_order = {
        "external_id": 0,
        "filename": 1,
        "alias": 2,
        "candidate_merge": 3,
        "none": 4,
    }
    return method_order[match.method], match.prediction_version_id
