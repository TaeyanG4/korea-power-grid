# Phase 1 Pilot Results — 2026-07

Status: **PASS WITH OBSERVATIONS**

Machine-readable audit: `data/audits/pilot_2026_07.json`.

## Measured results

| Source | ZIP bytes | Extracted bytes | Rows | Parquet ZSTD bytes |
|---|---:|---:|---:|---:|
| demand | 144,414 | 658,944 | 8,928 | 123,758 |
| dispatch | 19,821,316 | 146,162,747 | 4,679,698 | 5,256,132 |
| state_estimation | 25,560,291 | 195,049,183 | 5,371,818 | 17,391,879 |
| **Total** | **45,526,021** | **341,870,874** | **10,060,444** | **22,771,769** |

Parsing, QA and Parquet creation took about 15.5 seconds locally. Download time was not instrumented precisely enough to use as a benchmark.

## Physical format findings

- Demand: the ZIP member is named `.xlsx` but has OLE `.xls` magic bytes (`D0 CF 11 E0 A1 B1 1A E1`). `xlrd` parses it. Original columns: `TIME`, `LF05_1`.
- Dispatch: comma-delimited ASCII TXT. Original columns: `TIME`, `GEN_CODE`, `BASEPOINT`.
- State estimation: comma-delimited CP949 TXT. Original columns: `시간`, `발전기CODE`, `상태추정MW`. Midnight is date-only; other rows use Korean `오전`/`오후` timestamps.

## Coverage / QA

### Demand
- Grain: `timestamp`.
- 8,928/8,928 expected 5-minute timestamps, no duplicates or parse failures.
- Two values are exactly 0 MW: `2026-07-14 16:15` and `2026-07-14 16:20`. Retained unchanged and flagged for later forensic comparison.

### Dispatch
- Grain: `(timestamp, generator_id)`.
- 4,679,698 rows, 647 generator IDs.
- 8,928/8,928 timestamps, no duplicate candidate keys, no null/blank IDs.
- 111 negative values; retained unchanged pending source-semantic validation.

### State estimation
- Grain: `(timestamp, generator_id)`.
- 5,371,818 rows, 725 generator IDs.
- Timestamp parse failures after dedicated Korean AM/PM parser: 0.
- 8,927/8,928 expected timestamps.
- Single missing timestamp: **2026-07-12 07:50** (observed 07:45 -> 07:55 gap).
- No duplicate candidate keys and no null/blank IDs.
- 11,489 negative values; retained unchanged pending source-semantic validation.

## Cross-source generator IDs

The two generator-level sources do not expose a directly joinable identifier namespace in this pilot.

- Dispatch examples: `2`, `3`, `4`, ...
- State-estimation examples: `IJ1`, `IJ10`, `IJ100`, ...
- Direct overlap: 0

No prefix stripping or guessed mapping is applied. A mapping will be added only if an official source establishes it.

## Linear size projection

| Range | Raw ZIP | Parquet |
|---|---:|---:|
| 3 years / 36 months | 1.639 GB | 0.820 GB |
| 5 years / 60 months | 2.732 GB | 1.366 GB |
| 8 years / 96 months | 4.370 GB | 2.186 GB |
| 10 years / 120 months | 5.463 GB | 2.733 GB |
| Full board history / 132 months | **6.009 GB** | **3.006 GB** |

These are pilot-based linear projections, not final release measurements.

## Decision

**GO to Phase 2 and historical-backfill preparation.** Full-history size is currently compatible with the 2–4 GB release target and 20 GB raw-data limit. Historical collection must still proceed newest-to-oldest with 3-year and 5-year checkpoints to measure real schema drift and size before extending to the oldest period.
