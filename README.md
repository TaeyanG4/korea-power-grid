# South Korea Power Grid Operations — 5-Minute Data

Generator Dispatch, State Estimation and Demand Forecasts from official Korea Power Exchange (KPX) sources.

## Project status

- Phase 0 — source/license discovery: complete
- Phase 1 — 2026-07 one-month pilot: complete (`PASS WITH OBSERVATIONS`)
- Phase 2 — repository/pipeline structure: complete
- Phase 3 — historical backfill: Checkpoint 1 (recent 3 years) complete (`PASS WITH OBSERVATIONS`); Checkpoint 2 ready

See:

- `docs/DATA_SOURCES.md`
- `docs/LICENSE_REVIEW.md`
- `docs/PHASE1_PILOT_RESULTS.md`
- `docs/PHASE2_PIPELINE.md`
- `docs/PHASE3_CHECKPOINT1.md`
- `docs/PHASE3_CHECKPOINT2_PLAN.md`
- `data/audits/pilot_2026_07.json`
- `data/audits/phase3_checkpoint1_summary.json`

## Pilot headline numbers

For 2026-07, the three source ZIPs total 45,526,021 bytes. The normalized ZSTD Parquet pilot totals 22,771,769 bytes across 10,060,444 rows.

The pilot-only linear projection for all 132 monthly board entries is about 3.006 GB of Parquet. This is not a final release size estimate; historical checkpoints will replace the linear projection with measured values.

## Collection

The collector discovers monthly posts from the official KPX boards and then resolves the attachment from each article. It does not hard-code 132 historical attachment URLs.

Dry-run example:

```powershell
python scripts/collect.py --start 2023-08 --end 2026-07 --dry-run
```

Download example:

```powershell
python scripts/collect.py --start 2023-08 --end 2026-07
```

Raw downloads are intentionally ignored by Git. Small manifests and audit outputs are retained as reproducibility metadata.
