# V1 Release Package Results

Status: **PACKAGE QA PASS**

The V1 package has been assembled at `data/release/v1` from the five validated
Phase 3 processed roots without reprocessing the historical data. Available
monthly Parquet files are exposed as hard links on the same local volume, so
package assembly does not duplicate the 2.66 GB normalized dataset on disk.

## Package contents

- logical source-month records: **396**
- available Parquet files: **388**
- explicit source-unavailable records: **8**
- auxiliary metadata/documentation files: **8**
- normalized output rows: **1,008,249,180**
- Parquet bytes: **2,661,216,619**
- release-manifest build commit: `064957ae9b2a3a54a98962ea4149cc7a7802079f`

Available Parquet file counts:

- demand: **128**
- dispatch: **130**
- state estimation: **130**

## Release QA

`data/audits/release_v1_qa.json` records the final package QA.

Status: **PASS**

The full QA re-hashed all 388 Parquet files and verified:

- exact package filename set
- per-file SHA-256 against `release_manifest.json`
- per-file Parquet row count
- canonical Parquet schema by source
- aggregate row count and byte size
- 8 source-unavailable records
- missingness summary and normalization-exception metadata
- Kaggle dataset id/title/subtitle/license metadata constraints used by the
  project
- non-endorsement statement
- official permission wording in package documentation
- no unexpected files in the release root

No QA problems remain.

## License / attribution gate

The three official data.go.kr records were re-checked at
`2026-09-10T09:28:09+09:00`. The machine-readable audit is
`data/audits/release_license_check_2026-09-10.json` and its status is `PASS`.

The package includes the official KPX board URLs, official data.go.kr URLs,
the source permission wording, transformation notes, unavailable-month notes,
and the documented `state_estimation 2016-06-03 17:20` ambiguity policy.

Kaggle metadata uses license category `other`; the package does not assert a
Creative Commons license that the official source metadata does not state.

## Kaggle draft target

- owner: `taeyangg4`
- dataset id: `taeyangg4/south-korea-power-grid-5-minute`
- title: `South Korea Power Grid 5-Minute Data 2015-2026`
- initial visibility: **private**
- upload option: `--keep-tabular` to preserve Parquet

The next action is a private Kaggle dataset draft upload. Public visibility is
not required for validating the upload and can be decided after the private
draft is confirmed complete.
