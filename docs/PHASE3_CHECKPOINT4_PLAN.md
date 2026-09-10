# Phase 3 — Checkpoint 4 Plan: Extend to Recent Ten Years

Status: **COMPLETE — PASS WITH OBSERVATIONS**

Checkpoint 3 validated the logical eight-year window `2018-08` through
`2026-07`. Checkpoint 4 extends it to ten years using only the missing older
segment.

## Incremental scope

- extension start: `2016-08`
- extension end: `2018-07`
- additional months: 24
- sources: 3
- additional source-month records: 72

The current source index contains all 72 required posts.

## Collection

Run only the incremental range:

```powershell
python scripts/collect.py --start 2016-08 --end 2018-07
```

Existing raw files and all three validated processed roots must not be
regenerated.

## QA sequence

After collection:

```powershell
python scripts/checkpoint_qa.py --start 2016-08 --end 2018-07
python scripts/format_qa.py --start 2016-08 --end 2018-07
python scripts/content_qa.py --start 2016-08 --end 2018-07
```

Use the same rules established by Checkpoint 3:

- direct-file source delivery may be wrapped locally only when exact source
  payload provenance is retained in the manifest
- multi-member archives require source-aware primary-member evidence
- an officially unavailable attachment is recorded as `source_unavailable`,
  not replaced with fabricated data
- source-level timestamp gaps are summarized and not silently imputed

## Incremental processing

Process only the 24-month extension into a new root:

```powershell
python scripts/process_checkpoint.py `
  --start 2016-08 `
  --end 2018-07 `
  --output-root data/processed/checkpoint_10y_extension
```

The logical ten-year dataset will then consist of four validated roots:

- `data/processed/checkpoint_10y_extension`: `2016-08` through `2018-07`
- `data/processed/checkpoint_8y_extension`: `2018-08` through `2021-07`
- `data/processed/checkpoint_5y_extension`: `2021-08` through `2023-07`
- `data/processed/checkpoint_3y`: `2023-08` through `2026-07`

## Exit criteria

- all 72 extension source-months are explicitly accounted
- raw QA has no unexplained integrity problems or leftover `.part` files
- format QA accounts for every available file and any unavailable source-month
- content QA has zero timestamp parse failures
- exact duplicate removal is documented
- remaining candidate-key duplicates are zero
- extension processed manifests account for all 72 source-months
- logical source-month coverage is exactly 120 months × 3 sources = 360 records
- logical period is exactly `2016-08` through `2026-07`
- source-level missingness is summarized without imputation
