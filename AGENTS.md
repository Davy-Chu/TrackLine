# AGENTS.md

# Trackline — Agent Instructions

Keep changes simple, incremental, and aligned with `PRODUCT.md` and `TECHNICAL.md`.

## Read First

Before making meaningful changes, read:

1. `PRODUCT.md`
2. `TECHNICAL.md`

Treat those files as the source of truth for product scope and architecture.

If an implementation idea conflicts with them, do not silently change direction. Prefer the simpler design unless there is a clear technical reason not to.

---

## Current Priorities

The project is currently focused on **Milestone 0: pipeline validation**.

Prioritize:

- source discovery
- source-backed claim extraction
- version identification
- duplicate/version merging
- fan-edit filtering
- version-difference extraction
- lineage reconciliation
- benchmark/evaluation tooling

Do not prioritize visual polish before the research pipeline is reliable.

---

## Architecture Constraints

Use the agreed MVP architecture:

- Next.js + TypeScript frontend
- FastAPI + Python backend
- PostgreSQL
- one background research worker
- Docker Compose for local development

Do not add infrastructure unless it is clearly required.

Avoid introducing:

- microservices
- Redis
- Kafka
- Neo4j
- Elasticsearch/OpenSearch
- Kubernetes

These are intentionally deferred.

---

## Domain Rules

Preserve these boundaries:

- `SongWork` and `Version` are separate concepts.
- externally derived information should enter as source-backed `Claim`s.
- `Source` provenance must be preserved.
- contributors belong to specific `Version`s.
- version lineage may branch and may be uncertain.
- Trackline owns its own internal IDs.
- external APIs/providers should be isolated behind adapters.
- fan edits must not enter canonical lineage.
- do not force a lineage relationship when evidence is insufficient.

---

## LLM Rules

LLMs are helpers, not sources of truth.

Use LLMs for:

- structured extraction from retrieved sources
- ambiguous entity/version matching
- reconciliation assistance
- user-facing summaries generated from stored data

Do not:

- ask an LLM to invent song history from memory
- persist unsupported LLM facts as truth
- let an LLM override source evidence

Prefer structured outputs where possible.

---

## Implementation Style

- Prefer clear, boring code over clever abstractions.
- Keep modules small and responsibilities obvious.
- Add abstractions only when they solve a current problem.
- Avoid premature optimization.
- Avoid speculative infrastructure.
- Keep external-provider schemas out of core domain logic.
- Prefer deterministic rules before LLM-based decisions.

When changing data models or core domain behavior, consider migration/compatibility impact carefully.

---

## Testing

For pipeline-related changes, add or update tests where practical.

The most important quality checks are:

- correct version discovery
- duplicate merging
- fan-edit rejection
- contributor accuracy
- evidence coverage
- version-difference accuracy
- lineage relationship accuracy

Do not treat a change as successful only because it runs without errors.

---

## Scope Discipline

If a requested feature is outside the current MVP:

1. check `PRODUCT.md`
2. check `TECHNICAL.md`
3. prefer deferring it unless it directly helps Milestone 0

Do not expand scope just because a feature is technically interesting.

---

## When Unsure

Choose the option that:

1. preserves data provenance
2. keeps domain identities correct
3. is easier to test
4. is easier to reverse
5. uses less infrastructure

The goal right now is to prove the data pipeline works, not to build the final production system.
