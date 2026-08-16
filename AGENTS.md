# AGENTS.md

# Trackline — Agent Instructions

Keep changes simple, incremental, and aligned with `PRODUCT.md` and `TECHNICAL.md`.

## Read First

Before changing code, schemas, dependencies, infrastructure, provider integrations, prompts, evaluation behavior, or product behavior, read:

1. `PRODUCT.md`
2. `TECHNICAL.md`

`PRODUCT.md` defines product behavior and scope. `TECHNICAL.md` defines architecture and implementation constraints.

If the documents conflict, report the conflict and ask for a decision. Do not resolve a locked conflict merely by choosing the simpler implementation. Simplicity must not override product semantics, provenance, or domain identity.

---

## Current Priorities

The project is currently focused on **Milestone 0: pipeline validation**.

Prioritize:

- benchmark annotation and reproducible evaluation
- source discovery
- source-backed claim extraction
- version identification
- duplicate/version merging
- fan-edit filtering
- version-difference extraction
- lineage reconciliation
- benchmark/evaluation tooling

Do not call the pipeline “reliable” without reporting its benchmark results. Do not prioritize visual polish before the pipeline has a reproducible end-to-end benchmark result.

Milestone 0 remains internal/local. Do not add arbitrary public research triggering, authentication, quotas, or abuse-control infrastructure unless the user explicitly changes the milestone scope.

---

## Architecture Constraints

Use the agreed MVP architecture:

- Next.js + TypeScript frontend
- FastAPI + Python backend
- PostgreSQL
- exactly one deployed background research worker for Milestone 0
- Docker Compose for local development

Do not add infrastructure without a measured benchmark/operational need or explicit user approval. Record the observed need when proposing such a change.

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
- `SongWork` is an artist-specific creative lineage, not a universal composition.
- covers by unrelated artists use separate SongWorks.
- reference demos may join a SongWork only when evidence places them in that artist recording's development path.
- source observations and unverified/rejected candidates remain separate from canonical `Version`s.
- externally derived information should enter as source-backed `Claim`s.
- every externally derived displayed value must trace through a resolution decision to supporting `Claim`s and evidence.
- source provenance includes source identity, retrieval time, content hash or locator, evidence excerpt/location, and extraction method/run.
- contributors belong to specific `Version`s.
- version lineage may branch and may be uncertain.
- canonical relationships are Confirmed or Possible; unknown lineage is represented by no canonical edge.
- Trackline owns its own internal IDs.
- external APIs/providers should be isolated behind adapters.
- fan edits must not enter canonical lineage, but rejected candidates and reasons may be retained for audit and evaluation.
- do not force a lineage relationship when evidence is insufficient.
- playable media is optional and does not determine Version existence confidence.
- claims that a Version existed and claims about how it sounded require separate support.

---

## LLM Rules

LLMs are helpers, not sources of truth.

Use LLMs for:

- structured extraction from retrieved sources
- ambiguous entity/version matching
- optional reconciliation assistance after deterministic rules are evaluated
- user-facing summaries generated only from stored resolved data

Do not:

- ask an LLM to invent song history from memory
- persist unsupported LLM facts as truth
- let an LLM override source evidence

LLM extraction must use validated structured output and an exact source excerpt or locator for every Claim. Reject invalid or unsupported output; do not silently repair it into fact.

Store model, prompt/schema version, token usage, cost, and call status. Unit tests must use recorded responses rather than live or paid model calls.

---

## Implementation Style

- Prefer clear, boring code over clever abstractions.
- Keep modules small and responsibilities obvious.
- Add abstractions only when they solve a current problem.
- Avoid premature optimization.
- Avoid speculative infrastructure.
- Keep external-provider schemas out of core domain logic.
- Prefer deterministic rules before LLM-based decisions, but do not treat weak non-LLM signals such as similar duration or title as proof.
- Make research jobs and refreshes idempotent; retries must not duplicate domain entities or evidence.
- Respect provider terms, robots rules, rate limits, licensing, and content-storage restrictions.
- Never commit credentials or copyrighted audio.

Data-model changes require a migration and tests that preserve existing provenance and research history. Do not make destructive schema changes without explicit approval.

---

## Testing

Pipeline behavior changes must add or update deterministic tests and run against the existing relevant benchmark fixtures. Change gold benchmark annotations only for a source-backed correction or an intentional coverage addition, never merely to make a pipeline change pass. If a test is genuinely impossible, document the specific reason in the handoff.

Unit tests must not depend on live external providers. Keep live-provider and live-model checks separate and opt-in.

The most important quality checks are:

- correct version discovery
- duplicate merging
- fan-edit rejection
- contributor accuracy
- evidence coverage
- version-difference accuracy
- lineage relationship accuracy

Do not treat a change as successful only because it runs without errors.

Report the relevant metric delta for changes to extraction, matching, fan-edit filtering, difference recovery, confidence, or reconciliation. Keep held-out benchmark cases separate from prompt/rule tuning.

---

## Scope Discipline

The active scope is Milestone 0 unless the user explicitly changes it.

If a requested feature is outside Milestone 0:

1. check `PRODUCT.md`
2. check `TECHNICAL.md`
3. defer it unless the request explicitly authorizes the scope change or it is required to evaluate Milestone 0

Do not expand scope just because a feature is technically interesting.

---

## When Unsure

Choose the option that:

1. preserves data provenance
2. keeps domain identities correct
3. is easier to test
4. is easier to reverse
5. uses less infrastructure

These are decision criteria, not permission to contradict locked product or technical rules. When two criteria conflict materially, report the tradeoff instead of silently selecting one.

The goal right now is to prove the data pipeline works against a defined benchmark, not to build the final production system.
