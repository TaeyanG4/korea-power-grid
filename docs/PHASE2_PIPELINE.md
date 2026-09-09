# Phase 2 — Repository and Collector Pipeline

Status: **PASS**

Phase 2 establishes the reproducible collection layer. It does not perform the historical backfill itself.

## Implemented structure

- `src/korea_power_grid/sources.py`: official V1 source definitions and month parsing.
- `src/korea_power_grid/collector.py`: board discovery, attachment resolution, resilient download and manifests.
- `scripts/collect.py`: command-line entry point.
- `scripts/pilot_audit.py`: Phase 1 forensic audit and pilot Parquet measurement.
- `tests/`: source/month parsing regression tests.
- `data/manifests/`: small reproducibility metadata retained outside raw data.
- `data/raw/`, `data/working/`, `data/processed/`, `data/release/`: ignored as large/local artifacts.

## Collector guarantees

The collector currently provides:

- newest-to-oldest month ordering
- official KPX board discovery instead of 132 hard-coded attachment URLs
- source-month manifests
- existing valid download skip/resume behavior
- HTTP timeouts
- bounded retries with backoff
- `.part` temporary files
- `fsync` before atomic rename
- ZIP integrity validation before accepting a new download
- SHA-256 checksum recording
- failed source-month recording
- checkpoint updates after each attempted source-month
- missing-post report

Manifest fields include:

- `source`
- `month`
- `source_url`
- `attachment_url`
- `downloaded_at`
- `file_size`
- `sha256`
- `status`
- `retry_count`

## Historical board-title drift handled

KPX did not use one title convention for the entire history. The indexer now recognizes:

1. `YYYY년 M월`
2. `YYYY년도 M월`
3. compact `YYYYMM` embedded in a title
4. early month-only titles such as `8월분 실적`, using the row's publication date to determine the year

This is required for the oldest state-estimation posts, whose article titles omit the year.

## Validation results

### Unit tests

`python -m pytest -q`

Result: **2 passed**.

### Existing-pilot resume check

Command:

```powershell
python scripts/collect.py --start=2026-07 --end=2026-07
```

Result: all three existing pilot ZIPs were detected and reported as `skipped_existing`; they were not re-downloaded.

### Recent 3-year planning check

Command:

```powershell
python scripts/collect.py --start=2023-08 --end=2026-07 --dry-run
```

Result: **108 / 108 planned**, no missing posts.

### Full observed-history planning check

Command:

```powershell
python scripts/collect.py --start=2015-08 --end=2026-07 --dry-run
```

Result: **396 / 396 planned**.

The generated source index contains exactly:

- demand: 132 months, 2015-08 through 2026-07
- dispatch: 132 months, 2015-08 through 2026-07
- state estimation: 132 months, 2015-08 through 2026-07
- missing posts: 0

## Phase 2 exit decision

**GO to Phase 3 Checkpoint 1: recent 3-year historical backfill.**

Because that download may take longer than 30–40 minutes depending on KPX throughput and retries, it should be run by the user from the local terminal. After completion, the resulting manifests and raw files must be audited before extending to five years.

