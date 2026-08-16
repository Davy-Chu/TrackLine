# PRODUCT.md

# Trackline

## Product Definition

Trackline is a searchable song-version lineage platform.

It reconstructs the publicly supportable history of a musical work across:

- demos
- reference tracks
- alternate vocals/features
- alternate production or arrangements
- alternate mixes
- album-era reworks
- official releases
- post-release audio revisions

For each known version, Trackline should explain:

- what the version is
- approximately when it existed
- who contributed to it
- how it differs from other versions
- how it relates to earlier/later versions
- what sources support the claims
- where it can be heard externally, when an appropriate link exists

Core promise:

> Search a song and understand its known legitimate versions and how it changed over time.

Trackline does not claim to know every private studio version ever created. It reconstructs the best publicly supportable lineage available.

---

## Target Users

Primary users:

1. Music fans who want a clear version history without manually searching trackers, Reddit, YouTube, wikis, and interviews.
2. Knowledgeable fans / archivists who care about provenance, version differences, filenames, dates, and disputed claims.

The UI should be simple enough for group 1 while exposing enough evidence for group 2.

---

## Core Use Cases

### Search an existing song
User searches a title or alias and views the stored lineage.

### Research a missing song

During Milestone 0, missing-song research is triggered only through internal developer tooling.

For Milestone 1, a missing song for a supported artist may trigger an automated research job after the artist/work has been resolved. Ambiguous searches must be resolved before a job starts.

### Compare versions
A user can see what changed between versions, including:

- contributor added/removed
- vocals changed
- lyrics changed
- production changed
- arrangement changed
- instrumental changed
- mix/master changed

### Inspect evidence
Every externally derived displayed claim exposes its supporting sources and confidence or relationship certainty.

### Open media
A version may link to an external audio/video source. Media is optional and never hosted by Trackline.

---

## Definition of a Version

A Version is a legitimate artist/studio iteration of a SongWork containing an audible musical change.

The change may be established by reliable documentary evidence even when no playable audio is public. Version existence confidence and media availability are separate. If audio is unavailable, Trackline must limit claims about what changed to what the sources explicitly support.

Examples:

- demo
- reference track
- alternate feature
- alternate vocals
- alternate instrumental
- alternate arrangement
- alternate mix
- official release
- post-release audio revision

Trackline supports:

- **major versions**: meaningful creative iterations
- **minor revisions**: genuine smaller audio revisions

The model should support this distinction, but sophisticated automatic major/minor classification is not required for the first validation milestone.

Excluded from canonical lineage:

- fan edits
- fan remasters
- mashups
- unofficial stem compilations
- fan “finished” versions

Ambiguous material should default to unverified rather than canonical.

A change in title, filename, leak status, upload, platform, or release status does not by itself create a new Version. If the underlying audio is the same, represent the new information as an alias, source, media link, or release event instead.

## Definition of a SongWork

A SongWork is an artist-specific creative lineage, not a universal composition shared across all performers.

For example, Trackline models the Kanye West creative lineage for “Hurricane,” rather than an abstract composition containing every cover or unrelated interpretation.

Rules:

- covers or independent interpretations by unrelated artists are separate SongWorks
- songwriter or reference demos may belong to the target artist's SongWork when evidence shows they are part of that recording's development path
- transferred songs remain separate SongWorks in Milestone 0
- cross-SongWork transfer or adaptation relationships may be added later without introducing a universal composition identity
- a SongWork may have multiple ordered artist credits, but one artist/context owns the lineage for Milestone 0 evaluation

---

## Confidence Rules

Public confidence levels:

- High
- Medium
- Low

Display policy:

- High/Medium versions appear in the main lineage.
- Low-confidence versions appear under **Unverified Versions**.
- Unsupported material is not shown as fact.

Confidence scopes are separate:

- **version existence confidence**: whether a distinct legitimate Version existed
- **claim confidence**: whether a particular displayed assertion is sufficiently supported
- **relationship certainty**: whether a lineage edge is Confirmed or Possible

Playable media availability is not a confidence level. A Version may be High or Medium confidence without a public audio link.

Canonical Version relationships may be:

- Confirmed
- Possible

Possible relationships may be shown with a dotted edge. Unknown relationships are represented by the absence of a canonical edge, not by inventing an “Unknown” edge.

---

# MVP Strategy

## Milestone 0 — Pipeline Validation

The first milestone is not a polished product.

Goal:

> Prove that automated song-lineage reconstruction works reliably enough to be useful.

### Initial validation artists

Use five artists with different source environments:

- Kanye West
- Lana Del Rey
- Frank Ocean
- Playboi Carti
- Travis Scott

### Benchmark corpus

Use roughly 20–30 manually researched songs across those artists.

Include examples with:

- many versions
- few versions
- renamed songs
- demos that became releases
- alternate-feature versions
- common fan edits
- disputed lineage
- strong first-party evidence
- weaker archival evidence

Benchmark items may be marked indeterminate where the public evidence does not support a reliable gold answer. Indeterminate items should remain visible for analysis but should not be scored as ordinary false positives or false negatives.

### Milestone 0 UI

Only build:

- search box
- research status
- simple timeline/branch view
- version details
- evidence links
- confidence labels

No elaborate graph UI is required.

Milestone 0 remains internal/local. Arbitrary public users cannot trigger research jobs. Public research triggering, quotas, abuse protection, and user-facing job controls are Milestone 1 decisions.

### Evaluation metrics

Track at minimum:

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

Do not proceed to a broader product solely because the pipeline “looks good.” Use the benchmark results.

Before Milestone 1 begins, define the exact metric formulas and numeric exit thresholds. Incorrect merges and fan-edit false positives require explicit safety gates rather than being hidden inside one aggregate score.

---

## Milestone 1 — Searchable MVP

Proceed only after Milestone 0 meets its defined metric thresholds and the incorrect-merge and fan-edit safety gates.

Target:

- approximately 10 active/popular artists
- approximately 100+ researched songs
- a product decision, informed by Milestone 0 cost, latency, and failure data, on whether and how users may trigger research for missing supported songs

Artist selection should consider:

- popularity
- active/recent music output
- availability of publicly documentable version history

Do not choose artists purely by popularity if the lineage data is too sparse.

---

# MVP Features

## Search

Support:

- canonical title
- alternate title
- common leak title
- artist + title
- reasonable spelling/title variation

Ambiguous searches should ask the user to choose a resolved work before research starts.

## Song Page

Show:

- canonical title
- primary artist
- aliases
- known eras/projects
- concise lineage summary
- known versions
- last researched date

## Version Lineage

Show a simple chronological timeline with branch support.

The data model must support branching even if the UI is simple.

## Version Detail

A version may contain:

- display label
- aliases
- original filename
- approximate recording date/range
- date precision
- leak/discovery date
- era/project
- version type
- major/minor classification
- contributors
- meaningful differences
- relationships to other versions
- confidence
- sources
- external media link

## What Changed

“What changed?” is a first-class feature.

Differences should be structured enough to represent changes between two versions.

## Evidence

Important displayed claims should have source-level provenance.

Do not rely only on a page-level bibliography.

## External Media

Prefer:

1. official artist upload
2. official streaming source
3. authorized/public platform upload
4. other appropriate public source
5. no link

A missing media link must not block the version from appearing.

## Research Failure State

If the system cannot construct a history that meets the canonical evidence rules:

> We could not reconstruct a reliable version history for this song yet.

Do not manufacture a lineage.

Distinguish this from two other outcomes:

- a completed research run that found a supported lineage
- a completed research run that reliably found no alternate versions

Operational failures, insufficient evidence, and valid no-alternate results must not share the same state.

## Persistence

Once researched, a song is stored and reused.

For the MVP, data remains static until manually refreshed.

A manual refresh creates a new research run. It must preserve earlier source Claims and research history rather than destructively replacing them.

Songs with no discovered alternate versions are still persisted and shown as:

> No alternate versions found.

---

# Data Principles

Trackline treats song history as a multi-source evidence problem.

Core rule:

> Sources do not overwrite one another.

A source produces Claims. Claims are reconciled into displayed knowledge.

Every externally derived displayed fact must remain traceable to its supporting Claims and Sources. Genuine contradictions should be attached to the affected fact, not hidden in a page-level bibliography.

LLMs are used to read and structure evidence, not to act as the source of truth.

If sources disagree:

- compatible claims may be merged
- genuine contradictions remain visible
- stronger direct or first-party evidence may outweigh weak secondary evidence, depending on the claim being evaluated
- an LLM output cannot establish a fact without source-backed Claims

Multiple sources count as corroboration only when they are operationally independent. Several pages or trackers copying the same upstream assertion are not independent confirmation.

---

# Explicit Non-Goals

Not part of the MVP:

- user accounts
- profiles
- favorites
- follows
- comments
- crowdsourced editing
- community voting
- direct audio uploads
- copyrighted leak hosting
- playlists
- social feeds
- personalized recommendations
- continuous tracker/leak monitoring
- automatic scheduled refresh
- custom audio-identification ML
- sophisticated audio fingerprinting
- elaborate interactive graph UI
- perfect support for arbitrary artists

Infrastructure explicitly deferred unless justified by measured need:

- Redis
- Neo4j
- Elasticsearch/OpenSearch
- Kafka
- Kubernetes
- microservices

---

# Product Decisions Considered Locked

- SongWork and Version are separate concepts.
- SongWork represents an artist-specific creative lineage, not a universal composition.
- Covers by unrelated artists are separate SongWorks.
- Reference demos may belong to the target SongWork when evidence establishes a development path.
- A canonical Version may be established through reliable documentary evidence without playable public audio.
- Version existence confidence and media availability are separate.
- Milestone 0 research triggering is internal only.
- Public automatic research for missing supported songs is deferred to Milestone 1.
- Fan edits are excluded from canonical lineage.
- Low-confidence versions are separated as unverified.
- Possible lineage edges may be shown as uncertain.
- Unknown lineage is represented by the absence of a canonical edge.
- Songs with no alternate versions are persisted.
- Generated descriptive version labels are allowed when no authentic label exists.
- External audio/video links are optional.
- No user accounts in MVP.
- No copyrighted audio hosting.
- Milestone 0 focuses on pipeline reliability, not visual polish.
