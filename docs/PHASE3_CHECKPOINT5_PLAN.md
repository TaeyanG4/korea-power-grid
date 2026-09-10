# Phase 3 — Checkpoint 5 Plan: Full Observed Board History

Status: **READY**

Checkpoint 4 validates the recent ten-year window `2016-08` through `2026-07`.
Checkpoint 5 adds the remaining observed board history without regenerating any
prior outputs.

## Incremental scope

- extension start: `2015-08`
- extension end: `2016-07`
- additional months: 12
- sources: 3
- additional source-month records: 36
- final logical window: `2015-08` through `2026-07`
- final logical source-month records: 132 months × 3 = 396

The earliest month has known partial-coverage caveats from official KPX source
text. Missing timestamps in `2015-08` must be measured and reported, not
imputed.

## Collection and QA

Run only the final incremental range:

```powershell
python scripts/collect.py --start 2015-08 --end 2016-07
python scripts/checkpoint_qa.py --start 2015-08 --end 2016-07
python scripts/format_qa.py --start 2015-08 --end 2016-07
python scripts/content_qa.py --start 2015-08 --end 2016-07
```

The same historical rules continue to apply:

- preserve exact source payload provenance for direct-file attachments
- select data members from multi-member archives using source-aware evidence
- record officially unavailable attachments as `source_unavailable`
- stop on unexplained physical-format drift rather than guessing
- report partial months and timestamp gaps without silent imputation

## Incremental processing

```powershell
python scripts/process_checkpoint.py `
  --start 2015-08 `
  --end 2016-07 `
  --output-root data/processed/checkpoint_full_extension
```

The full logical dataset will consist of five validated roots:

- `data/processed/checkpoint_full_extension`: `2015-08` through `2016-07`
- `data/processed/checkpoint_10y_extension`: `2016-08` through `2018-07`
- `data/processed/checkpoint_8y_extension`: `2018-08` through `2021-07`
- `data/processed/checkpoint_5y_extension`: `2021-08` through `2023-07`
- `data/processed/checkpoint_3y`: `2023-08` through `2026-07`

## Exit criteria

- all 36 extension source-months explicitly accounted
- raw QA has no unexplained integrity problems or leftover `.part` files
- format QA accounts for all 36 source-months
- content QA has zero timestamp parse failures and zero outside-month timestamps
- exact duplicate removal is documented
- remaining candidate-key duplicates are zero
- full processed manifests account for 396 source-months exactly
- per-source logical months equal all 132 months from `2015-08` through
  `2026-07`
- partial coverage, unavailable source months, and other source-level
  missingness are summarized explicitly
