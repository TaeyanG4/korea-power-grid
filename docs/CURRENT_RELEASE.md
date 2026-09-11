# Current Release Handoff

This note records the public, secret-free release state after the September 2026
CSV-compatibility and notebook refresh.

## Repository

- repository: `TaeyanG4/korea-power-grid`
- branch: `main`
- release-content commit recorded in the published manifest: `c8d4fc9f64c5dbe2c8db8705ff932f459de3cecc`
- validation: `18 passed` with project pytest; changed release/QA scripts pass Ruff and `git diff --check`

## Kaggle dataset

- dataset: `taeyangg4/south-korea-power-grid-5-minute`
- current live version: **5**
- status: **ready**
- dataset version id: `19571150`
- databundle version id: `20686877`
- live Usability: **1.0**
- live files: **5**

Primary release files:

- `south_korea_power_grid_5min.parquet` — 1,992,834,865 bytes; full 2015-08 through 2026-07 history; 1,008,249,180 rows
- `south_korea_power_grid_5min_2026_07.csv` — 502,736,368 bytes; July 2026 compatibility slice; 10,060,444 rows

July 2026 CSV source rows:

- `demand`: 8,928
- `dispatch`: 4,679,698
- `state_estimation`: 5,371,818

The CSV is deliberately a bounded compatibility slice. Do **not** regress to an
equivalent 50+ GB full-history CSV beside the Parquet unless a future user-value case
clearly justifies that duplication.

## Kaggle notebook

- notebook: `taeyangg4/south-korea-power-grid-v2-daily-operations-study`
- pushed kernel version: **3**
- final worker status: **COMPLETE**
- local execution against the current release package completed without notebook errors

The notebook uses predicate-filtered Parquet reads for the full-history analysis and
uses the July 2026 CSV only as a small interoperability preview.

## Data Explorer metadata

- file descriptions present: 4 / 5
- exact target file descriptions: 3 / 5
- column descriptions present/exact: 15 / 19
- the missing four column descriptions belong to `south_korea_power_grid_5min_2026_07.csv`
- the CSV file description is empty; the manifest file description still reflects the prior V3 wording
- dataset-level metadata, provenance, cover, Unicode/Korean text, public access, and Usability 1.0 are verified

The ordinary Kaggle metadata update path does not persist those Data Explorer fields
on the existing processed version. A protected SDK-style Data Explorer smoke write
returned HTTP 401 `UNAUTHENTICATED`, so repeating that request unchanged is not useful.

## Next action

Prioritize adoption diagnosis and external reuse. If an already-authenticated Kaggle
MCP or explicitly authorized same-origin browser path becomes available later, use it
only to fill the four July-CSV column descriptions and correct the two non-exact file
descriptions; do not create another data version solely for that metadata gap.
