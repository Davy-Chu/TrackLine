# Trackline Benchmark Contract v1

The benchmark is the manually reviewed answer key used to evaluate Trackline's research
pipeline. It is not the production database schema.

Version 1 currently validates answer-key fixtures only. Prediction matching and metric scoring
will be added separately after this contract is stable.

## Layout

```text
benchmarks/
  v1/
    development/  # visible cases used while rules and prompts are developed
    held-out/      # cases kept separate from rule and prompt tuning
```

Each JSON file describes one artist-specific `SongWork`. The included
`synthetic-simple.json` fixture is fictional and exists only to test the validator.

## Annotation rules

- Use `schema_version: "1.0"`.
- Give every benchmark object a stable lowercase ID. IDs may contain numbers, periods,
  underscores, and hyphens.
- Treat a `SongWork` as an artist-specific creative lineage, not a universal composition.
- Put only legitimate High- or Medium-confidence Versions in `versions`.
- Put fan edits, duplicate references, same-audio uploads, and unverified material in
  `candidate_expectations` with the expected decision and reason.
- A title, filename, upload, platform, leak, or release-status change alone does not create a
  Version.
- Attach contributors to their specific Version.
- Represent a relationship from the newer/derived Version (`subject_version_id`) to the
  earlier/source Version (`object_version_id`). Do not create an edge for unknown lineage.
- Put disputed items that do not have a reliable gold answer in `indeterminate_items`; they
  will be reported separately rather than scored as ordinary errors.
- Do not change a gold annotation merely to make a pipeline prediction pass.

## Evidence rules

Every externally derived annotation must reference evidence retained under a source. In
particular, keep these forms of support separate:

- evidence that a Version existed
- evidence about how the Version sounded
- evidence for a contributor
- evidence for a difference between Versions
- evidence for a lineage relationship

A source records its identity, retrieval time, content hash, retrieval method/run, and short
evidence excerpts with precise locators and extraction method/run. Do not store entire source
pages or copyrighted audio in benchmark fixtures.

## Validate fixtures

From the repository root on Windows:

```powershell
.\.venv\Scripts\python -m research.evaluation.cli benchmarks\v1\development
```

The command exits with status `0` when every discovered JSON fixture passes and status `1`
when a fixture or path fails validation.

## Adding a real fixture later

1. Start in `development`, not `held-out`.
2. Record the SongWork identity and source retrieval metadata.
3. Add short, exact evidence excerpts and locators.
4. Add canonical Versions only when legitimacy and distinct audio iteration are supported.
5. Record encountered fan edits, duplicates, and unverified candidates separately.
6. Validate the file.
7. Perform a second manual review before marking the annotation `reviewed`.
