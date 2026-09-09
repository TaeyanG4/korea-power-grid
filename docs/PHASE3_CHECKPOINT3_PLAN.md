# Phase 3 — Checkpoint 3 Plan: Extend to Recent Eight Years

Status: **COMPLETE — PASS WITH OBSERVATIONS**

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

Stop on unexplained missing ZIPs, size/SHA mismatch, CRC failure, or leftover
`.part` files. An official attachment explicitly published as `0Byte` is
accounted as `source_unavailable`, not fabricated into a raw file.

## Format and content QA

Historical files may contain additional physical-format drift. Perform a
lightweight magic/encoding/header scan before the full content parse. Add
parser support only from observed raw-file evidence; do not guess a format.

```powershell
python scripts/format_qa.py --start 2018-08 --end 2021-07
```

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

- all 108 extension source-months are accounted for by either a validated raw
  file or an explicitly evidenced `source_unavailable` status
- parser/schema audit covers every available extension file and accounts for
  unavailable source-months explicitly
- timestamp parse failures are 0 after normalization
- exact duplicate removal, if any, is documented
- remaining candidate-key duplicates are 0
- extension Parquet manifests are complete
- logical coverage is exactly `2018-08` through `2026-07`
- source-level missingness is summarized, not silently imputed
