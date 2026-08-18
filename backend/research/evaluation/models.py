"""Validated data contract for Trackline benchmark fixtures."""

from collections.abc import Iterable
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    ),
]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

AnnotationStatus = Literal["synthetic", "draft", "reviewed"]
CandidateDecision = Literal["merged", "rejected", "unverified"]
CandidateReason = Literal[
    "fan_edit",
    "duplicate_reference",
    "same_audio_new_upload",
    "same_audio_new_title",
    "insufficient_evidence",
    "unverified_legitimacy",
    "not_target_song_work",
    "other",
]
ChangeCategory = Literal[
    "contributor_added",
    "contributor_removed",
    "vocals_changed",
    "lyrics_changed",
    "production_changed",
    "arrangement_changed",
    "instrumental_changed",
    "mix_master_changed",
    "other",
]
ContributorRole = Literal["vocals", "production", "other", "unknown"]
ExistenceConfidence = Literal["high", "medium"]
IndeterminateScope = Literal[
    "version",
    "candidate",
    "contributor",
    "change",
    "relationship",
    "other",
]
RelationshipCertainty = Literal["confirmed", "possible"]
RelationshipType = Literal["derived_from", "post_release_revision_of"]
VersionClassification = Literal["major", "minor"]
VersionType = Literal[
    "demo",
    "reference_track",
    "alternate_feature",
    "alternate_vocals",
    "alternate_production",
    "alternate_arrangement",
    "alternate_mix",
    "official_release",
    "post_release_revision",
    "other",
]


class StrictModel(BaseModel):
    """Base model that prevents unnoticed fixture fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class BenchmarkAnnotation(StrictModel):
    """Records who created or reviewed a benchmark annotation."""

    annotator: NonEmptyString
    annotated_at: datetime
    status: AnnotationStatus
    notes: NonEmptyString | None = None

    @field_validator("annotated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("annotated_at must include a timezone")
        return value


class SongWorkIdentity(StrictModel):
    """Human-reviewed identity of the artist-specific SongWork."""

    canonical_title: NonEmptyString
    artists: list[NonEmptyString] = Field(min_length=1)
    aliases: list[NonEmptyString] = Field(default_factory=list)

    @field_validator("artists", "aliases")
    @classmethod
    def require_unique_names(cls, values: list[str]) -> list[str]:
        duplicates = _duplicates(value.casefold() for value in values)
        if duplicates:
            raise ValueError(f"values must be unique; repeated: {_display(duplicates)}")
        return values


class ExternalIdentity(StrictModel):
    """Provider-qualified stable identity used only as a matching signal."""

    provider: NonEmptyString
    value: NonEmptyString


class MatchSignals(StrictModel):
    """Auditable exact signals that may later pair predictions with gold versions."""

    aliases: list[NonEmptyString] = Field(default_factory=list)
    filenames: list[NonEmptyString] = Field(default_factory=list)
    external_ids: list[ExternalIdentity] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_signal_and_uniqueness(self) -> Self:
        if not (self.aliases or self.filenames or self.external_ids):
            raise ValueError("at least one alias, filename, or external ID is required")

        issues: list[str] = []
        for label, values in (
            ("aliases", self.aliases),
            ("filenames", self.filenames),
        ):
            duplicates = _duplicates(value.casefold() for value in values)
            if duplicates:
                issues.append(f"{label} contain repeated values: {_display(duplicates)}")

        external_values = (
            (identity.provider.casefold(), identity.value.casefold())
            for identity in self.external_ids
        )
        duplicate_external_ids = _duplicates(external_values)
        if duplicate_external_ids:
            issues.append("external_ids contain repeated provider/value pairs")

        if issues:
            raise ValueError("; ".join(issues))
        return self


class BenchmarkEvidence(StrictModel):
    """Exact excerpt or locator supporting a benchmark assertion."""

    evidence_id: Identifier
    locator: NonEmptyString
    excerpt: NonEmptyString
    extraction_method: Literal["manual_annotation", "recorded_extraction"]
    extraction_run_id: Identifier


class BenchmarkSource(StrictModel):
    """A retrieved source and the evidence retained from it."""

    source_id: Identifier
    url: HttpUrl
    title: NonEmptyString
    publisher: NonEmptyString
    retrieved_at: datetime
    content_hash: Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
    retrieval_method: Literal["manual", "http", "api", "recorded_fixture"]
    retrieval_run_id: Identifier
    evidence: list[BenchmarkEvidence] = Field(min_length=1)

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value


class BenchmarkContributor(StrictModel):
    """A source-backed contributor attached to one Version."""

    name: NonEmptyString
    role: ContributorRole
    evidence_ids: list[Identifier] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _raise_for_duplicate_references(values)
        return values


class BenchmarkVersion(StrictModel):
    """A legitimate canonical Version in the benchmark answer key."""

    benchmark_version_id: Identifier
    display_label: NonEmptyString
    version_type: VersionType
    classification: VersionClassification | None = None
    existence_confidence: ExistenceConfidence
    match_signals: MatchSignals
    contributors: list[BenchmarkContributor] = Field(default_factory=list)
    existence_evidence_ids: list[Identifier] = Field(min_length=1)

    @field_validator("existence_evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _raise_for_duplicate_references(values)
        return values


class BenchmarkCandidateExpectation(StrictModel):
    """Expected handling of a discovered noncanonical candidate."""

    benchmark_candidate_id: Identifier
    label: NonEmptyString
    expected_decision: CandidateDecision
    reason: CandidateReason
    reason_detail: NonEmptyString | None = None
    merge_target_version_id: Identifier | None = None
    match_signals: MatchSignals
    evidence_ids: list[Identifier] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _raise_for_duplicate_references(values)
        return values

    @model_validator(mode="after")
    def require_decision_details(self) -> Self:
        merge_reasons = {
            "duplicate_reference",
            "same_audio_new_upload",
            "same_audio_new_title",
        }
        if self.expected_decision == "merged":
            if self.merge_target_version_id is None:
                raise ValueError("a merged candidate requires merge_target_version_id")
            if self.reason not in merge_reasons:
                raise ValueError("a merged candidate requires a duplicate or same-audio reason")
        elif self.merge_target_version_id is not None:
            raise ValueError("only a merged candidate may have merge_target_version_id")

        if self.reason == "other" and self.reason_detail is None:
            raise ValueError("reason_detail is required when reason is other")
        return self


class BenchmarkChange(StrictModel):
    """A source-backed audible difference between two benchmark Versions."""

    benchmark_change_id: Identifier
    from_version_id: Identifier
    to_version_id: Identifier
    category: ChangeCategory
    detail: NonEmptyString
    evidence_ids: list[Identifier] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _raise_for_duplicate_references(values)
        return values


class BenchmarkRelationship(StrictModel):
    """A canonical edge from a newer Version to an earlier Version."""

    benchmark_relationship_id: Identifier
    subject_version_id: Identifier
    relationship_type: RelationshipType
    object_version_id: Identifier
    certainty: RelationshipCertainty
    evidence_ids: list[Identifier] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _raise_for_duplicate_references(values)
        return values


class BenchmarkIndeterminateItem(StrictModel):
    """A visible annotation intentionally excluded from ordinary scoring."""

    benchmark_indeterminate_id: Identifier
    scope: IndeterminateScope
    description: NonEmptyString
    evidence_ids: list[Identifier] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence(cls, values: list[str]) -> list[str]:
        _raise_for_duplicate_references(values)
        return values


class BenchmarkSong(StrictModel):
    """Complete version 1 benchmark answer key for one SongWork."""

    schema_version: Literal["1.0"]
    benchmark_song_id: Identifier
    split: Literal["development", "held_out"]
    annotation: BenchmarkAnnotation
    song_work: SongWorkIdentity
    sources: list[BenchmarkSource] = Field(min_length=1)
    versions: list[BenchmarkVersion] = Field(min_length=1)
    candidate_expectations: list[BenchmarkCandidateExpectation] = Field(default_factory=list)
    changes: list[BenchmarkChange] = Field(default_factory=list)
    relationships: list[BenchmarkRelationship] = Field(default_factory=list)
    indeterminate_items: list[BenchmarkIndeterminateItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_fixture_semantics(self) -> Self:
        issues: list[str] = []

        _record_duplicate_ids(issues, "source", (source.source_id for source in self.sources))
        _record_duplicate_ids(
            issues,
            "version",
            (version.benchmark_version_id for version in self.versions),
        )
        _record_duplicate_ids(
            issues,
            "candidate",
            (candidate.benchmark_candidate_id for candidate in self.candidate_expectations),
        )
        _record_duplicate_ids(
            issues,
            "change",
            (change.benchmark_change_id for change in self.changes),
        )
        _record_duplicate_ids(
            issues,
            "relationship",
            (relationship.benchmark_relationship_id for relationship in self.relationships),
        )
        _record_duplicate_ids(
            issues,
            "indeterminate item",
            (item.benchmark_indeterminate_id for item in self.indeterminate_items),
        )

        all_evidence = [evidence for source in self.sources for evidence in source.evidence]
        _record_duplicate_ids(
            issues,
            "evidence",
            (evidence.evidence_id for evidence in all_evidence),
        )
        evidence_ids = {evidence.evidence_id for evidence in all_evidence}
        version_ids = {version.benchmark_version_id for version in self.versions}

        candidate_ids = {
            candidate.benchmark_candidate_id for candidate in self.candidate_expectations
        }
        overlapping_ids = version_ids & candidate_ids
        if overlapping_ids:
            issues.append(
                "canonical versions and noncanonical candidates share IDs: "
                f"{_display(overlapping_ids)}"
            )

        for version in self.versions:
            _record_unknown_evidence(
                issues,
                f"version {version.benchmark_version_id} existence",
                version.existence_evidence_ids,
                evidence_ids,
            )
            contributor_keys = (
                (contributor.name.casefold(), contributor.role)
                for contributor in version.contributors
            )
            duplicate_contributors = _duplicates(contributor_keys)
            if duplicate_contributors:
                issues.append(
                    f"version {version.benchmark_version_id} has repeated contributor/role pairs"
                )
            for contributor in version.contributors:
                _record_unknown_evidence(
                    issues,
                    (f"contributor {contributor.name} on version {version.benchmark_version_id}"),
                    contributor.evidence_ids,
                    evidence_ids,
                )

        for candidate in self.candidate_expectations:
            _record_unknown_evidence(
                issues,
                f"candidate {candidate.benchmark_candidate_id}",
                candidate.evidence_ids,
                evidence_ids,
            )
            target_id = candidate.merge_target_version_id
            if target_id is not None and target_id not in version_ids:
                issues.append(
                    f"candidate {candidate.benchmark_candidate_id} has unknown merge target "
                    f"{target_id}"
                )

        for change in self.changes:
            _record_version_reference(
                issues,
                f"change {change.benchmark_change_id} from_version_id",
                change.from_version_id,
                version_ids,
            )
            _record_version_reference(
                issues,
                f"change {change.benchmark_change_id} to_version_id",
                change.to_version_id,
                version_ids,
            )
            if change.from_version_id == change.to_version_id:
                issues.append(f"change {change.benchmark_change_id} compares a version to itself")
            _record_unknown_evidence(
                issues,
                f"change {change.benchmark_change_id}",
                change.evidence_ids,
                evidence_ids,
            )

        relationship_edges: list[tuple[str, str]] = []
        relationship_keys: list[tuple[str, str, str]] = []
        for relationship in self.relationships:
            _record_version_reference(
                issues,
                f"relationship {relationship.benchmark_relationship_id} subject_version_id",
                relationship.subject_version_id,
                version_ids,
            )
            _record_version_reference(
                issues,
                f"relationship {relationship.benchmark_relationship_id} object_version_id",
                relationship.object_version_id,
                version_ids,
            )
            if relationship.subject_version_id == relationship.object_version_id:
                issues.append(
                    f"relationship {relationship.benchmark_relationship_id} is a self-edge"
                )
            _record_unknown_evidence(
                issues,
                f"relationship {relationship.benchmark_relationship_id}",
                relationship.evidence_ids,
                evidence_ids,
            )
            relationship_edges.append(
                (relationship.subject_version_id, relationship.object_version_id)
            )
            relationship_keys.append(
                (
                    relationship.subject_version_id,
                    relationship.relationship_type,
                    relationship.object_version_id,
                )
            )

        duplicate_relationships = _duplicates(relationship_keys)
        if duplicate_relationships:
            issues.append("relationships contain repeated subject/type/object edges")

        cycle = _find_cycle(version_ids, relationship_edges)
        if cycle is not None:
            issues.append(f"relationships contain a cycle: {' -> '.join(cycle)}")

        for item in self.indeterminate_items:
            _record_unknown_evidence(
                issues,
                f"indeterminate item {item.benchmark_indeterminate_id}",
                item.evidence_ids,
                evidence_ids,
            )

        if issues:
            rendered = "\n- ".join(issues)
            raise ValueError(f"benchmark semantic validation failed:\n- {rendered}")
        return self


def _duplicates[T](values: Iterable[T]) -> set[T]:
    seen: set[T] = set()
    duplicates: set[T] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _display(values: Iterable[object]) -> str:
    return ", ".join(sorted(str(value) for value in values))


def _raise_for_duplicate_references(values: list[str]) -> None:
    duplicates = _duplicates(values)
    if duplicates:
        raise ValueError(f"evidence references must be unique; repeated: {_display(duplicates)}")


def _record_duplicate_ids(issues: list[str], label: str, values: Iterable[str]) -> None:
    duplicates = _duplicates(values)
    if duplicates:
        issues.append(f"duplicate {label} IDs: {_display(duplicates)}")


def _record_unknown_evidence(
    issues: list[str],
    owner: str,
    references: Iterable[str],
    evidence_ids: set[str],
) -> None:
    unknown = set(references) - evidence_ids
    if unknown:
        issues.append(f"{owner} references unknown evidence: {_display(unknown)}")


def _record_version_reference(
    issues: list[str],
    owner: str,
    reference: str,
    version_ids: set[str],
) -> None:
    if reference not in version_ids:
        issues.append(f"{owner} references unknown version: {reference}")


def _find_cycle(
    nodes: set[str],
    edges: Iterable[tuple[str, str]],
) -> list[str] | None:
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for subject_id, object_id in edges:
        if subject_id in adjacency and object_id in adjacency:
            adjacency[subject_id].append(object_id)

    state = {node: 0 for node in nodes}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        path.append(node)
        for neighbor in adjacency[node]:
            if state[neighbor] == 0:
                cycle = visit(neighbor)
                if cycle is not None:
                    return cycle
            elif state[neighbor] == 1:
                start = path.index(neighbor)
                return [*path[start:], neighbor]
        path.pop()
        state[node] = 2
        return None

    for node in sorted(nodes):
        if state[node] == 0:
            cycle = visit(node)
            if cycle is not None:
                return cycle
    return None
