# Kaggle publishing notes

This page records the presentation and usability details that are easy to lose between dataset releases.

## Cover image geometry

Kaggle CLI 2.2.x submits fixed crop rectangles when it uploads a dataset cover:

- header image: `560 x 280`, starting at the image's top-left corner
- square thumbnail: `280 x 280`, starting at `x=140, y=0`

For this project, `scripts/build_kaggle_cover.py` therefore renders the canonical cover at exactly `560 x 280`. Keeping the important network/curve content inside the central `x=140..420` region also produces a useful square thumbnail.

Do not replace the cover with a larger landscape canvas unless the upload/crop behavior is re-verified first; otherwise Kaggle can show only the empty top-left portion of the artwork.

## Current release shape

The current live Kaggle dataset version is **5**. The repository keeps the `v4`
release-tooling directory/name for the packaging work unit that produced this shape.

V4 keeps one canonical full-history Parquet and adds a bounded UTF-8 CSV compatibility slice:

- `south_korea_power_grid_5min.parquet` — recommended analytics file
- `south_korea_power_grid_5min_2026_07.csv` — all three sources for July 2026, 10,060,444 rows

Do not publish an equivalent 50+ GB full-history CSV alongside the Parquet. Keep Parquet as the default in notebooks and examples; the July 2026 slice is the CSV-only interoperability path.

The Kaggle dataset metadata API updates the dataset card successfully, but on the
current processed version it does not persist the new CSV's Data Explorer file/column
descriptions. The authenticated SDK-style Data Explorer write path returned HTTP 401;
do not retry it unchanged. This gap is tracked separately from core release QA because
the live dataset remains `ready` and its Kaggle Usability rating is 1.0.

## Usability score

Kaggle's Data Explorer descriptions are platform-side metadata. The release metadata contains the target file and column descriptions, but every new dataset version must be read back after processing because CLI submission alone does not prove those descriptions were persisted.

To complete that final criterion, enter these descriptions for **both** `south_korea_power_grid_5min.parquet` and `south_korea_power_grid_5min_2026_07.csv` (4 columns x 2 files = 8 descriptions):

| Column | Description |
|---|---|
| `timestamp` | Five-minute source timestamp from KPX. Parquet stores `timestamp[ns]`; CSV uses `YYYY-MM-DD HH:MM:SS` text. No timezone is asserted. |
| `source` | Measurement family: `demand`, `dispatch`, or `state_estimation`. This field determines the semantic meaning of `value_mw`. |
| `generator_id` | Source-native KPX generator CODE for dispatch/state estimation; blank/null for system-level demand rows. |
| `value_mw` | MW value. `demand` = demand forecast; `dispatch` = economic-dispatch BASEPOINT; `state_estimation` = state-estimated generator output. |

After those eight main-table Data Explorer descriptions are saved, re-run the live usability check:

```powershell
python scripts/kaggle_v2_usability_qa.py
```

The score is platform-controlled, so the repository checks the live Kaggle value rather than assuming that a metadata write has been accepted.

## Refreshing the public card

Build the cover first:

```powershell
python scripts/build_kaggle_cover.py
```

For a metadata-only refresh, run the Kaggle metadata update from the current release directory and immediately read the live metadata back. Do not create a dataset version merely to retry metadata persistence.

```powershell
cd data/release/v4
python -c "from kaggle.api.kaggle_api_extended import KaggleApi; api=KaggleApi(); api.authenticate(); api.dataset_metadata_update('taeyangg4/south-korea-power-grid-5-minute', '.')"
```

Finally, verify the public dataset and linked notebook:

```powershell
python scripts/kaggle_v4_remote_qa.py
python scripts/kaggle_v2_usability_qa.py
```
