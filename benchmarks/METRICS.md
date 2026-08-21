# Trackline Metric Contract v1

This document defines how one recorded pipeline prediction is compared with one benchmark
answer key. The formulas are deterministic and versioned. Numeric Milestone 0 exit thresholds
are intentionally not set here; they require a later product decision informed by the first
representative benchmark results.

The current implementation produces per-song scores from synthetic fixtures. Corpus
aggregation and the full evaluation runner remain later build-order work.

## Inputs

- **Gold fixture:** the manually reviewed `BenchmarkSong` answer key.
- **Prediction snapshot:** the immutable `SongPrediction` emitted by one recorded run.
- The two inputs must have the same `benchmark_song_id`.
- Draft gold fixtures are validation-only and cannot be scored.
- Gold `indeterminate_items` remain visible in diagnostics but are not ordinary positives or
  negatives.

## Version pairing

Pairing uses exact signals after Unicode NFKC normalization, case-folding, trimming, and
collapsing whitespace. It does not use fuzzy titles, similar durations, or model judgment.

Precedence:

1. exact provider-qualified external identity or exact filename
2. exact alias, only when it identifies one gold item
3. a known duplicate/same-audio candidate whose gold decision is `merged`, mapped to its gold
   merge target
4. otherwise unmatched

If strong signals from one predicted Version point to multiple distinct gold Versions, the
prediction is an incorrect merge. If an alias points to multiple gold Versions, it is ambiguous
and receives no true-positive match.

When several predicted Versions pair with the same gold Version, the representative used for
contributor scoring is chosen deterministically by signal strength and then prediction ID. The
additional predictions are duplicates.

## Classification formulas

For ordinary precision/recall metrics:

```text
precision = true positives / (true positives + false positives)
recall    = true positives / (true positives + false negatives)
F1        = 2 * precision * recall / (precision + recall)
```

A value is `null`, rather than zero, when its denominator is zero. Every report retains the raw
counts so a value can be audited.

## Version discovery

```text
version true positives  = unique gold Versions paired with at least one prediction
version false positives = predicted canonical Versions - true positives
version false negatives = gold canonical Versions - true positives
```

Extra predictions paired to an already represented gold Version are false positives as well as
duplicates.

## Duplicate rate

```text
duplicate rate = extra predicted canonical Versions paired to an already represented gold Version
                 / predicted canonical Versions
```

The rate is `null` when no canonical Version was predicted.

## Incorrect merge rate

A scorable merge decision is either:

- a predicted canonical Version whose strong signals point to multiple distinct gold Versions;
  or
- an explicit predicted candidate merge that can be paired with a gold candidate expectation.

An explicit merge is correct only when the gold candidate is expected to be merged and the
predicted target pairs with the expected gold target.

```text
incorrect merge rate = incorrect scorable merge decisions / scorable merge decisions
```

Unmatched or alias-ambiguous candidate merges are reported outside this rate because the gold
fixture does not provide a reliable comparison target.

## Fan-edit safety

A known fan edit is **encountered** when either a predicted canonical Version or a predicted
candidate pairs with its gold candidate expectation.

A fan edit is a false positive when it is emitted as a canonical Version or explicitly merged
into a canonical Version. Keeping it rejected or unverified does not enter canonical lineage.

```text
fan-edit false-positive rate = encountered fan edits promoted or merged / encountered fan edits
fan-edit encounter coverage  = encountered known fan edits / all known fan edits
```

Both numbers must be reported together. A pipeline does not demonstrate fan-edit safety merely
by failing to discover the benchmark's fan edits.

## Contributor accuracy

Contributors are compared only on paired representative Versions, using the exact tuple:

```text
(gold Version, normalized contributor name, contributor role)
```

A correct name with the wrong role is one false positive and one false negative; v1 gives no
partial credit. Contributor precision, recall, and F1 are all reported. Version recall remains
the separate measure of contributors that cannot be evaluated because their Version was missed.

## Evidence coverage

The prediction snapshot treats each of these as one externally derived assertion:

- Version existence
- Version contributor
- candidate decision
- Version difference
- canonical relationship

```text
evidence coverage = predicted assertions with at least one evidence reference
                    / predicted externally derived assertions
```

This checks attachment coverage, not source quality or whether the cited evidence truly supports
the assertion. Those require later source/Claim evaluation.

## Difference accuracy

A difference matches only when these fields match exactly after identity pairing and text
normalization:

```text
(from Version, to Version, category, detail)
```

A correct category with incorrect or unsupported detail receives no partial credit in v1; it
becomes one false positive and one false negative. Difference precision, recall, and F1 are
reported.

## Relationship accuracy

A relationship edge matches on:

```text
(subject/newer Version, relationship type, object/earlier Version)
```

Relationship precision, recall, and F1 ignore certainty. Confirmed/Possible correctness is then
reported separately for matched edges:

```text
relationship certainty accuracy = matched edges with correct certainty / matched edges
```

Unknown lineage has no gold edge. An invented edge is therefore a false positive.

## Operational failures, latency, and cost

- A failed prediction publishes no partial result collections.
- Its missing gold Versions, differences, and relationships remain false negatives.
- Version precision is `null` when it predicted no Versions; Version recall is zero when gold
  Versions exist.
- `operational_success`, `latency_ms`, `cost_usd`, and `source_count` are always reported.
- A completed `insufficient_evidence` result is distinct from an operational failure.

## Future corpus aggregation

The later evaluation runner must report both:

- **micro metrics:** sum raw counts across songs, then calculate the metric;
- **macro metrics:** calculate each song's metric, then average defined values.

Operationally failed songs remain in corpus coverage, latency, cost, and recall reporting. A
metric that is undefined for a song is excluded from that macro metric's denominator and the
number of defined songs must be reported.

Development and held-out splits must be aggregated and reported separately.

## Not scored in contract v1

The current gold fixture has no structured recording-date fields, so date accuracy and partial
date overlap are not scored. Adding date evaluation requires a versioned fixture-contract change
with explicit precision/range rules.

Version type, major/minor classification, and existence-confidence calibration are retained in
fixtures or predictions but do not yet have required Milestone 0 metrics. They must not be folded
silently into another score.
