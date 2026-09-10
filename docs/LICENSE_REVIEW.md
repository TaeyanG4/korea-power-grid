# License and Redistribution Review

Last verified: 2026-09-10 (Asia/Seoul)

This is a project-level source and redistribution review, not legal advice.

## Decision

**Phase 1 pilot: GO**

**Historical collection: GO only after the Phase 1 pilot validates the physical files and the project records source provenance/checksums.**

**Kaggle redistribution: GO. V1 was published after package QA, private remote QA, and the final same-day license re-check all passed.**

The current official data.go.kr records for all three V1 datasets state:

- provider: Korea Power Exchange
- cost: free (`무료`)
- permitted-use scope: `이용허락범위 제한 없음`

No dataset-specific restriction is currently displayed on those records.

## Final release re-verification

The release gate was re-run again on `2026-09-10T10:26:19+09:00` immediately
before public publication. The machine-readable result is:

`data/audits/release_license_check_2026-09-10.json`

Status: **PASS**

All three official data.go.kr records still report:

- provider: Korea Power Exchange (`한국전력거래소`)
- `비용부과유무 = 무료`
- `이용허락범위 = 이용허락범위 제한 없음`

The release metadata will use Kaggle's `other` license category and explain the
official Korean public-data permission field in the dataset description rather
than asserting a Creative Commons license that the source does not state.

## Official license evidence

### Demand forecast

- data.go.kr record: https://www.data.go.kr/data/15051432/fileData.do
- Current record: `비용부과유무 = 무료`
- Current record: `이용허락범위 = 이용허락범위 제한 없음`

### Generator economic dispatch

- data.go.kr record: https://www.data.go.kr/data/15051425/fileData.do
- Current record: `비용부과유무 = 무료`
- Current record: `이용허락범위 = 이용허락범위 제한 없음`

### Generator state estimation

- data.go.kr record: https://www.data.go.kr/data/15051426/fileData.do
- Current record: `비용부과유무 = 무료`
- Current record: `이용허락범위 = 이용허락범위 제한 없음`

## Redistribution assessment

For V1, the official data.go.kr records are the primary license evidence because they are the Korean government's public-data catalog entries for the exact KPX datasets.

The phrase `이용허락범위 제한 없음` provides a strong basis for using and redistributing the data in a Kaggle dataset. The project will nevertheless preserve attribution and provenance rather than presenting the files as originally authored by this repository.

Release documentation must include at minimum:

- provider: Korea Power Exchange (KPX)
- original KPX board URL for each source
- data.go.kr dataset URL for each source
- date on which license metadata was re-checked
- statement that the Kaggle package is a cleaned/normalized derivative and is not an official KPX distribution channel

## Why public release still has a package gate

The portal metadata can change. Therefore the project must re-check the three official data.go.kr records immediately before a public Kaggle release and record that verification date in the release manifest or release notes.

If any source stops showing `이용허락범위 제한 없음`, or displays a new special condition, the release is blocked until that condition is reviewed.

## Source-of-truth policy

1. Dataset-specific data.go.kr records are the source of truth for the current license field.
2. KPX board pages are the source of truth for attachments, monthly history, and publication behavior.
3. Third-party mirrors or metadata aggregators are not used to override current official records.
4. A stale third-party license label must not be propagated into Kaggle metadata without official confirmation.

## Release gate

Before a public Kaggle release, all items below must be true:

- [x] data.go.kr license field re-checked for demand
- [x] data.go.kr license field re-checked for dispatch
- [x] data.go.kr license field re-checked for state estimation
- [x] official KPX/data.go.kr source URLs included in package documentation
- [x] release files contain no unrelated copyrighted website assets
- [x] package describes transformations and does not imply KPX endorsement
- [x] release manifest records the license-review date

If any item fails, public redistribution pauses even if collection/analysis can continue locally.
