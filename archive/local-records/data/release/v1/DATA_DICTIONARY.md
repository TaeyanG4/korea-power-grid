# Data Dictionary

All files are ZSTD-compressed Parquet and are partitioned into one flat file per
available source-month.

## demand_YYYY_MM.parquet

| Column | Meaning |
|---|---|
| `timestamp` | Source timestamp, stored as a naive datetime |
| `demand_forecast_mw` | Five-minute electricity demand forecast in MW |

Candidate grain: `timestamp`.

## dispatch_YYYY_MM.parquet

| Column | Meaning |
|---|---|
| `timestamp` | Source timestamp, stored as a naive datetime |
| `generator_id` | Source-native generator CODE |
| `dispatch_mw` | Economic dispatch BASEPOINT / target value in MW |

Candidate grain: `timestamp, generator_id`.

## state_estimation_YYYY_MM.parquet

| Column | Meaning |
|---|---|
| `timestamp` | Source timestamp, stored as a naive datetime |
| `generator_id` | Source-native generator CODE |
| `estimated_generation_mw` | State-estimated generator output in MW |

Candidate grain: `timestamp, generator_id`.

Dispatch and state-estimation generator IDs are not assumed to share the same
identifier namespace. No prefix stripping or guessed crosswalk is applied.
