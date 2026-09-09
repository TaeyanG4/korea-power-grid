# Phase 3 — Checkpoint 3 Results: Recent Eight Years

Status: **PASS WITH OBSERVATIONS**

Checkpoint 3 extends the validated logical dataset through `2018-08` without
regenerating the previously validated five-year outputs.

## Coverage

- logical period: `2018-08` through `2026-07`
- months: 96
- sources: 3
- logical source-month records: 288 / 288
- processed roots:
  - `data/processed/checkpoint_8y_extension`
  - `data/processed/checkpoint_5y_extension`
  - `data/processed/checkpoint_3y`

## Checkpoint 3 extension

The new incremental segment is `2018-08` through `2021-07`:

- 36 months
- 108 source-month records accounted
- 107 validated raw files
- 1 explicitly evidenced `source_unavailable` record
- raw integrity problem count: 0
- leftover `.part` files: 0
- timestamp parse failures after normalization: 0
- remaining candidate-key duplicates after processing: 0

The unavailable record is `demand 2019-11`. The official KPX article reports
the attachment as `0Byte`, and the current download endpoint returns only four
CR/LF bytes. No placeholder raw file or imputed demand values are created.

## Historical delivery drift handled

Checkpoint 3 added evidence-based support for several older delivery variants:

- some KPX attachments are delivered directly as CP949 TXT rather than ZIP;
  the exact source payload size/SHA-256 is preserved in the download manifest
  and the unchanged bytes are stored in a deterministic single-member local ZIP
  wrapper for downstream consistency
- `state_estimation 2019-08` contains two outer ZIP members; source-aware header
  detection selects the actual state-estimation TXT and records the unrelated
  nested reserve-data ZIP as ignored provenance metadata
- one source-month may be represented explicitly as `source_unavailable` when
  official evidence shows the attachment itself is unavailable; this is not
  treated as a successful raw download

## Processing results for the 36-month extension

- input rows: 260,200,547
- exact duplicate rows removed: 206,567
- output rows: 259,993,980
- Parquet size: 753,756,483 bytes

All exact duplicate removal in this extension is from `state_estimation`.
Processing verifies that no candidate-key duplicates remain afterward.

## Measured eight-year footprint

Across all three validated roots:

- raw stored bytes: 4,164,505,327
- normalized Parquet bytes: 1,965,735,204
- input rows before deduplication: 772,668,865
- output rows after exact deduplication: 768,139,730
- exact duplicate rows removed: 4,529,135

The measured Parquet footprint remains below the project's previously stated
2–4 GB V1 release target, so continuing to the 10-year checkpoint is reasonable.

## Missingness observations

Missing timestamps remain source-level observations and are not silently
imputed.

- `demand`: 8,645 missing timestamps across 3 months over the eight-year
  window; the largest case is the fully unavailable `2019-11` month (8,640)
- `dispatch`: 6,330 missing timestamps across 3 months; the largest case is
  `2022-07`, which ends at `2022-07-10 00:45` and is missing 6,326 timestamps
- `state_estimation`: 5,864 missing timestamps across 95 months; the largest
  case remains `2026-05` with 1,228 missing timestamps and a 1,221-timestamp
  contiguous gap

## Decision

**GO to Phase 3 / Checkpoint 4.**

Checkpoint 4 extends only the missing older segment `2016-08` through
`2018-07` and must not regenerate any existing eight-year outputs.
