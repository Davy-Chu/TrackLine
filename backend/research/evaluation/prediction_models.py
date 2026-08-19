"""Validated prediction snapshot contract for deterministic benchmark scoring."""

from collections.abc import Iterable
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from research.evaluation.models import (
    CandidateDecision,
    CandidateReason,
    ChangeCategory,
    ContributorRole,
    ExistenceConfidence,
    Identifier,
    MatchSignals,
    NonEmptyString,
    RelationshipCertainty,
    RelationshipType,
    StrictModel,
    VersionType,
)

PredictionOutcome = Literal[
    "lineage_found",
    "no_alternates_found",
    "insufficient_evidence",
]
PredictionRunStatus = Literal["completed", "failed"]


class PredictedContributor(StrictModel):
    """Contributor assertion attached to one predicted Version."""

    name: NonEmptyString
    role: ContributorRole
    evidence_ids: list[Identifier] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _require_unique(values, "evidence references")
        return values


class PredictedVersion(StrictModel):
    """Canonical Version emitted by a recorded pipeline run."""

    prediction_version_id: Identifier
    display_label: NonEmptyString
    version_type: VersionType
    existence_confidence: ExistenceConfidence
    match_signals: MatchSignals
    contributors: list[PredictedContributor] = Field(default_factory=list)
    existence_evidence_ids: list[Identifier] = Field(default_factory=list)

    @field_validator("existence_evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _require_unique(values, "evidence references")
        return values


class PredictedCandidate(StrictModel):
    """Noncanonical candidate decision emitted by a recorded pipeline run."""

    prediction_candidate_id: Identifier
    label: NonEmptyString
    decision: CandidateDecision
    reason: CandidateReason
    merge_target_prediction_version_id: Identifier | None = None
    match_signals: MatchSignals
    evidence_ids: list[Identifier] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _require_unique(values, "evidence references")
        return values

    @model_validator(mode="after")
    def require_merge_target_only_for_merges(self) -> Self:
        if self.decision == "merged" and self.merge_target_prediction_version_id is None:
            raise ValueError("a merged prediction candidate requires a merge target")
        if self.decision != "merged" and self.merge_target_prediction_version_id is not None:
            raise ValueError("only a merged prediction candidate may have a merge target")
        return self


class PredictedChange(StrictModel):
    """Structured difference asserted between two predicted Versions."""

    prediction_change_id: Identifier
    from_prediction_version_id: Identifier
    to_prediction_version_id: Identifier
    category: ChangeCategory
    detail: NonEmptyString
    evidence_ids: list[Identifier] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _require_unique(values, "evidence references")
        return values


class PredictedRelationship(StrictModel):
    """Canonical relationship asserted between two predicted Versions."""

    prediction_relationship_id: Identifier
    subject_prediction_version_id: Identifier
    relationship_type: RelationshipType
    object_prediction_version_id: Identifier
    certainty: RelationshipCertainty
    evidence_ids: list[Identifier] = Field(default_factory=list)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _require_unique(values, "evidence references")
        return values


class SongPrediction(StrictModel):
    """Immutable prediction snapshot for one benchmark SongWork."""

    schema_version: Literal["1.0"]
    benchmark_song_id: Identifier
    run_id: Identifier
    run_status: PredictionRunStatus
    outcome: PredictionOutcome | None = None
    failure_reason: NonEmptyString | None = None
    latency_ms: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0)
    source_count: int = Field(ge=0)
    versions: list[PredictedVersion] = Field(default_factory=list)
    candidates: list[PredictedCandidate] = Field(default_factory=list)
    changes: list[PredictedChange] = Field(default_factory=list)
    relationships: list[PredictedRelationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_prediction_semantics(self) -> Self:
        issues: list[str] = []

        if self.run_status == "completed":
            if self.outcome is None:
                issues.append("a completed prediction requires an outcome")
            if self.failure_reason is not None:
                issues.append("a completed prediction cannot have failure_reason")
        else:
            if self.outcome is not None:
                issues.append("a failed prediction cannot have a completed outcome")
            if self.failure_reason is None:
                issues.append("a failed prediction requires failure_reason")
            if self.versions or self.candidates or self.changes or self.relationships:
                issues.append("a failed prediction cannot publish partial result collections")

        version_ids = [version.prediction_version_id for version in self.versions]
        candidate_ids = [candidate.prediction_candidate_id for candidate in self.candidates]
        _record_duplicate_ids(issues, "version", version_ids)
        _record_duplicate_ids(issues, "candidate", candidate_ids)
        _record_duplicate_ids(
            issues,
            "change",
            [change.prediction_change_id for change in self.changes],
        )
        _record_duplicate_ids(
            issues,
            "relationship",
            [relationship.prediction_relationship_id for relationship in self.relationships],
        )

        overlapping_ids = set(version_ids) & set(candidate_ids)
        if overlapping_ids:
            issues.append(
                "predicted canonical versions and candidates share IDs: "
                f"{_display(overlapping_ids)}"
            )

        known_versions = set(version_ids)
        for version in self.versions:
            contributor_keys = [
                (contributor.name.casefold(), contributor.role)
                for contributor in version.contributors
            ]
            duplicates = _duplicates(contributor_keys)
            if duplicates:
                issues.append(
                    f"predicted version {version.prediction_version_id} has repeated "
                    "contributor/role pairs"
                )

        for candidate in self.candidates:
            target_id = candidate.merge_target_prediction_version_id
            if target_id is not None and target_id not in known_versions:
                issues.append(
                    f"predicted candidate {candidate.prediction_candidate_id} has unknown "
                    f"merge target {target_id}"
                )

        for change in self.changes:
            _record_version_reference(
                issues,
                f"predicted change {change.prediction_change_id} from_prediction_version_id",
                change.from_prediction_version_id,
                known_versions,
            )
            _record_version_reference(
                issues,
                f"predicted change {change.prediction_change_id} to_prediction_version_id",
                change.to_prediction_version_id,
                known_versions,
            )
            if change.from_prediction_version_id == change.to_prediction_version_id:
                issues.append(
                    f"predicted change {change.prediction_change_id} compares a version to itself"
                )

        relationship_keys: list[tuple[str, str, str]] = []
        for relationship in self.relationships:
            _record_version_reference(
                issues,
                (
                    f"predicted relationship {relationship.prediction_relationship_id} "
                    "subject_prediction_version_id"
                ),
                relationship.subject_prediction_version_id,
                known_versions,
            )
            _record_version_reference(
                issues,
                (
                    f"predicted relationship {relationship.prediction_relationship_id} "
                    "object_prediction_version_id"
                ),
                relationship.object_prediction_version_id,
                known_versions,
            )
            if (
                relationship.subject_prediction_version_id
                == relationship.object_prediction_version_id
            ):
                issues.append(
                    f"predicted relationship {relationship.prediction_relationship_id} is a "
                    "self-edge"
                )
            relationship_keys.append(
                (
                    relationship.subject_prediction_version_id,
                    relationship.relationship_type,
                    relationship.object_prediction_version_id,
                )
            )

        if _duplicates(relationship_keys):
            issues.append("predicted relationships contain repeated subject/type/object edges")

        if issues:
            rendered = "\n- ".join(issues)
            raise ValueError(f"prediction semantic validation failed:\n- {rendered}")
        return self


def _require_unique(values: list[str], label: str) -> None:
    duplicates = _duplicates(values)
    if duplicates:
        raise ValueError(f"{label} must be unique; repeated: {_display(duplicates)}")


def _record_duplicate_ids(issues: list[str], label: str, values: list[str]) -> None:
    duplicates = _duplicates(values)
    if duplicates:
        issues.append(f"duplicate predicted {label} IDs: {_display(duplicates)}")


def _record_version_reference(
    issues: list[str],
    owner: str,
    reference: str,
    known_versions: set[str],
) -> None:
    if reference not in known_versions:
        issues.append(f"{owner} references unknown predicted version: {reference}")


def _duplicates[T](values: list[T]) -> set[T]:
    seen: set[T] = set()
    duplicates: set[T] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _display(values: Iterable[object]) -> str:
    return ", ".join(sorted(str(value) for value in values))
