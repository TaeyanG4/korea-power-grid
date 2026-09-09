# Phase 3 — Checkpoint 2 Results: Recent Five Years

Status: **PASS WITH OBSERVATIONS**

Validated logical window: `2021-08` through `2026-07` (60 months).

Checkpoint 2 extended the completed three-year checkpoint without regenerating
the existing `2023-08` through `2026-07` Parquet outputs.

## Coverage

- sources: `demand`, `dispatch`, `state_estimation`
- months per source: 60
- logical source-month records: 180 / 180
- extension downloaded and processed in this checkpoint: 72 / 72
- extension period: `2021-08` through `2023-07`

The validated logical dataset consists of two roots:

- `data/processed/checkpoint_5y_extension`: `2021-08` through `2023-07`
- `data/processed/checkpoint_3y`: `2023-08` through `2026-07`

No existing three-year Parquet data was regenerated.

## Raw extension QA

- records: 72 / 72
- raw ZIP bytes: 1,352,153,230
- missing or corrupt ZIPs: 0
- size/SHA mismatches: 0
- ZIP CRC failures: 0
- leftover `.part` files: 0

## Content QA

All 72 extension source-months parsed successfully.

- timestamp parse failures: 0
- timestamps outside the requested source month: 0
- candidate-key duplicate rows before processing: 0

Historical physical-format drift was observed and is now supported:

- `demand`: 24 CP949 comma-delimited files with two preamble rows
- `dispatch`: 15 CP949 comma-delimited files with five preamble rows, plus
  nine real OOXML `.xlsx` workbooks
- `state_estimation`: 24 CP949 comma-delimited files, with either zero or
  three preamble rows

The dispatch Excel months are `2021-08`, `2021-12`, and `2022-01` through
`2022-07`. Some workbooks split a month across multiple worksheets and omit
headers on continuation worksheets. The parser now handles this layout.

## Extension processing

The 72 extension records produced:

- input rows: 171,704,063
- exact duplicate rows removed: 0
- output rows: 171,704,063
- Parquet bytes: 483,798,981
- timestamp parse failures: 0
- remaining candidate-key duplicate rows: 0

Per-source extension Parquet sizes:

- demand: 2,934,180 bytes
- dispatch: 110,208,539 bytes
- state estimation: 370,656,262 bytes

## Five-year measured size

Combining the completed three-year checkpoint and the two-year extension:

- raw ZIP bytes: 2,854,707,078 (about 2.855 GB decimal)
- Parquet bytes: 1,211,978,721 (about 1.212 GB decimal)

A simple full-history size projection using the measured five-year average is
about 6.28 GB raw and 2.67 GB Parquet for 132 months. This is only a planning
projection; older checkpoints must still be measured because physical formats
can drift.

## Source-level missingness observations

Missing timestamps are recorded as source coverage observations. They are not
silently filled.

### Demand

- months with missing timestamps: 1 / 60
- total missing timestamps: 2
- largest monthly missing count: 2 (`2026-06`)

### Dispatch

- months with missing timestamps: 3 / 60
- total missing timestamps: 6,330
- largest monthly missing count: 6,326 (`2022-07`)
- longest gap: `2022-07-10 00:50` through `2022-07-31 23:55`

The `2022-07` dispatch source workbook itself ends at `2022-07-10 00:45`.
This is treated as a source-level partial month, not a parser failure.

### State estimation

- months with missing timestamps: 60 / 60
- total missing timestamps: 4,475
- largest monthly missing count: 1,228 (`2026-05`)
- longest gap in that month: `2026-05-10 08:35` through
  `2026-05-14 14:15` (1,221 timestamps)

## Exit decision

Checkpoint 2 hard checks all pass. The measured five-year raw and Parquet
sizes remain comfortably inside the project size policy, and the observed
historical dispatch Excel variation is now reproducibly parsed.

**Decision: GO to the eight-year checkpoint.**

The next incremental range is `2018-08` through `2021-07`, 36 months per
source, or 108 additional source-month records. Existing five-year outputs
must not be regenerated.
