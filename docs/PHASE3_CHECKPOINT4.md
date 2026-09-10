# Phase 3 — Checkpoint 4 Results: Recent Ten Years

Status: **PASS WITH OBSERVATIONS**

Checkpoint 4 extends the validated logical dataset through `2016-08` without
regenerating any prior processed roots.

## Coverage

- logical period: `2016-08` through `2026-07`
- months: 120
- sources: 3
- logical source-month records: 360 / 360
- timestamp parse failures: 0
- remaining candidate-key duplicates: 0
- logical source-unavailable records: 1 (`demand 2019-11`, inherited from
  Checkpoint 3)

## Checkpoint 4 extension

The new `2016-08` through `2018-07` segment contains:

- 24 months
- 72 / 72 successful raw downloads
- raw integrity problem count: 0
- leftover `.part` files: 0
- source-unavailable records: 0
- timestamp parse failures: 0
- outside-month timestamps: 0

One additional historical schema variant was measured at `dispatch 2018-05`:
the source header includes generator name and LFC min/max fields in addition to
the V1 time/CODE/BASEPOINT fields. The parser projects only the established V1
fields while retaining the full source header and ignored columns in physical
metadata.

## Processing results for the 24-month extension

- input rows: 170,669,906
- exact duplicate rows removed: 48,073
- output rows: 170,621,833
- Parquet size: 499,628,735 bytes

The duplicate removals occur in `state_estimation`; the processing invariant
requires candidate-key duplicate extras to equal exact duplicate extras before
removal, and no candidate-key duplicates remain afterward.

## Measured ten-year footprint

Across all four validated processed roots:

- raw stored bytes: 5,014,291,957
- normalized Parquet bytes: 2,465,363,939
- input rows before exact deduplication: 943,338,771
- output rows after exact deduplication: 938,761,563
- exact duplicate rows removed: 4,577,208

The measured normalized footprint remains inside the project's 2–4 GB V1
release-size target. The final 12-month historical extension is therefore
reasonable without changing the partition strategy.

## Missingness observations over the ten-year window

- `demand`: 8,671 missing timestamps across 11 months; largest is the fully
  unavailable `2019-11` month with 8,640 timestamps
- `dispatch`: 6,348 missing timestamps across 5 months; largest is the partial
  `2022-07` month with 6,326 missing timestamps
- `state_estimation`: 5,968 missing timestamps across 114 months; largest is
  `2026-05` with 1,228 missing timestamps

These remain source-level observations. No missing timestamp is silently
imputed.

## Decision

**GO to Phase 3 / Checkpoint 5.**

The final extension is `2015-08` through `2016-07` (12 months × 3 sources = 36
source-months). `2015-08` is already known from official source text to be a
partial month for at least demand and state estimation and must remain explicit
missingness rather than being promoted to full coverage.
