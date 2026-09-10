# V1 Release / Kaggle Plan

Status: **PACKAGE QA PASS — READY FOR PRIVATE KAGGLE DRAFT UPLOAD**

Phase 3 completed the full observed KPX board history from `2015-08` through
`2026-07`. The measured normalized footprint is 2.661 GB, within the V1 target.

## Release principles

- publish normalized Parquet, not raw website attachments
- do not reprocess or copy validated Parquet merely to assemble the release
- build flat release filenames using hard links on the same local volume
- preserve all source/month lineage in a machine-readable release manifest
- keep source-unavailable months explicit rather than inventing empty data
- keep the `state_estimation 2016-06-03 17:20` ambiguity exception explicit
- describe timestamps as naive because the source files do not contain verified
  timezone metadata
- preserve KPX attribution and the three official data.go.kr URLs
- use Kaggle license category `other`; describe the official permission field
  `이용허락범위 제한 없음` in the release text

## Package layout

Target root: `data/release/v1`

Available normalized source-months are exposed as flat files:

```text
demand_YYYY_MM.parquet
dispatch_YYYY_MM.parquet
state_estimation_YYYY_MM.parquet
```

The package also contains:

- `dataset-metadata.json`
- `README.md`
- `DATA_DICTIONARY.md`
- `SOURCE_LICENSE.md`
- `missing_source_months.csv`
- `missingness_summary.csv`
- `normalization_exceptions.json`
- `release_manifest.json`

The expected data-file count is 388 Parquet files: 396 logical source-months
minus eight explicitly unavailable official source attachments.

## Kaggle target

- owner: `taeyangg4`
- proposed slug: `south-korea-power-grid-5-minute`
- proposed title: `South Korea Power Grid 5-Minute Data 2015-2026`
- initial upload visibility: **private**
- CLI upload mode: `--keep-tabular` so Parquet is not converted to CSV

Public visibility is not enabled until release QA and the package-documentation
items in `docs/LICENSE_REVIEW.md` are all complete.
