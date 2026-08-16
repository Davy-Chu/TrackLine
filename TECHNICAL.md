# TECHNICAL.md

# Trackline — Technical Specification

## Technical Goal

Build the smallest architecture that can reliably:

1. resolve a song/work
2. discover relevant public sources
3. extract source-backed claims
4. identify genuine candidate versions
5. merge duplicate references
6. filter fan edits
7. recover meaningful differences
8. infer only supported lineage relationships
9. persist the result
10. expose the lineage through a simple API/UI

The architecture should optimize for pipeline iteration and debuggability rather than early scale.

---

# Recommended Architecture

Use a **modular monolith plus one background worker**.

```text
Next.js
   |
   v
FastAPI
   |
   v
PostgreSQL
   ^
   |
Research Worker
   |
   +--> Music APIs
   +--> Web/Search
   +--> Trackers
   +--> OpenAI
```

Components:

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Python
- **Database:** PostgreSQL
- **Background processing:** one Python worker using the same backend codebase
- **Local development:** Docker Compose

Do not introduce Redis, Kafka, Neo4j, Elasticsearch, Kubernetes, or microservices until a measured bottleneck justifies them.

---

# Repository-Level Boundaries

Suggested logical modules:

```text
frontend/

backend/
  api/
  domain/
  database/
  research/
    discovery/
    extraction/
    resolution/
    reconciliation/
    evaluation/
  sources/
  jobs/
  llm/
```

Keep business logic modular even though deployment remains simple.

---

# Core Domain Entities

## Artist

Canonical artist/contributor identity.

Relates to:

- SongWorkArtistCredit
- VersionContributor
- ExternalIdentity

## SongWorkArtistCredit

Ordered relationship between Artist and SongWork.

It supports collaborations while identifying the artist/context that owns the lineage for Milestone 0. Do not model primary artist as a single foreign key on SongWork.

## SongWork

An artist-specific creative lineage independent of any one recording iteration.

SongWork is not a universal composition identity. Covers and independent interpretations by unrelated artists use separate SongWorks. A songwriter/reference demo may belong to the target SongWork when source evidence places it in that artist recording's development path.

Transferred songs remain separate SongWorks during Milestone 0. A future cross-SongWork relationship may describe a transfer or adaptation without changing SongWork identity.

Relates to:

- SongWorkArtistCredit
- SongAlias
- Version
- VersionCandidate
- ResearchJob
- ExternalIdentity

## SongAlias

Alternative name for a SongWork.

Used for:

- search
- entity resolution
- renamed/leaked titles

## Version

A resolved legitimate artist/studio iteration of a SongWork.

A Version is our canonical internal identity for a recording/iteration, not every web reference we discover.

A Version requires evidence of a distinct legitimate audio iteration. A title, filename, leak, upload, platform, or release event alone does not create a Version. Reliable documentary evidence may establish a Version even when no playable audio is public.

Minimum resolved fields should support:

- display label and whether it is authentic or generated
- version type
- optional major/minor classification
- version existence confidence: High or Medium
- approximate date/range and date precision
- leak/discovery date when supported
- current resolution decision and provenance

Relates to:

- SongWork
- VersionAlias
- VersionContributor
- EraProject
- VersionRelationship
- VersionChange
- Claim
- ExternalMedia
- ExternalIdentity

## VersionCandidate

A pre-canonical candidate assembled from one or more source observations.

Candidate states:

- unresolved
- unverified
- promoted
- merged
- rejected

Store merge targets, rejection reason codes, and supporting evidence. Low-confidence candidates are returned as Unverified Versions. During Milestone 0, encountered fan edits and duplicate references must be retained for audit and evaluation but never enter canonical Version lineage.

## VersionAlias

Alternative labels referring to the same Version.

Examples:

- tracker label
- leak title
- alternate upload title
- known shorthand

## EraProject

Album/project/creative era associated with a Version.

Do not attach era only at SongWork level because versions may move between projects.

Treat Version-to-EraProject association as source-backed and potentially many-to-many. Do not require canonical project normalization before the benchmark demonstrates a need.

## VersionContributor

Relationship between Artist and Version.

Initial role categories:

- vocals
- production
- other
- unknown

Do not over-model credit taxonomy yet.

## VersionRelationship

Represents lineage between Versions.

Initial canonical types:

- DERIVED_FROM
- POST_RELEASE_REVISION_OF

Use one direction consistently: the subject is the newer/derived Version and the object is the earlier/source Version. Component reuse and release events are structured claims or changes unless the benchmark proves that dedicated relationship types improve accuracy.

Relationships support:

- Confirmed
- Possible

Unknown lineage is represented by no canonical edge. Hypotheses may be retained outside canonical lineage. Do not assume lineage is linear; reject self-edges and detect cycles for review.

## VersionChange

Structured meaningful difference between Versions.

Each change identifies a `from_version`, `to_version`, category, structured detail, and supporting Claims. Direction is required so categories such as contributor added/removed are unambiguous. A comparison may exist without asserting a lineage edge.

Initial change categories:

- contributor added
- contributor removed
- vocals changed
- lyrics changed
- production changed
- arrangement changed
- instrumental changed
- mix/master changed
- other

## Source

A stable identity for an external source or document.

Conceptual fields:

- URL
- title
- source type
- publisher/uploader
- external identifier if relevant

## SourceRetrieval

An immutable record of retrieving a Source at a point in time.

Conceptual fields:

- retrieval time
- final URL and response metadata
- content hash
- permitted normalized content or excerpt
- source locator information such as page, timestamp, heading, or character range
- fetch status and failure reason

Store full source content only where provider terms and content rights permit it. Otherwise retain enough metadata, hashes, and evidence excerpts/locators to audit the Claim.

## Claim

A source-supported assertion about a domain entity.

Claims use a controlled predicate registry and typed values. A value may be a scalar, date/range, structured value, or reference to another internal entity.

Conceptually:

```text
subject -> predicate -> value
```

Examples:

```text
Version X -> HAS_FILENAME -> "..."
Version X -> HAS_CONTRIBUTOR -> Artist Y
Version X -> RECORDED_DURING -> Project Z
Version B -> DERIVED_FROM -> Version A
```

Important rule:

> External data should enter the system as Claims before becoming resolved display state.

Claims also retain extraction method, source wording/qualifiers, and the ResearchJob that produced them. Provider payloads and unrestricted provider-specific JSON must not become the core claim schema.

## ClaimEvidence

Connects a Claim to a SourceRetrieval and an exact evidence excerpt or locator.

Equivalent assertions from different sources may support the same normalized proposition, but each source-specific assertion and qualifier must remain independently auditable. Sources that copy the same upstream assertion are not independent corroboration.

## ResolutionDecision

Records how Claims become current displayed knowledge.

A ResolutionDecision identifies the subject/predicate, selected display value, supporting Claims, contradicting Claims, method/rule version, rationale, and optional reviewer override. Resolved domain fields must remain traceable through this record rather than being written from raw LLM output.

## ExternalMedia

Optional external audio/video representation of a Version.

Separate from Source because a URL may be evidence, playable media, or both.

Media availability does not affect Version existence confidence. Store platform, URL, uploader/publisher, media type, authorization category, availability status, and retrieval time. Prefer official or authorized media deterministically; a missing link never blocks a Version.

## ResearchJob

Represents one durable research run, including manual refreshes. A refresh creates a new ResearchJob and preserves earlier Claims and decisions.

Execution statuses:

- pending
- running
- completed
- failed

Store the current pipeline stage separately:

- discover
- fetch
- extract
- resolve
- reconcile
- persist

Completed research outcomes:

- lineage_found
- no_alternates_found
- insufficient_evidence

An operational failure is not a research outcome.

Store operational metrics such as:

- start/end time
- source count
- LLM usage/cost
- failure reason
- attempt count and lease expiry
- prompt/model/rule versions

## ExternalIdentity

Maps Trackline entities to provider IDs.

Examples:

- MusicBrainz
- Spotify
- Discogs

Trackline internal IDs must never depend on external provider IDs.

---

# Expensive-to-Reverse Decisions

These are considered locked:

1. SongWork and Version are separate identities.
2. SongWork is an artist-specific creative lineage, not a universal composition.
3. VersionCandidate is separate from canonical Version.
4. Claims/evidence and ResolutionDecisions are separate from resolved display fields.
5. Contributors attach to individual Versions; SongWork artist credits are separate.
6. Version lineage supports branching and uncertainty.
7. Media availability is independent of Version existence confidence.
8. Trackline owns stable internal IDs.
9. External providers are isolated behind adapters.
10. PostgreSQL is the system of record.
11. Milestone 0 research triggering is internal only.

Do not simplify these boundaries for short-term convenience.

---

# External Interfaces

## Frontend -> Backend

Minimum MVP API:

### Search

`GET /search?q=...`

Returns stored SongWorks and aliases. Search is read-only and must not create canonical entities or trigger research as a side effect.

### Song

`GET /songs/{song_id}`

Returns song-level information.

### Lineage

`GET /songs/{song_id}/lineage`

Returns:

- versions
- relationships
- changes
- Version existence confidence
- relationship certainty
- claim confidence through resolved value references
- sources/evidence references
- external media

Each resolved externally derived value should include a reference to its ResolutionDecision. Disputed values include supporting and contradicting Claim references rather than only a page-level bibliography.

### Version Detail

`GET /versions/{version_id}`

Returns full Version detail.

### Start Research — Internal Milestone 0 Interface

`POST /internal/research-requests`

Accepts either an existing `song_work_id` or a resolved artist/title candidate and creates a ResearchJob if one is not already active.

This interface is available only to local/internal developer tooling during Milestone 0. It must resolve ambiguous input before creating a SongWork; raw search text must not create canonical entities automatically.

Public missing-song research is deferred to Milestone 1 after latency, cost, failure rate, deduplication, quotas, and abuse controls are measured.

### Research Status

`GET /research-jobs/{job_id}`

Frontend polls this endpoint.

No WebSockets are required initially.

Milestone 0 does not require public authentication because the application remains local/internal. Do not expose the internal research interface in a public deployment.

### Internal Review Tooling

Milestone 0 may use a CLI or internal-only endpoint to inspect candidates, promote/reject a VersionCandidate, and resolve disputed Claims. Every manual action must create a ResolutionDecision with rationale; it must not mutate or delete the underlying Claims. No public moderation or crowdsourced editing UI is required.

---

# Background Jobs

Research must not run inside the HTTP request lifecycle.

Initial job granularity:

```text
research_song(song_work_id)
```

Internal stages:

```text
DISCOVER
  ->
FETCH
  ->
EXTRACT
  ->
RESOLVE
  ->
RECONCILE
  ->
PERSIST
```

Keep these as separate functions/modules but one coarse queued job for MVP.

Initial queue implementation:

- store ResearchJob in PostgreSQL
- worker claims pending jobs
- worker updates status

Deploy exactly one worker during Milestone 0. Still use an atomic claim and expiring lease so a crashed worker can be recovered safely. Retries must be idempotent and must not duplicate entities, candidates, Claims, media, relationships, or ResolutionDecisions.

Do not add Redis initially.

---

# Source Adapter Boundary

External providers must not leak their schemas into the rest of the application.

Use provider-specific adapters that return Trackline internal structures.

Adapters return provider-neutral retrieval metadata, external identities, and candidate observations suitable for conversion into Claims. They must not write provider assertions directly into canonical Version state.

Provider selection for Milestone 0 is benchmark-driven. Implement only the minimum adapters needed by the current benchmark subset, then extract shared interfaces from observed needs. Respect provider terms, robots rules, rate limits, licensing, and storage restrictions.

Important adapters may include:

## MusicBrainz

Use for:

- artist identity
- work/recording identity
- aliases
- releases
- official relationships

Treat as a released-metadata and identity foundation, not as canonical truth or an unreleased lineage source. Validate how MusicBrainz Work/Recording semantics map to Trackline's artist-specific SongWork before relying on it for entity creation.

## Spotify

Use selectively for:

- released catalog identity
- official streaming links
- artist/catalog metadata

Do not depend on Spotify for unreleased history.

## Discogs

Optional during Milestone 0.

Use only if it materially improves:

- release identity
- credits
- alternate releases

Respect its API/data licensing constraints.

## Specialist Trackers

Examples:

- ArtistGrid-hosted trackers
- artist-specific spreadsheets/databases

Use for:

- candidate version discovery
- filenames
- leak dates
- contributor differences
- version descriptions
- era associations

Trackers are evidence, not canonical truth.

Record known upstream dependencies between trackers. Multiple trackers that copy the same source do not provide independent corroboration.

## Web Search Provider

Abstract behind:

```text
SearchProvider
```

Responsibilities:

- targeted web discovery
- exact filename searches
- interviews
- making-of content
- historical articles
- tracklists
- forum discussions

Do not couple research logic to one search vendor.

## Web Fetcher

Separate from SearchProvider.

Responsibilities:

- retrieve a discovered page
- return normalized readable content and metadata

The fetcher must also return retrieval status, final URL, content hash, and evidence locators. It must not bypass access controls or store full content when terms or rights do not permit it.

## YouTube

Use for:

- candidate media links
- upload metadata
- duration
- corroboration

Do not accept uploader titles as authoritative version identity.

## Reddit / Forums

Use mainly as lead-generation sources.

Do not promote a forum claim directly to resolved truth without corroboration.

---

# LLM Boundaries

LLMs are server-side only.

Do not call OpenAI directly from the frontend.

## LLM Use 1 — Source Extraction

Input:

- target SongWork
- retrieved source content

Output:

- schema-constrained explicit Claims
- exact evidence excerpts or locators for each Claim

The model must be instructed to extract only source-supported information. Reject invalid structured output or Claims without evidence anchors; do not silently repair them into resolved facts.

## LLM Use 2 — Candidate Version Matching

Use when deterministic rules cannot decide whether two references describe the same Version.

Possible output:

- likely same
- likely different
- uncertain

Deterministic evidence wins whenever available.

“Deterministic” does not mean every non-LLM signal is decisive. Exact stable provider identity or an authenticated filename may be strong; similar duration, contributors, or titles are matching features rather than proof.

## LLM Use 3 — Reconciliation Assistance

Optional after deterministic reconciliation has been evaluated. Use only to classify disagreements or propose relationships between Claims.

The LLM may assist but must not silently choose truth.

## LLM Use 4 — User-Facing Summary

Deferred during the first Milestone 0 vertical slice. Initially generate concise histories deterministically from stored resolved data. If an LLM summary is later added, it may use only that stored data and must not introduce new facts.

## LLM Non-Goals

Never:

- ask the model to generate the song history from memory
- write unsupported model facts directly into Version state
- let the model be the sole confidence system
- let model output override source evidence

Wrap model calls behind a small `LLMClient` abstraction so exact model/provider choice remains replaceable.

Store model, prompt/schema version, token usage, cost, and call status for reproducibility and evaluation. Unit tests use recorded responses, not live or paid calls.

---

# Data Reconciliation Rules

## Sources never overwrite one another

Store conflicting source Claims separately.

## Compatible Claims

Example:

- February 22, 2010
- February 2010
- early 2010

These may be reconciled into a compatible display value while preserving originals.

## Genuine Contradictions

Keep the disagreement attached to the affected resolved value and expose it through the API.

## Strong Authority Mismatch

Prefer stronger first-party evidence for displayed state, but preserve weaker Claims internally.

Source authority must use an explicit, testable policy. Authority is claim-dependent: an official release page may be strong for release metadata but weak for undocumented session chronology.

## LLM vs Source

LLM output cannot establish a fact. It may extract a source assertion or propose a reconciliation decision, but displayed knowledge must cite source Claims and deterministic or reviewed resolution logic.

## Confidence Contract

Confidence is assigned by a versioned, testable resolution policy and recorded in the relevant ResolutionDecision. Do not derive public confidence directly from an LLM score.

Keep these scopes separate:

- **Version existence confidence** controls canonical promotion and Unverified placement.
- **Claim confidence** describes support for a displayed assertion such as a date, filename, or contributor.
- **Relationship certainty** is Confirmed or Possible and applies only to canonical edges.
- **Media availability** is a separate property and does not raise or lower existence confidence.

Initial qualitative rules:

- **High**: explicit strong first-party/authentic documentation, or multiple independent reliable sources with no material unresolved contradiction
- **Medium**: at least one credible direct source or multiple consistent indirect signals sufficient to support the assertion, with material uncertainty disclosed
- **Low**: ambiguous, weak, derivative, or insufficiently corroborated evidence; a low-confidence VersionCandidate remains Unverified

Source authority is claim-dependent and corroboration requires operational independence. Record the reason for every manual override or rule-based promotion/demotion. Calibrate these rules against the benchmark before adding a sophisticated scoring formula.

---

# Version Resolution Priorities

Pipeline priority order:

1. create source-backed VersionCandidates
2. identify genuine distinct versions
3. merge duplicate references
4. reject fan edits with an auditable reason
5. attach evidence to displayed claims
6. recover meaningful differences
7. infer lineage relationships only where supported

Do not optimize relationship inference before version identity is reliable.

Useful deterministic matching signals include:

- exact filename
- exact external ID
- same duration
- same known contributors
- same source metadata
- strong alias match

Do not treat any single weak signal as proof.

Canonical promotion requires separate support for legitimacy and distinctness. A playable file is not required, but documentary evidence must explicitly support the existence of a distinct audio iteration. Evidence that establishes existence does not automatically establish detailed musical differences.

---

# Search and Persistence

Use PostgreSQL for:

- canonical entities
- VersionCandidates and rejection/merge decisions
- aliases
- fuzzy title lookup
- research jobs
- Source/SourceRetrieval/Claim persistence
- ResolutionDecisions and research history

Keep the supported Milestone 0 artists in an explicit allowlist/configuration keyed by Trackline Artist IDs. Do not infer research eligibility from arbitrary search input.

PostgreSQL full-text/trigram search should be sufficient for MVP scale.

Do not add Elasticsearch unless search quality/performance becomes a measured problem.

Manual refresh creates a new ResearchJob. It must preserve prior Claims and decisions, reconcile new observations idempotently, and identify which run produced the current display projection.

---

# Evaluation

Maintain a manually verified benchmark dataset.

Create the benchmark and metric contract before building the full persistence model. Use development and held-out evaluation subsets so prompts and matching rules are not tuned directly against every scored example.

For each benchmark SongWork, record:

- aliases
- known genuine versions
- known version aliases
- known fan edits
- contributors
- known differences
- chronology
- confirmed relationships
- uncertain relationships
- strong supporting sources
- indeterminate/disputed annotations
- known source dependencies where corroborating sources share an upstream origin

Measure every pipeline iteration against the benchmark.

Define matching and scoring rules before interpreting results, including:

- how predicted and gold Versions are paired
- how partial contributor/date/difference matches score
- macro versus micro aggregation
- how indeterminate gold items are excluded or reported
- how operational failures affect latency, cost, and coverage

Required metrics:

- version precision
- version recall
- duplicate rate
- incorrect merge rate
- fan-edit false-positive rate
- contributor accuracy
- evidence coverage
- difference accuracy
- relationship accuracy
- research latency
- research cost per song

Milestone 0 should optimize these metrics before frontend polish.

Before Milestone 1 begins, set numeric exit thresholds. Incorrect merge rate and fan-edit false-positive rate require explicit safety gates in addition to the full metric report.

Benchmark fixtures must be reproducible and must not depend on live providers or live LLM calls. Keep opt-in source-access and model integration tests separate.

---

# Safe-to-Defer Decisions

Do not decide prematurely:

- Redis vs another queue
- polling vs WebSockets/SSE
- exact cloud provider
- exact OpenAI model
- graph database
- search index
- sophisticated confidence calibration beyond the required High/Medium/Low contract
- detailed contributor taxonomy
- graph visualization library
- public research-trigger authentication, quotas, and abuse controls

Design modules so these can be introduced later without changing core domain meaning.

Milestone 0 deploys one worker. Multi-worker deployment is deferred, while atomic claiming and crash recovery remain required correctness behavior.

---

# Rejected / Deferred Alternatives

## Next.js-only backend

Rejected for MVP because long-running research jobs and data-pipeline logic fit poorly in the same runtime.

## Microservices

Rejected because they increase development/debugging complexity before scale requires them.

## Redis queue from day one

Deferred. PostgreSQL-backed jobs are sufficient until measured throughput/retry needs justify a dedicated queue.

## Neo4j

Deferred. PostgreSQL can represent VersionRelationship edges at MVP scale.

## Elasticsearch/OpenSearch

Deferred. PostgreSQL search is sufficient initially.

---

# Pre-Implementation Validation

Before committing to provider-specific schemas or full pipeline implementation, validate these assumptions on a small representative slice of the benchmark:

1. likely trackers, spreadsheets, forums, interviews, and metadata sources are legally and technically retrievable
2. permitted stored excerpts/locators are sufficient to audit extracted Claims
3. MusicBrainz identity coverage maps acceptably to artist-specific SongWorks
4. textual evidence and deterministic metadata can distinguish useful Versions and common fan edits without custom fingerprinting
5. schema-constrained extraction produces evidence-anchored Claims at acceptable accuracy, latency, and cost
6. a PostgreSQL job lease recovers safely from a worker crash and retry
7. PostgreSQL trigram search handles the benchmark's aliases, punctuation, Unicode, and ambiguous titles
8. external media can be classified consistently as official, authorized, other public, or unsuitable

Record validation results in the benchmark/evaluation artifacts. A failed assumption should change the smallest affected design; it does not automatically justify new infrastructure.

---

# Initial Build Order

1. define benchmark annotation rules, metric formulas, and fixture format
2. manually assemble an initial representative benchmark slice
3. validate likely source access, retention constraints, and MusicBrainz identity coverage
4. define the minimum domain schema for SourceRetrieval, Claim, VersionCandidate, Version, and ResolutionDecision
5. implement the evaluation runner against frozen fixtures
6. implement ResearchJob, one worker, atomic lease recovery, and idempotency
7. implement one thin end-to-end source adapter/fetch path selected by benchmark need
8. implement evidence-anchored Claim extraction
9. implement VersionCandidate resolution, deduplication, and rejection reasons
10. implement fan-edit filtering and evaluate the first vertical slice
11. add only the next source adapters demonstrated necessary by benchmark recall
12. implement difference extraction and evidence linkage
13. implement relationship reconciliation with the minimal relationship taxonomy
14. run the complete Milestone 0 benchmark and iterate
15. add the minimal backend read API and internal research trigger
16. add the minimal Next.js internal UI

Do not prioritize visual polish before the pipeline has a reproducible benchmark result. Do not begin Milestone 1 until its numeric exit thresholds and safety gates are met.
