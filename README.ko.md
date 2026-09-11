<p align="center">
  <img src="docs/assets/dataset-cover-image.png" alt="대한민국 전력계통 운영 데이터셋 표지" width="560">
</p>

# 대한민국 전력계통 — KPX 5분 단위 운영 데이터셋

[English](README.md) · **한국어** · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

이 저장소는 Kaggle에 공개한 **South Korea Power Grid 5-Minute Data** 데이터셋을 만들기 위한 재현 가능한 **수집·정규화·품질검증·배포 파이프라인**입니다.

**한국전력거래소(KPX)**가 월별로 공개하는 자료를 수집해, **5분 단위 전력수요 예측**, **발전기별 경제급전 BASEPOINT(목표값)**, **발전기별 상태추정 출력**을 하나의 분석용 long-format 테이블로 정규화합니다.

**데이터셋:** https://www.kaggle.com/datasets/taeyangg4/south-korea-power-grid-5-minute

## 데이터 한눈에 보기

| 항목 | 현재 Kaggle 릴리스 (V4) |
|---|---|
| KPX 게시판 관측 범위 | **2015-08 → 2026-07** |
| 시간 해상도 | **5분** |
| 정규화 행 수 | **1,008,249,180** |
| 신호 종류 | `demand`, `dispatch`, `state_estimation` |
| 권장 파일 | `south_korea_power_grid_5min.parquet` — **1.99 GB** |
| CSV 호환용 일부 파일 | `south_korea_power_grid_5min_2026_07.csv` — **2026-07, 10,060,444행** |
| 원 제공기관 | 한국전력거래소(KPX) |

현재 Kaggle 릴리스는 **2015-2026 전체 기간을 Parquet 1개**로 제공하고, CSV가 꼭 필요한 도구를 위해 **2026년 7월 전체 신호 10,060,444행을 담은 CSV 호환용 일부 파일**을 함께 제공합니다. 50GB가 넘는 전체 CSV를 중복 배포하지 않아 파일 선택과 다운로드 부담을 줄였습니다.

## 세 신호의 의미

| `source` | `value_mw`의 의미 | `generator_id` |
|---|---|---|
| `demand` | 5분 단위 계통 **전력수요 예측값**(MW) | 없음 |
| `dispatch` | 발전기 **경제급전 BASEPOINT / 목표값**(MW) | KPX 원본 발전기 CODE |
| `state_estimation` | **상태추정 발전기 출력**(MW) | KPX 원본 발전기 CODE |

세 신호는 서로 관련되어 있지만 **동일한 측정값이 아닙니다**. 특히 경제급전과 상태추정의 발전기 CODE가 동일 체계라고 임의로 가정하거나 추정 매핑을 만들지 않습니다.

## 통합 스키마

전체 Parquet과 2026-07 CSV는 모두 다음 4개 열을 사용합니다.

| 열 | 설명 |
|---|---|
| `timestamp` | KPX 원본의 5분 단위 시각. 원본 파일에서 검증 가능한 시간대 정보가 확인되지 않아 timezone을 임의 지정하지 않습니다. |
| `source` | `demand`, `dispatch`, `state_estimation` 중 하나 |
| `generator_id` | 발전기 단위 자료의 KPX 원본 발전기 CODE. `demand` 행은 비어 있음 |
| `value_mw` | MW 값. 실제 의미는 `source`에 따라 결정됨 |

## 빠른 시작

전체 데이터가 10억 행을 넘으므로 Parquet에서 필요한 구간과 열을 **먼저 필터링한 뒤** pandas로 변환하는 방식을 권장합니다.

```python
from datetime import datetime
import pyarrow.dataset as ds

grid = ds.dataset("south_korea_power_grid_5min.parquet", format="parquet")

week = grid.to_table(
    columns=["timestamp", "value_mw"],
    filter=(
        (ds.field("source") == "demand")
        & (ds.field("timestamp") >= datetime(2026, 7, 1))
        & (ds.field("timestamp") < datetime(2026, 7, 8))
    ),
)

df = week.to_pandas()
print(df.head())
```

Kaggle에는 메모리 사용을 억제한 구간 필터링, 5분 램프 분석, 운영 신호 집계, 발전기 집중도, 데이터 커버리지 검사를 보여주는 공개 노트북도 연결되어 있습니다.

## 데이터 품질 원칙

- 공식 첨부파일을 확보할 수 없었던 **8개 source-month**는 만들어내지 않고 명시적으로 기록합니다.
- 누락된 5분 시각은 자동 보간하지 않습니다.
- 중복 제거는 문서화된 canonical key 기준에서 정확 중복인 경우에만 수행합니다.
- `2016-06-03 17:20` 상태추정 자료에는 서로 충돌하는 전체 발전기 스냅샷 두 개가 존재해, 임의 선택 대신 해당 시각 전체를 제외하고 예외로 기록했습니다.
- 원본에 검증 가능한 timezone 메타데이터가 없어 timestamp는 timezone-naive 상태로 유지합니다.

Kaggle 패키지의 `missing_source_months.csv`, `missingness_summary.csv`, `normalization_exceptions.json`, `release_manifest.json`에서 근거를 확인할 수 있습니다.

## GitHub 저장소와 Kaggle 데이터셋의 역할

| GitHub | Kaggle |
|---|---|
| 원천 게시물 탐색 및 수집 | 최종 분석용 데이터 배포 |
| 과거 파일 형식 변화 처리 | 전체 Parquet + 2026-07 CSV 일부 파일 |
| 정규화 코드 | 데이터 사전 및 출처 문서 |
| QA, manifest, checksum, 릴리스 게이트 | 공개 노트북 및 Data Card |

대용량 raw/working/processed/release 데이터는 Git에서 제외하고, 재현성을 위한 작은 manifest와 audit 결과만 저장합니다.

## KPX 자료 수집

수집기는 KPX 월별 게시물을 탐색한 뒤 각 게시물의 첨부파일을 해석합니다. 132개월치 첨부 URL을 하드코딩하지 않습니다.

```powershell
python scripts/collect.py --start 2023-08 --end 2026-07 --dry-run
python scripts/collect.py --start 2023-08 --end 2026-07
```

## 문서

- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — 공식 출처와 역사적 파일 형식 변화
- [`docs/LICENSE_REVIEW.md`](docs/LICENSE_REVIEW.md) — 출처·재배포 검토
- [`docs/KAGGLE_PUBLISHING.md`](docs/KAGGLE_PUBLISHING.md) — 카드 이미지 크롭, Data Card 갱신, Usability 메타데이터 메모
- [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) — Phase 0–3 및 V1 구축 이력
- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) — V2 통합 스키마와 source별 의미

기존 Phase 중심 문서는 재현성을 위해 보존하지만, 프로젝트 첫 화면에서는 현재 데이터셋과 사용법을 우선 설명합니다.

## 출처 및 이용

원 제공기관은 **한국전력거래소(KPX)**입니다. 이 프로젝트는 공식 KPX 배포 채널이 아니라 정제·정규화한 파생 데이터셋이며 KPX의 보증이나 승인을 의미하지 않습니다. 릴리스 직전 확인한 data.go.kr 원문에는 `이용허락범위 제한 없음`으로 표시되어 있어, Kaggle에는 원 출처에 없는 Creative Commons 라이선스를 임의 부여하지 않고 `other` 카테고리를 사용합니다.
