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
For a supported artist, a missing song triggers an automated research job.

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
Important claims expose their supporting sources and confidence.

### Open media
A version may link to an external audio/video source. Media is optional and never hosted by Trackline.

---

## Definition of a Version

A Version is a legitimate artist/studio iteration of a SongWork containing an audible musical change.

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

Version relationships may be:

- Confirmed
- Possible
- Unknown

Possible relationships may be shown with a dotted edge. Unknown relationships should not be invented.

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

### Milestone 0 UI

Only build:

- search box
- research status
- simple timeline/branch view
- version details
- evidence links
- confidence labels

No elaborate graph UI is required.

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

---

## Milestone 1 — Searchable MVP

Proceed after Milestone 0 is sufficiently reliable.

Target:

- approximately 10 active/popular artists
- approximately 100+ researched songs
- automatic research for missing supported songs

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

If the system cannot construct a sufficiently reliable history:

> We could not reconstruct a reliable version history for this song yet.

Do not manufacture a lineage.

## Persistence

Once researched, a song is stored and reused.

For the MVP, data remains static until manually refreshed.

Songs with no discovered alternate versions are still persisted and shown as:

> No alternate versions found.

---

# Data Principles

Trackline treats song history as a multi-source evidence problem.

Core rule:

> Sources do not overwrite one another.

A source produces Claims. Claims are reconciled into displayed knowledge.

LLMs are used to read and structure evidence, not to act as the source of truth.

If sources disagree:

- compatible claims may be merged
- genuine contradictions remain visible
- stronger first-party evidence may outweigh weak secondary evidence
- the source always wins over an LLM inference

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
- Missing supported songs trigger automated research.
- Fan edits are excluded from canonical lineage.
- Low-confidence versions are separated as unverified.
- Possible lineage edges may be shown as uncertain.
- Songs with no alternate versions are persisted.
- Generated descriptive version labels are allowed when no authentic label exists.
- External audio/video links are optional.
- No user accounts in MVP.
- No copyrighted audio hosting.
- Milestone 0 focuses on pipeline reliability, not visual polish.
