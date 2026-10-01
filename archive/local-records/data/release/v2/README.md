# South Korea Power Grid 5-Minute Data (2015-2026)

Normalized Korea Power Exchange (KPX) five-minute operating data covering the
observed monthly board history from **2015-08 through 2026-07**.

## Start here

V2 exposes the full normalized dataset in **two equivalent data files** instead
of hundreds of monthly files:

- `south_korea_power_grid_5min.parquet` — recommended for Python, Polars, DuckDB, Spark, and analytics
- `south_korea_power_grid_5min.csv` — compatibility export with the same 1,008,249,180 rows

Parquet is strongly recommended for normal analysis because it is only
1.99 GB compared with 50.14 GB for
the plain CSV export.

## Unified row schema

| Column | Meaning |
|---|---|
| `timestamp` | Five-minute source timestamp; timezone-naive because the source files do not provide verified timezone metadata |
| `source` | `demand`, `dispatch`, or `state_estimation` |
| `generator_id` | Source-native KPX generator CODE; null/blank for demand rows |
| `value_mw` | MW value whose meaning is determined by `source` |

`value_mw` mapping:

- `demand` → five-minute system demand forecast
- `dispatch` → generator economic-dispatch BASEPOINT / target
- `state_estimation` → state-estimated generator output

No guessed generator-ID crosswalk is applied between dispatch and state
estimation.

## Data quality

- logical coverage: 132 months × 3 sources = 396 source-months
- normalized rows: **1,008,249,180**
- source-unavailable attachments: **8** (see `missing_source_months.csv`)
- missing timestamps are not silently imputed
- exact duplicates were removed only under the documented canonical-key rule
- one ambiguous historical state-estimation timestamp (`2016-06-03 17:20`) was
  excluded rather than arbitrarily choosing between conflicting snapshots; see
  `normalization_exceptions.json`

## Source and reuse

Provider: **Korea Power Exchange (한국전력거래소, KPX)**.

This is a cleaned/normalized derivative dataset, not an official KPX
distribution channel, and it does not imply KPX endorsement. The official
data.go.kr records were re-checked before release and state
`이용허락범위 제한 없음`. Kaggle uses license category `other` so this package
does not invent a Creative Commons license not stated by the official source.

See `SOURCE_LICENSE.md`, `DATA_DICTIONARY.md`, and `release_manifest.json` for
full provenance and integrity metadata.
