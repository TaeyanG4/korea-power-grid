# Phase 3 — Checkpoint 1: Recent 3-Year Backfill

Status: **PASS WITH OBSERVATIONS**

Period: **2023-08 through 2026-07 (36 months)**

Checkpoint 1 is complete. The recent three-year window has been downloaded,
validated, normalized and written to Parquet. The remaining timestamp gaps are
treated as source-level missingness observations rather than parser failures.

## Completed scope

- 3 sources: `demand`, `dispatch`, `state_estimation`
- 36 months per source
- 108 / 108 raw downloads present
- raw ZIP integrity, size and SHA-256 checks passed
- 108 / 108 processed source-month manifests present
- timestamp parse failures after normalization: 0
- remaining candidate-key duplicates after exact deduplication: 0

Processed totals:

- input rows: 340,764,255
- exact duplicate rows removed: 4,322,568
- output rows: 336,441,687
- Parquet size: 728,179,740 bytes

All exact duplicate removals occurred in `state_estimation`.

## Parser coverage observed in the checkpoint

The parser now handles the physical variants encountered in the 36-month
checkpoint, including:

- CP949 comma-delimited text
- ASCII comma-delimited text
- UTF-8 BOM comma-delimited text
- optional preamble rows
- source-aware 3-column header detection
- the 2026-07 demand file whose ZIP member name says `.xlsx` but whose payload is
  Excel 97-2003 OLE format

The parser regression suite currently passes all 6 tests.

## Source-level timestamp missingness

The normalized timestamps parse cleanly, but the source data is not perfectly
complete at the 5-minute grain.

Across the checkpoint:

- `demand`: 2 missing timestamps across 1 month
- `dispatch`: 4 missing timestamps across 2 months
- `state_estimation`: 3,310 missing timestamps; all 36 months contain at least
  one missing timestamp

The most important observed gap is `state_estimation` 2026-05:

- missing timestamps: 1,228
- longest contiguous missing run: 1,221 timestamps
- run start: 2026-05-10 08:35
- run end: 2026-05-14 14:15

For 2026-06, two missing timestamps are shared by all three sources:

- 2026-06-11 18:55
- 2026-06-11 19:35

Because the same 2026-06 timestamps are absent from independent source files,
and because parser/normalization invariants pass, these gaps should be carried
forward as source-level missingness instead of filled or attributed to parser
failure without additional evidence.

## Reproducible checkpoint summary

Run the lightweight checkpoint aggregator after the existing outputs are in
place:

```powershell
python scripts/phase3_checkpoint1_qa.py
```

It reads the existing download QA, content QA and processed manifests, plus only
the timestamp columns needed to verify the two key gap observations. It writes:

`data/audits/phase3_checkpoint1_summary.json`

It does not rerun the full preprocessing pipeline.

## Checkpoint decision

**GO to Phase 3 / Checkpoint 2: extend the recent window from 3 years to 5 years.**

The incremental extension is exactly:

- 2021-08 through 2023-07
- 24 additional months
- 72 additional source-month downloads (24 × 3)

Do not re-download or reprocess 2023-08 through 2026-07 merely to begin the next
checkpoint. The next long-running collection should target only the extension
window.

Suggested collection command for the user terminal:

```powershell
python scripts/collect.py --start 2021-08 --end 2023-07
```

Because the download may exceed the interactive 30–40 minute budget, it should
be run by the user. After that completes, audit the 72 new raw files before
processing them. The older 24 months should be processed into a separate
incremental root so the completed 3-year Parquet checkpoint is not regenerated.
