# Phase 3 — Checkpoint 5 Results: Full Observed Board History

Status: **PASS WITH OBSERVATIONS**

Checkpoint 5 completes the historical backfill through the oldest observed KPX
board month without regenerating any previously validated processed roots.

## Final coverage

- logical period: `2015-08` through `2026-07`
- months: 132
- sources: 3
- logical source-month records: **396 / 396**
- per-source logical months: **132 / 132 / 132**
- timestamp parse failures: **0**
- remaining candidate-key duplicates: **0**

The logical dataset is composed of five validated processed roots:

- `data/processed/checkpoint_full_extension`: `2015-08` through `2016-07`
- `data/processed/checkpoint_10y_extension`: `2016-08` through `2018-07`
- `data/processed/checkpoint_8y_extension`: `2018-08` through `2021-07`
- `data/processed/checkpoint_5y_extension`: `2021-08` through `2023-07`
- `data/processed/checkpoint_3y`: `2023-08` through `2026-07`

## Final 12-month extension

For `2015-08` through `2016-07`:

- source-month records accounted: **36 / 36**
- successful raw attachments: **29**
- explicit `source_unavailable`: **7**
- raw QA unexplained problems: **0**
- format QA records accounted: **36 / 36**
- timestamp parse failures: **0**
- outside-month timestamps: **0**
- processed status: **29 success + 7 source_unavailable**

The seven unavailable extension records are:

- demand: `2015-08`, `2015-09`, `2016-07`
- dispatch: `2015-08`, `2015-09`
- state estimation: `2015-08`, `2015-09`

Together with `demand 2019-11` from Checkpoint 3, the full logical history has
eight explicitly unavailable source-month records.

## Ambiguous duplicate snapshot policy

`state_estimation 2016-06` contains two full-generator duplicate snapshots:

- `2016-06-29 17:20`: 407 generator keys × 2 rows, all exact duplicates
- `2016-06-03 17:20`: 407 generator keys × 2 rows; 188 exact pairs and 219
  conflicting MW pairs

Raw ordering shows that each duplicate pair is adjacent. Comparison with
`17:15` and `17:25` does not identify a consistent first/second winner, and the
official KPX article contains no correction, revision, re-upload, error, or
duplicate notice. The source schema also provides no revision field.

Accordingly, the pipeline does **not** keep-first, keep-last, average, or choose
the value closest to an adjacent interval. Instead, the entire ambiguous
`2016-06-03 17:20` timestamp is excluded from normalized output. The exception
is machine-readable in `data/manifests/normalization_exceptions.json` and is
validated against the observed raw structure before it can be applied.

Effect of the exception:

- raw rows excluded: **814**
- candidate keys affected: **407**
- conflicting candidate keys: **219**
- exact candidate keys inside the excluded snapshot: **188**
- downstream missing timestamps added: **1**

## Final extension processing

- input rows: **69,492,469**
- normalization-exception rows removed: **814**
- exact duplicate rows removed: **4,038**
- output rows: **69,487,617**
- Parquet size: **195,852,680 bytes**

## Full-history measured footprint

Across all five processed roots:

- raw stored bytes: **5,354,865,388**
- normalized Parquet bytes: **2,661,216,619**
- input rows: **1,012,831,240**
- normalization-exception rows removed: **814**
- exact duplicate rows removed: **4,581,246**
- output rows: **1,008,249,180**

Per source:

| Source | Input rows | Exception rows | Exact dup rows removed | Output rows | Parquet bytes |
|---|---:|---:|---:|---:|---:|
| demand | 1,122,028 | 0 | 15 | 1,122,013 | 15,626,941 |
| dispatch | 479,358,271 | 0 | 790 | 479,357,481 | 688,676,442 |
| state_estimation | 532,350,941 | 814 | 4,580,441 | 527,769,686 | 1,956,913,236 |

The measured normalized footprint remains within the project's 2–4 GB V1
release target.

## Full-history missingness

Missingness includes unavailable source attachments, gaps present in available
raw files, and the one explicitly removed ambiguous timestamp.

- demand: **35,171** missing timestamps across 17 months
- dispatch: **23,921** missing timestamps across 11 months
- state estimation: **23,578** missing timestamps across 125 months, including
  one normalization-exception timestamp

The largest monthly gap for all three sources is now a fully unavailable oldest
month (`2015-08`, 8,928 expected five-minute timestamps). Missingness is not
silently imputed.

## Decision

**Phase 3 historical backfill is complete.**

Proceed to release packaging and the final redistribution/license gate. The
public Kaggle release must re-check the three official data.go.kr license fields
immediately before publication and include KPX attribution, source URLs,
transformation notes, missingness/source-unavailable notes, and the
normalization-exception policy.
