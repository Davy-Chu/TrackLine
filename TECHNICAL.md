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

- SongWork as primary artist
- VersionContributor
- ExternalIdentity

## SongWork

The underlying musical work independent of a specific recording.

Relates to:

- Artist
- SongAlias
- Version
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

Possible types include:

- DERIVED_FROM
- REWORKED_INTO
- RELEASED_AS
- REFERENCE_FOR
- REUSES_VOCALS_FROM
- REUSES_INSTRUMENTAL_FROM
- POST_RELEASE_REVISION_OF

Relationships support:

- Confirmed
- Possible
- Unknown

Do not assume lineage is linear.

## VersionChange

Structured meaningful difference between Versions.

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

A retrieved piece of external evidence.

Conceptual fields:

- URL
- title
- source type
- publisher/uploader
- retrieval time
- external identifier if relevant

## Claim

A source-supported assertion about a domain entity.

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

## ClaimEvidence

Connects one Claim to one or more Sources.

## ExternalMedia

Optional external audio/video representation of a Version.

Separate from Source because a URL may be evidence, playable media, or both.

## ResearchJob

Represents one automated research attempt.

Initial statuses:

- pending
- discovering
- extracting
- resolving
- reconciling
- completed
- failed

Store operational metrics such as:

- start/end time
- source count
- LLM usage/cost
- failure reason

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
2. Claims/evidence are separate from resolved facts.
3. Contributors attach to individual Versions.
4. Version lineage supports branching and uncertainty.
5. Trackline owns stable internal IDs.
6. External providers are isolated behind adapters.
7. PostgreSQL is the system of record.

Do not simplify these boundaries for short-term convenience.

---

# External Interfaces

## Frontend -> Backend

Minimum MVP API:

### Search

`GET /search?q=...`

Returns resolved known works/candidates.

### Song

`GET /songs/{song_id}`

Returns song-level information.

### Lineage

`GET /songs/{song_id}/lineage`

Returns:

- versions
- relationships
- changes
- confidence
- sources/evidence references
- external media

### Version Detail

`GET /versions/{version_id}`

Returns full Version detail.

### Start Research

`POST /songs/{song_id}/research`

Creates a ResearchJob if one is not already active.

For unresolved title/artist queries, the backend may first resolve/create the SongWork before starting research.

### Research Status

`GET /research-jobs/{job_id}`

Frontend polls this endpoint.

No WebSockets are required initially.

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

Use safe job-claiming/locking so multiple workers cannot process the same job if worker count increases later.

Do not add Redis initially.

---

# Source Adapter Boundary

External providers must not leak their schemas into the rest of the application.

Use provider-specific adapters that return Trackline internal structures.

Important adapters may include:

## MusicBrainz

Use for:

- artist identity
- work/recording identity
- aliases
- releases
- official relationships

Treat as a canonical metadata foundation, not an unreleased lineage source.

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

The model must be instructed to extract only source-supported information.

## LLM Use 2 — Candidate Version Matching

Use when deterministic rules cannot decide whether two references describe the same Version.

Possible output:

- likely same
- likely different
- uncertain

Deterministic evidence wins whenever available.

## LLM Use 3 — Reconciliation Assistance

Use to classify disagreements or relationships between claims.

The LLM may assist but must not silently choose truth.

## LLM Use 4 — User-Facing Summary

After lineage is resolved, generate a concise history from stored structured data.

## LLM Non-Goals

Never:

- ask the model to generate the song history from memory
- write unsupported model facts directly into Version state
- let the model be the sole confidence system
- let model output override source evidence

Wrap model calls behind a small `LLMClient` abstraction so exact model/provider choice remains replaceable.

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

Keep the disagreement visible.

## Strong Authority Mismatch

Prefer stronger first-party evidence for displayed state, but preserve weaker Claims internally.

## LLM vs Source

The Source always wins.

---

# Version Resolution Priorities

Pipeline priority order:

1. identify genuine distinct versions
2. merge duplicate references
3. reject obvious fan edits
4. attach evidence to important claims
5. recover meaningful differences
6. infer lineage relationships only where supported

Do not optimize relationship inference before version identity is reliable.

Useful deterministic matching signals include:

- exact filename
- exact external ID
- same duration
- same known contributors
- same source metadata
- strong alias match

Do not treat any single weak signal as proof.

---

# Search and Persistence

Use PostgreSQL for:

- canonical entities
- aliases
- fuzzy title lookup
- research jobs
- source/claim persistence

PostgreSQL full-text/trigram search should be sufficient for MVP scale.

Do not add Elasticsearch unless search quality/performance becomes a measured problem.

---

# Evaluation

Maintain a manually verified benchmark dataset.

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

Measure every pipeline iteration against the benchmark.

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
- research cost

Milestone 0 should optimize these metrics before frontend polish.

---

# Safe-to-Defer Decisions

Do not decide prematurely:

- Redis vs another queue
- one worker vs many workers
- polling vs WebSockets/SSE
- exact cloud provider
- exact OpenAI model
- graph database
- search index
- sophisticated confidence algorithm
- detailed contributor taxonomy
- graph visualization library

Design modules so these can be introduced later without changing core domain meaning.

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

# Initial Build Order

1. domain entities + persistence
2. benchmark dataset format
3. ResearchJob + worker
4. MusicBrainz / canonical identity adapter
5. generic web search/fetch interfaces
6. one specialist tracker adapter
7. source-backed claim extraction
8. candidate Version resolution/deduplication
9. fan-edit filtering
10. difference extraction
11. relationship reconciliation
12. evaluation tooling
13. minimal backend API
14. minimal Next.js UI
15. run Milestone 0 benchmark and iterate

Do not prioritize visual polish before the research pipeline is measurably useful.
