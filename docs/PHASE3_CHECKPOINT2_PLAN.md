# Phase 3 — Checkpoint 2 Plan: Extend to Recent 5 Years

Status: **IN PROGRESS — 72/72 RAW DOWNLOADS COMPLETE; CONTENT QA RUNNING**

Checkpoint 1 already covers 2023-08 through 2026-07. Checkpoint 2 extends the
logical dataset to a five-year window without regenerating the completed
three-year outputs.

## Incremental scope

Only the missing older segment is required:

- extension start: 2021-08
- extension end: 2023-07
- additional months: 24
- sources: 3
- additional source-month records: 72

The existing source index contains all 72 required source-month posts. The
incremental download has completed successfully for all 72 records and raw ZIP
integrity QA passed with zero problems and zero leftover `.part` files.

## Long-running collection

Run this from the user terminal rather than an interactive ChatGPT tool call:

```powershell
python scripts/collect.py --start 2021-08 --end 2023-07
```

This intentionally excludes 2023-08 through 2026-07 so the completed raw
checkpoint is not revisited.

## Raw checkpoint QA

After the download completes, audit only the new extension range:

```powershell
python scripts/checkpoint_qa.py --start 2021-08 --end 2023-07
```

Do not proceed to normalization if the raw QA reports missing ZIPs, size/SHA
mismatches, CRC failures or leftover `.part` files.

## Content QA

The extension should receive the same parser/schema/timestamp audit used for
Checkpoint 1:

```powershell
python scripts/content_qa.py --start 2021-08 --end 2023-07
```

This can be a substantial scan because it parses all 72 new raw source-month
files. If it is likely to exceed 30–40 minutes, run it from the user terminal.

Any timestamp gaps should be recorded as observations first. Do not fill them
or classify them as parser bugs unless raw-file evidence supports that.

## Incremental processing

Process only the older 24 months into a separate root:

```powershell
python scripts/process_checkpoint.py `
  --start 2021-08 `
  --end 2023-07 `
  --output-root data/processed/checkpoint_5y_extension
```

This avoids reprocessing the already validated
`data/processed/checkpoint_3y` tree.

The logical five-year dataset will therefore initially consist of two validated
roots:

- `data/processed/checkpoint_5y_extension`: 2021-08 through 2023-07
- `data/processed/checkpoint_3y`: 2023-08 through 2026-07

A later release/checkpoint step can validate the union and choose whether to
keep this two-root layout or materialize a release-specific layout. No copy or
reprocessing of the existing 3-year Parquet data is required merely to perform
Checkpoint 2.

## Checkpoint 2 exit criteria

Checkpoint 2 is complete only when all of the following hold:

- 72 / 72 extension downloads are present and raw QA passes
- parser/schema audit covers all 72 extension records
- timestamp parse failure count is 0 after normalization
- any exact duplicate removal is documented
- remaining candidate-key duplicates are 0
- extension Parquet manifests are complete
- the combined logical window is exactly 2021-08 through 2026-07
- source-level missingness is summarized rather than silently imputed
