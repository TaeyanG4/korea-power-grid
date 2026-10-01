# Unified Data Dictionary

The Parquet and CSV files contain the same normalized rows in the same four-column
long-form schema.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `timestamp` | Parquet `timestamp[ns]`; CSV text | no | Five-minute KPX source timestamp. CSV format is `YYYY-MM-DD HH:MM:SS`. Timezone is intentionally not asserted. |
| `source` | string | no | Measurement family: `demand`, `dispatch`, or `state_estimation`. |
| `generator_id` | string | yes | Source-native generator CODE for dispatch/state rows; null/blank for demand. |
| `value_mw` | float64 / numeric text | yes | Power value in MW; semantic meaning depends on `source`. |

## value_mw semantics

- `source = demand`: five-minute system demand forecast in MW
- `source = dispatch`: generator economic-dispatch BASEPOINT / target in MW
- `source = state_estimation`: state-estimated generator output in MW

## Candidate grain

- demand rows: `timestamp, source`
- dispatch/state-estimation rows: `timestamp, source, generator_id`

Source-level missingness and the one evidence-backed normalization exception are
documented separately. Missing timestamps are not fabricated or imputed.
