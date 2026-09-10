# Kaggle publishing notes

This page records the presentation and usability details that are easy to lose between dataset releases.

## Cover image geometry

Kaggle CLI 2.2.x submits fixed crop rectangles when it uploads a dataset cover:

- header image: `560 x 280`, starting at the image's top-left corner
- square thumbnail: `280 x 280`, starting at `x=140, y=0`

For this project, `scripts/build_kaggle_cover.py` therefore renders the canonical cover at exactly `560 x 280`. Keeping the important network/curve content inside the central `x=140..420` region also produces a useful square thumbnail.

Do not replace the cover with a larger landscape canvas unless the upload/crop behavior is re-verified first; otherwise Kaggle can show only the empty top-left portion of the artwork.

## Usability score

Kaggle's current usability breakdown reports every dataset-level criterion as complete except **column descriptions**. The V2 release already includes descriptions in `dataset-metadata.json`, but the public Kaggle API/CLI metadata-update path does not currently propagate those descriptions into the existing Data Explorer table metadata.

To complete that final criterion, enter these descriptions for **both** `south_korea_power_grid_5min.parquet` and `south_korea_power_grid_5min.csv` (4 columns x 2 files = 8 descriptions):

| Column | Description |
|---|---|
| `timestamp` | Five-minute source timestamp from KPX. Parquet stores `timestamp[ns]`; CSV uses `YYYY-MM-DD HH:MM:SS` text. No timezone is asserted. |
| `source` | Measurement family: `demand`, `dispatch`, or `state_estimation`. This field determines the semantic meaning of `value_mw`. |
| `generator_id` | Source-native KPX generator CODE for dispatch/state estimation; blank/null for system-level demand rows. |
| `value_mw` | MW value. `demand` = demand forecast; `dispatch` = economic-dispatch BASEPOINT; `state_estimation` = state-estimated generator output. |

After those eight Data Explorer descriptions are saved, re-run:

```powershell
python scripts/kaggle_v2_usability_qa.py
```

The score is platform-controlled, so the repository checks the live Kaggle value rather than assuming that a metadata write has been accepted.

## Refreshing the public card

Build the cover first:

```powershell
python scripts/build_kaggle_cover.py
```

Then update the existing dataset metadata from inside the V2 release directory so the Kaggle CLI does not create a malformed temporary upload-state path for the cover image:

```powershell
cd data/release/v2
python -c "from kaggle.api.kaggle_api_extended import KaggleApi; api=KaggleApi(); api.authenticate(); api.dataset_metadata_update('taeyangg4/south-korea-power-grid-5-minute', '.')"
```

Finally, verify the public dataset and linked notebook:

```powershell
python scripts/kaggle_v2_remote_qa.py
python scripts/kaggle_v2_usability_qa.py
```
