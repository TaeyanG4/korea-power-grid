# South Korea Power Grid 5-Minute Data (2015-2026)

Normalized monthly power-grid operating data from the Korea Power Exchange
(KPX), covering the observed board history from **2015-08 through 2026-07**.

This package is a cleaned/normalized derivative prepared from official KPX
source attachments. **It is not an official KPX distribution channel and does
not imply KPX endorsement.**

## Contents

- demand forecast: `demand_YYYY_MM.parquet`
- generator economic dispatch: `dispatch_YYYY_MM.parquet`
- generator state estimation: `state_estimation_YYYY_MM.parquet`
- lineage and integrity metadata: `release_manifest.json`
- known unavailable source months: `missing_source_months.csv`
- source-level missingness summary: `missingness_summary.csv`
- normalization exception record: `normalization_exceptions.json`

Logical coverage is 396 source-month records
(132 months × 3 sources). Eight official source-month attachments are currently
unavailable and therefore have no fabricated Parquet placeholder.

## Important data notes

- timestamps are stored as **naive timestamps**; no timezone is asserted because
  the source files do not provide verified timezone metadata
- generator identifiers are retained in source-native form; no guessed mapping
  between dispatch and state-estimation identifier systems is applied
- missing timestamps are not silently imputed
- exact duplicate rows are removed only when candidate-key duplicates are exact
- one ambiguous source timestamp, `state_estimation 2016-06-03 17:20`, is
  excluded rather than arbitrarily choosing between conflicting duplicate rows;
  see `normalization_exceptions.json`

## Measured release size

- output rows: 1,008,249,180
- Parquet bytes: 2,661,216,619
- timestamp parse failures after normalization: 0
- remaining candidate-key duplicates: 0

## Source and permission

Provider: **Korea Power Exchange (한국전력거래소, KPX)**.

The three official data.go.kr records were re-checked at
`2026-09-10T10:26:19.878787+09:00` and each reported `무료` and
`이용허락범위 제한 없음`. Kaggle metadata therefore uses the `other` category
and this package states the official source condition rather than assigning a
different Creative Commons license.

See `SOURCE_LICENSE.md` and `release_manifest.json` for the official URLs and
verification metadata.
