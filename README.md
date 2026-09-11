<p align="center">
  <img src="docs/assets/dataset-cover-image.png" alt="South Korea power-grid operations dataset cover" width="560">
</p>

# South Korea Power Grid — 5-Minute KPX Operations Dataset

**English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

This repository is the reproducible collection, normalization, quality-assurance, and publishing pipeline behind the **South Korea Power Grid 5-Minute Data** dataset on Kaggle.

It turns monthly public files from the **Korea Power Exchange (KPX / 한국전력거래소)** into one analysis-ready long table covering three operational signals: **5-minute demand forecasts, generator economic-dispatch BASEPOINT targets, and generator state-estimated output**.

**Dataset:** https://www.kaggle.com/datasets/taeyangg4/south-korea-power-grid-5-minute

## Dataset at a glance

| Item | Current Kaggle release (V4) |
|---|---|
| Observed KPX board range | **2015-08 → 2026-07** |
| Resolution | **5 minutes** |
| Normalized rows | **1,008,249,180** |
| Signals | `demand`, `dispatch`, `state_estimation` |
| Primary file | `south_korea_power_grid_5min.parquet` — **1.99 GB** |
| Compatibility file | `south_korea_power_grid_5min.csv` — **50.14 GB** |
| Provider | Korea Power Exchange (KPX) |

The current Kaggle release exposes **one Parquet and one equivalent full-history CSV**. Use Parquet for normal analysis; the 50.14 GB CSV is intentionally provided for compatibility with tools and workflows that require CSV.

## What the three signals mean

| `source` | Meaning of `value_mw` | `generator_id` |
|---|---|---|
| `demand` | 5-minute system **demand forecast** in MW | blank / null |
| `dispatch` | Generator **economic-dispatch BASEPOINT / target** in MW | source-native KPX generator CODE |
| `state_estimation` | **State-estimated generator output** in MW | source-native KPX generator CODE |

These are related operating signals, but they are **not interchangeable measurements**. In particular, the project does not invent a generator-ID crosswalk between dispatch and state-estimation sources.

## Unified schema

Both main data files use the same four columns:

| Column | Description |
|---|---|
| `timestamp` | Five-minute source timestamp. Stored without an asserted timezone because the source files do not provide verified timezone metadata. |
| `source` | `demand`, `dispatch`, or `state_estimation`. |
| `generator_id` | Source-native KPX generator CODE for generator-level sources; null/blank for demand. |
| `value_mw` | MW value whose semantics are determined by `source`. |

## Quick start

The full dataset has more than one billion rows, so filter the Parquet file **before** converting data to pandas.

```python
from datetime import datetime
import pyarrow.dataset as ds

grid = ds.dataset("south_korea_power_grid_5min.parquet", format="parquet")

week = grid.to_table(
    columns=["timestamp", "value_mw"],
    filter=(
        (ds.field("source") == "demand")
        & (ds.field("timestamp") >= datetime(2026, 7, 1))
        & (ds.field("timestamp") < datetime(2026, 7, 8))
    ),
)

df = week.to_pandas()
print(df.head())
```

A public Kaggle notebook linked to the dataset demonstrates memory-conscious slicing, ramp analysis, aggregate operating signals, generator concentration, and coverage checks.

## Data-quality policy

The pipeline favors explicit provenance over silent repair:

- **8 official source-month attachments are unavailable** and are listed instead of being fabricated.
- Missing 5-minute timestamps remain missing; the release does not silently impute them.
- Exact duplicates are removed only under documented canonical-key rules.
- One ambiguous state-estimation timestamp, `2016-06-03 17:20`, contained conflicting full-generator snapshots and is excluded rather than arbitrarily choosing a version.
- Timestamps remain timezone-naive because a verified source timezone is not asserted by the files.

See the Kaggle package files `missing_source_months.csv`, `missingness_summary.csv`, `normalization_exceptions.json`, and `release_manifest.json` for machine-readable evidence.

## Repository vs. Kaggle dataset

| GitHub repository | Kaggle dataset |
|---|---|
| Source discovery and downloading | Published analysis-ready data |
| Historical format handling | One unified Parquet + one CSV |
| Normalization code | Data dictionary and provenance files |
| QA, manifests, checksums, release gates | Public notebook and dataset card |
| Reproducible publishing tooling | End-user download / analysis surface |

Large raw, working, processed, and release data are intentionally excluded from Git. Small manifests and audit outputs are retained so the build can be inspected and reproduced.

## Collecting from KPX

The collector discovers monthly KPX board posts and resolves the attachment from each article; it does not hard-code the complete historical attachment list.

```powershell
# Inspect what would be collected
python scripts/collect.py --start 2023-08 --end 2026-07 --dry-run

# Download and record provenance
python scripts/collect.py --start 2023-08 --end 2026-07
```

## Documentation

- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — official KPX/data.go.kr sources and measured historical format drift
- [`docs/LICENSE_REVIEW.md`](docs/LICENSE_REVIEW.md) — redistribution and source-permission review
- [`docs/KAGGLE_PUBLISHING.md`](docs/KAGGLE_PUBLISHING.md) — cover geometry, Data Card refresh, and Usability metadata notes
- [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) — Phase 0–3 and V1 build/release history
- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) — V2 four-column schema and source semantics

The old phase-by-phase material is preserved for reproducibility, but it is no longer the front page of the project.

## Source, attribution, and reuse

Original provider: **Korea Power Exchange (한국전력거래소, KPX)**.

This project publishes a cleaned/normalized derivative and is **not an official KPX distribution channel** and does not imply KPX endorsement. The official data.go.kr records were re-checked before release and reported `이용허락범위 제한 없음`. Kaggle therefore uses the `other` license category instead of assigning a Creative Commons license that the official source does not state.

For source URLs, verification dates, and release checksums, see the provenance documents above and the Kaggle release manifest.
