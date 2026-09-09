# Phase 3 — Checkpoint 3 Plan: Extend to Recent Eight Years

Status: **READY**

Checkpoint 2 validated the logical five-year window `2021-08` through
`2026-07`. Checkpoint 3 extends it to eight years without regenerating any
validated five-year outputs.

## Incremental scope

Only the missing older segment is required:

- extension start: `2018-08`
- extension end: `2021-07`
- additional months: 36
- sources: 3
- additional source-month records: 108

The current source index contains all 108 required posts.

## Long-running collection

```powershell
python scripts/collect.py --start 2018-08 --end 2021-07
```

Run this independently from the completed five-year ranges. Existing raw ZIPs
and processed Parquet outputs must not be regenerated.

## Raw QA

```powershell
python scripts/checkpoint_qa.py --start 2018-08 --end 2021-07
```

Stop on missing ZIPs, size/SHA mismatch, CRC failure, or leftover `.part`
files.

## Format and content QA

Historical files may contain additional physical-format drift. Perform a
lightweight magic/encoding/header scan before the full content parse. Add
parser support only from observed raw-file evidence; do not guess a format.

Then run:

```powershell
python scripts/content_qa.py --start 2018-08 --end 2021-07
```

Timestamp gaps are source-level observations unless raw-file evidence shows a
parser problem. Do not impute missing timestamps during this checkpoint.

## Incremental processing

Process only the new 36-month segment into its own root:

```powershell
python scripts/process_checkpoint.py `
  --start 2018-08 `
  --end 2021-07 `
  --output-root data/processed/checkpoint_8y_extension
```

The logical eight-year dataset will then consist of:

- `data/processed/checkpoint_8y_extension`: `2018-08` through `2021-07`
- `data/processed/checkpoint_5y_extension`: `2021-08` through `2023-07`
- `data/processed/checkpoint_3y`: `2023-08` through `2026-07`

## Exit criteria

- 108 / 108 extension downloads pass raw integrity QA
- parser/schema audit covers all 108 extension source-months
- timestamp parse failures are 0 after normalization
- exact duplicate removal, if any, is documented
- remaining candidate-key duplicates are 0
- extension Parquet manifests are complete
- logical coverage is exactly `2018-08` through `2026-07`
- source-level missingness is summarized, not silently imputed
