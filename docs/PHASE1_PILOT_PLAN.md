# Phase 1 — One-Month Pilot Plan

Pilot month: **2026-07**

Reason: as of 2026-09-10, 2026-07 is the latest month that has been published for all three V1 sources, and all three posts were published by KPX on 2026-08-31.

## Scope

Download exactly three KPX attachments for 2026-07:

1. `demand`
2. `dispatch`
3. `state_estimation`

Do not download any other month during the pilot.

## Expected download size before execution

Sizes shown by KPX on the official 2026-07 posts:

- demand ZIP: 141.03 KB
- dispatch ZIP: 18.9 MB
- state-estimation ZIP: 24.38 MB
- displayed total: approximately 43.4 MB

These are webpage-displayed attachment sizes, not local byte measurements. The audit must record exact local byte counts after download.

## Pilot checks

### Download provenance

- source key
- month
- source article URL
- attachment URL
- local filename
- downloaded timestamp
- exact byte size
- SHA-256
- HTTP status / retry count

### Archive inspection

- ZIP validity
- member names
- member count
- extracted size
- file extensions
- encoding evidence
- delimiter evidence
- header presence

### Schema inspection

- exact original column names
- inferred data types, clearly marked as inference
- timestamp representation
- generator identifier field
- numeric MW fields
- null representation

### Grain and coverage

Demand candidate grain:

- `timestamp`

Dispatch candidate grain:

- `(timestamp, generator_id)`

State-estimation candidate grain:

- `(timestamp, generator_id)`

For each source measure:

- row count
- min/max timestamp
- unique timestamp count
- expected 5-minute timestamp count for July 2026
- missing intervals
- duplicate candidate-key count
- parsing failures
- generator ID null count where applicable
- unique generator count where applicable

### Numeric audit

- null
- NaN
- Inf
- negative count
- min/max
- quantiles useful for forensic review

Do not delete outliers or negative values during the pilot.

### Cross-source audit

- overlap of dispatch and state-estimation generator IDs
- compare time coverage across all three sources
- exploratory comparison of aggregate generator values and demand forecast, without treating equality as a hard QA rule

### Parquet measurement

Create a loss-minimizing pilot Parquet representation and record:

- Parquet byte size
- compression settings
- row count after conversion
- exact schema

Do not publish normalized column names as final canonical definitions until original semantics have been verified.

## Machine-readable output

Target:

`data/audits/pilot_2026_07.json`

It should contain source-level audit objects plus a projection section for:

- 3 years
- 5 years
- 8 years
- 10 years
- full observed history

Size projections must distinguish:

- direct linear projection from the pilot
- measured historical size when later checkpoints exist

## Phase 1 exit gate

Proceed to historical collector/backfill design only if:

- all three official attachments are downloadable
- archives/files are parseable reproducibly
- timestamps and candidate grain can be established
- no license blocker has appeared
- projected release size is compatible with the V1 size policy, or a clear partition/period strategy exists

If a source has an incompatible or ambiguous schema, stop and document the issue instead of forcing normalization.

