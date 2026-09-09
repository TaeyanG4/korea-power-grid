# Data Sources

Last verified: 2026-09-10 (Asia/Seoul)

This document records only source facts verified from official Korea Power Exchange (KPX) and data.go.kr pages. Schema details not visible on those pages remain unverified until the Phase 1 pilot.

## V1 source summary

| Source key | Official dataset name | KPX board | data.go.kr | Published grain | Publication timing | Board coverage observed | Portal format |
|---|---|---|---|---|---|---|---|
| `demand` | 5분 단위 전력수요 예측자료 | https://www.kpx.or.kr/board.es?mid=a10109020700&bid=0065 | https://www.data.go.kr/data/15051432/fileData.do | 5-minute | End of following month | 2015-08 through 2026-07 (132 posts) | CSV |
| `dispatch` | 발전기별 5분 단위 경제급전 | https://www.kpx.or.kr/board.es?mid=a10109020200&bid=0070 | https://www.data.go.kr/data/15051425/fileData.do | 5-minute | End of following month | 2015-08 through 2026-07 (132 posts) | TXT |
| `state_estimation` | 발전기별 5분 단위 상태추정 | https://www.kpx.or.kr/board.es?mid=a10109020400&bid=0068 | https://www.data.go.kr/data/15051426/fileData.do | 5-minute | End of following month | 2015-08 through 2026-07 (132 posts) | TXT |

Provider for all three sources: Korea Power Exchange (한국전력거래소, KPX).

## Official publication schedule

KPX's `전력계통 운영정보` disclosure table states that all three V1 sources are published at 5-minute grain and are scheduled for publication at the end of the following month (`익월 말`).

Official schedule page:

- https://www.kpx.or.kr/menu.es?mid=a10109020000

The schedule page explicitly explains that an August dataset scheduled for `익월 말` is expected to be posted at the end of September.

The data.go.kr metadata field `업데이트 주기` is not consistent across the three records (for example, some currently show `수시 (1회성 데이터)`). For project scheduling, the KPX disclosure table and the observed monthly board history are treated as authoritative evidence of the publication process.

## Source 1: 5-minute demand forecast

### Official identity

- Dataset: `한국전력거래소_5분 단위 전력수요 예측자료`
- KPX board: https://www.kpx.or.kr/board.es?mid=a10109020700&bid=0065
- data.go.kr: https://www.data.go.kr/data/15051432/fileData.do
- Provider: Korea Power Exchange

### Official description

data.go.kr describes this as monthly power-system operating information containing 5-minute electricity-demand forecast data by date/time and forecast MW.

### Coverage observed on KPX board

- Latest fully published common month verified: `2026-07`
- Oldest board item: `2015-08`
- Board item count verified: 132
- First-month caveat: the 2015-08 post explicitly says `8.19 ~ 31`; therefore 2015-08 is a partial month and must not be treated as full coverage.

Earliest post:

- https://www.kpx.or.kr/board.es?act=view&bid=0065&list_no=60849&mid=a10109020700&nPage=14&tag=

Latest verified post:

- https://www.kpx.or.kr/board.es?act=view&bid=0065&list_no=78033&mid=a10109020700&nPage=1&tag=
- Attachment shown by KPX: `5분수요예측MW_202607 - 복사본.zip`
- Attachment size shown by KPX: 141.03 KB

### Format status

- Portal logical format: CSV
- KPX delivery wrapper: ZIP attachment
- ZIP member names, delimiter, encoding, exact headers, timestamp representation, timezone, and physical row grain: **unverified until Phase 1 pilot**

## Source 2: generator-level 5-minute economic dispatch

### Official identity

- Dataset: `한국전력거래소_발전기별 5분 단위 경제급전`
- KPX board: https://www.kpx.or.kr/board.es?mid=a10109020200&bid=0070
- data.go.kr: https://www.data.go.kr/data/15051425/fileData.do
- Provider: Korea Power Exchange

### Official description

data.go.kr states that this source covers output target/reference values for generators participating in automatic generation control among centrally dispatched generators. The portal describes the visible fields as time, generator CODE, and BASEPOINT.

### Coverage observed on KPX board

- Latest fully published common month verified: `2026-07`
- Oldest board item: `2015-08`
- Board item count verified: 132
- The 2015-08 post exists, but its article text does not state an exact internal start date. Its true min/max timestamp must be measured from the attachment before declaring it full-month.

Earliest post:

- https://www.kpx.or.kr/board.es?act=view&bid=0070&list_no=60624&mid=a10109020200&nPage=14&tag=

Latest verified post:

- https://www.kpx.or.kr/board.es?act=view&bid=0070&list_no=78025&mid=a10109020200&nPage=1&tag=
- Attachment shown by KPX: `발전기별_5분_경제급전자료(202607).zip`
- Attachment size shown by KPX: 18.9 MB

### Format status

- Portal logical format: TXT
- KPX delivery wrapper: ZIP attachment
- ZIP member names, delimiter, encoding, exact headers, timestamp representation, timezone, generator identifier normalization, and duplicate behavior: **unverified until Phase 1 pilot**

## Source 3: generator-level 5-minute state estimation

### Official identity

- Dataset: `한국전력거래소_발전기별 5분 단위 상태추정`
- KPX board: https://www.kpx.or.kr/board.es?mid=a10109020400&bid=0068
- data.go.kr: https://www.data.go.kr/data/15051426/fileData.do
- Provider: Korea Power Exchange

### Official description

data.go.kr states that the source provides transmission-end state-estimated output for centrally dispatched generators and large non-centrally-dispatched generators every 5 minutes. The portal describes the visible fields as time, generator CODE, and state-estimated MW.

### Coverage observed on KPX board

- Latest fully published common month verified: `2026-07`
- Oldest board item: `2015-08`
- Board item count verified: 132
- First-month caveat: the 2015-08 article explicitly states that it contains results for August 19 through August 31 only.

Earliest post:

- https://www.kpx.or.kr/board.es?act=view&bid=0068&list_no=61111&mid=a10109020400&nPage=14&tag=

Latest verified post:

- https://www.kpx.or.kr/board.es?act=view&bid=0068&list_no=78031&mid=a10109020400&nPage=1&tag=
- Attachment shown by KPX: `라_발전기별 5분 상태추정MW_2026년_7월__.zip`
- Attachment size shown by KPX: 24.38 MB

### Format status

- Portal logical format: TXT
- KPX delivery wrapper: ZIP attachment
- ZIP member names, delimiter, encoding, exact headers, timestamp representation, timezone, generator identifier normalization, and duplicate behavior: **unverified until Phase 1 pilot**

## V1 temporal strategy

The observed common board range is 2015-08 through 2026-07. This is 132 source-months per source (11 years of monthly board entries), but at least demand and state estimation have a partial first month.

Current release strategy:

1. Phase 1 uses only 2026-07, the latest fully published common month.
2. Historical backfill proceeds newest to oldest.
3. 2015-08 is retained as a candidate partial-coverage month, not silently promoted to a full month.
4. Final historical inclusion is decided from measured timestamps, schema stability, and release size.

## Facts intentionally not assumed yet

The following must come from actual downloaded files or another explicitly verified official source:

- timezone / UTC offset encoded by timestamps
- exact delimiters and encodings
- exact physical file layout within ZIPs
- whether each month is one file or multiple members
- exact generator ID semantics beyond the official `generator CODE` description
- generator fuel type, region, capacity, or plant mapping
- whether negative values are valid/invalid
- whether dispatch and state-estimation generator universes should match exactly

## Phase 1 measured physical-format correction

The 2026-07 pilot established physical delivery details that are more specific than the data.go.kr format labels:

- `demand`: the KPX ZIP member is named `.xlsx`, but its magic bytes identify an Excel 97–2003 OLE `.xls` binary. It is readable with `xlrd`. Original columns are `TIME`, `LF05_1`.
- `dispatch`: comma-delimited ASCII TXT. Original columns are `TIME`, `GEN_CODE`, `BASEPOINT`.
- `state_estimation`: comma-delimited CP949 TXT. Original columns are `시간`, `발전기CODE`, `상태추정MW`. Timestamps mix date-only midnight values with Korean `오전`/`오후` 12-hour strings.

These measured physical formats supersede any earlier assumption that the portal's logical `CSV`/`TXT` label exactly describes the downloadable KPX attachment.

## Phase 3 historical-format findings (2021-08 through 2023-07)

Checkpoint 2 content QA measured all 72 source-month files in the two-year
extension. Timestamp parsing succeeded for every record and no timestamp fell
outside its source month.

- `demand`: all 24 months are CP949 comma-delimited text with a two-row
  preamble before the CSV header.
- `dispatch`: 15 months are CP949 comma-delimited text with a five-row
  preamble. Nine months are real Office Open XML `.xlsx` workbooks:
  `2021-08`, `2021-12`, and `2022-01` through `2022-07`. Several workbooks
  partition one month across multiple worksheets; later worksheets may omit
  the header and continue directly with data rows.
- `state_estimation`: all 24 months are CP949 comma-delimited text. Nineteen
  months have no preamble and five months have a three-row preamble.

The `2022-07` dispatch workbook is a source-level partial-month observation:
it contains 2,602 unique five-minute timestamps and ends at
`2022-07-10 00:45`, leaving 6,326 expected timestamps missing through the end
of July. The pipeline records this as missing source coverage and does not
impute or fabricate the absent rows.
