# V2 unified data dictionary

The Kaggle V2 Parquet and CSV contain the same normalized rows in the same four-column long-form schema.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `timestamp` | Parquet `timestamp[ns]`; CSV text | no | Five-minute KPX source timestamp. CSV uses `YYYY-MM-DD HH:MM:SS`. A timezone is not asserted because verified timezone metadata is not present in the source files. |
| `source` | string | no | Measurement family: `demand`, `dispatch`, or `state_estimation`. |
| `generator_id` | string | yes | Source-native KPX generator CODE for dispatch/state-estimation rows; null/blank for demand. |
| `value_mw` | float64 / numeric text | yes | Power value in MW; semantics depend on `source`. |

## `value_mw` semantics

- `source = demand` → five-minute system demand forecast in MW
- `source = dispatch` → generator economic-dispatch BASEPOINT / target in MW
- `source = state_estimation` → state-estimated generator output in MW

## Candidate grain

- demand: `timestamp, source`
- dispatch/state estimation: `timestamp, source, generator_id`

Generator IDs are retained in source-native form. The project does not assume that dispatch and state-estimation identifiers share a validated crosswalk.

Missing timestamps are not fabricated or silently imputed. See [`DATA_SOURCES.md`](DATA_SOURCES.md) and the Kaggle package quality files for source-level missingness and normalization exceptions.
