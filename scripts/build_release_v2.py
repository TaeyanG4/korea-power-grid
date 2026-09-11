from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V1_ROOT = ROOT / "data" / "release" / "v1"
V2_ROOT = ROOT / "data" / "release" / "v2"
QA_PATH = ROOT / "data" / "audits" / "unified_v2_data_qa.json"
LICENSE_PATH = ROOT / "data" / "audits" / "release_license_check_2026-09-10.json"
COVER_PATH = ROOT / "docs" / "assets" / "dataset-cover-image.png"

PARQUET_NAME = "south_korea_power_grid_5min.parquet"
CSV_NAME = "south_korea_power_grid_5min.csv"

DATASET_ID = "taeyangg4/south-korea-power-grid-5-minute"
TITLE = "South Korea Power Grid 5-Minute Data 2015-2026"
SUBTITLE = "1B+ KPX rows in one Parquet and one CSV, with 5-minute resolution"
KEYWORDS = [
    "energy",
    "electricity",
    "government",
    "time series analysis",
    "tabular",
    "asia",
]

SOURCE_TEXT = (
    "Korea Power Exchange (KPX), Republic of Korea. Official monthly boards: "
    "[5-minute demand forecast](https://www.kpx.or.kr/board.es?mid=a10109020700&bid=0065), "
    "[generator economic dispatch](https://www.kpx.or.kr/board.es?mid=a10109020200&bid=0070), and "
    "[generator state estimation](https://www.kpx.or.kr/board.es?mid=a10109020400&bid=0068). "
    "Official data.go.kr records: [demand](https://www.data.go.kr/data/15051432/fileData.do), "
    "[dispatch](https://www.data.go.kr/data/15051425/fileData.do), and "
    "[state estimation](https://www.data.go.kr/data/15051426/fileData.do). "
    "The official records were re-checked before release and state 이용허락범위 제한 없음."
)

COLUMNS = [
    {
        "name": "timestamp",
        "description": (
            "Five-minute source timestamp from KPX. Parquet stores timestamp[ns]; "
            "CSV uses YYYY-MM-DD HH:MM:SS text. No timezone is asserted."
        ),
        "type": "datetime",
    },
    {
        "name": "source",
        "description": (
            "Measurement family: demand, dispatch, or state_estimation. This field "
            "determines the semantic meaning of value_mw."
        ),
        "type": "string",
    },
    {
        "name": "generator_id",
        "description": (
            "Source-native KPX generator CODE for dispatch/state_estimation; blank/null "
            "for system-level demand rows."
        ),
        "type": "string",
    },
    {
        "name": "value_mw",
        "description": (
            "MW value. demand = demand forecast; dispatch = economic-dispatch BASEPOINT; "
            "state_estimation = state-estimated generator output."
        ),
        "type": "numeric",
    },
]

MISSING_SOURCE_MONTHS_COLUMNS = [
    {
        "name": "source",
        "description": (
            "KPX measurement family whose official monthly attachment was unavailable: "
            "demand, dispatch, or state_estimation."
        ),
        "type": "string",
    },
    {
        "name": "month",
        "description": "Affected source month in YYYY-MM format.",
        "type": "datetime",
    },
    {
        "name": "evidence",
        "description": (
            "Evidence describing why the official source-month attachment is treated as "
            "unavailable."
        ),
        "type": "string",
    },
    {
        "name": "source_article_url",
        "description": (
            "Official KPX board article URL used to verify the unavailable attachment."
        ),
        "type": "string",
    },
]

MISSINGNESS_SUMMARY_COLUMNS = [
    {
        "name": "source",
        "description": "Measurement family: demand, dispatch, or state_estimation.",
        "type": "string",
    },
    {
        "name": "months",
        "description": "Number of calendar months evaluated for this source in the release.",
        "type": "integer",
    },
    {
        "name": "months_with_missing",
        "description": (
            "Number of source months containing one or more missing five-minute timestamps."
        ),
        "type": "integer",
    },
    {
        "name": "missing_timestamps",
        "description": (
            "Total count of missing five-minute timestamps identified for this source "
            "across the release period."
        ),
        "type": "integer",
    },
    {
        "name": "normalization_exception_timestamps_removed",
        "description": (
            "Number of timestamps intentionally removed under documented normalization "
            "exceptions."
        ),
        "type": "integer",
    },
    {
        "name": "max_monthly_missing",
        "description": (
            "Largest number of missing five-minute timestamps in any single source month."
        ),
        "type": "integer",
    },
    {
        "name": "max_missing_month",
        "description": "Source month in YYYY-MM format with the largest missing count.",
        "type": "datetime",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def copy_support_files() -> None:
    for name in (
        "missing_source_months.csv",
        "missingness_summary.csv",
        "normalization_exceptions.json",
    ):
        shutil.copyfile(V1_ROOT / name, V2_ROOT / name)
    shutil.copyfile(COVER_PATH, V2_ROOT / "dataset-cover-image.png")


def readme(qa: dict) -> str:
    parquet = qa["observed"]["parquet"]
    csv_info = qa["observed"]["csv"]
    return f"""# South Korea Power Grid 5-Minute Data (2015-2026)

Normalized Korea Power Exchange (KPX) five-minute operating data covering the
observed monthly board history from **2015-08 through 2026-07**.

## Start here

V2 exposes the full normalized dataset in **two equivalent data files** instead
of hundreds of monthly files:

- `{PARQUET_NAME}` — recommended for Python, Polars, DuckDB, Spark, and analytics
- `{CSV_NAME}` — compatibility export with the same {qa['observed']['rows']:,} rows

Parquet is strongly recommended for normal analysis because it is only
{parquet['bytes'] / 1e9:.2f} GB compared with {csv_info['bytes'] / 1e9:.2f} GB for
the plain CSV export.

## Unified row schema

| Column | Meaning |
|---|---|
| `timestamp` | Five-minute source timestamp; timezone-naive because the source files do not provide verified timezone metadata |
| `source` | `demand`, `dispatch`, or `state_estimation` |
| `generator_id` | Source-native KPX generator CODE; null/blank for demand rows |
| `value_mw` | MW value whose meaning is determined by `source` |

`value_mw` mapping:

- `demand` → five-minute system demand forecast
- `dispatch` → generator economic-dispatch BASEPOINT / target
- `state_estimation` → state-estimated generator output

No guessed generator-ID crosswalk is applied between dispatch and state
estimation.

## Data quality

- logical coverage: 132 months × 3 sources = 396 source-months
- normalized rows: **{qa['observed']['rows']:,}**
- source-unavailable attachments: **8** (see `missing_source_months.csv`)
- missing timestamps are not silently imputed
- exact duplicates were removed only under the documented canonical-key rule
- one ambiguous historical state-estimation timestamp (`2016-06-03 17:20`) was
  excluded rather than arbitrarily choosing between conflicting snapshots; see
  `normalization_exceptions.json`

## Source and reuse

Provider: **Korea Power Exchange (한국전력거래소, KPX)**.

This is a cleaned/normalized derivative dataset, not an official KPX
distribution channel, and it does not imply KPX endorsement. The official
data.go.kr records were re-checked before release and state
`이용허락범위 제한 없음`. Kaggle uses license category `other` so this package
does not invent a Creative Commons license not stated by the official source.

See `SOURCE_LICENSE.md`, `DATA_DICTIONARY.md`, and `release_manifest.json` for
full provenance and integrity metadata.
"""


def data_dictionary() -> str:
    return """# Unified Data Dictionary

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
"""


def source_license(license_audit: dict) -> str:
    checked = license_audit["checked_at_asia_seoul"]
    return f"""# Source, Attribution, and Permission Notes

Provider: **Korea Power Exchange (한국전력거래소, KPX)**.

This release is a normalized derivative and is not an official KPX distribution
channel.

Final permission metadata re-check: `{checked}`.

At that check, all three official data.go.kr records reported
`비용부과유무 = 무료` and `이용허락범위 = 이용허락범위 제한 없음`.

## Official source pages

- Demand KPX board: https://www.kpx.or.kr/board.es?mid=a10109020700&bid=0065
- Demand data.go.kr: https://www.data.go.kr/data/15051432/fileData.do
- Dispatch KPX board: https://www.kpx.or.kr/board.es?mid=a10109020200&bid=0070
- Dispatch data.go.kr: https://www.data.go.kr/data/15051425/fileData.do
- State-estimation KPX board: https://www.kpx.or.kr/board.es?mid=a10109020400&bid=0068
- State-estimation data.go.kr: https://www.data.go.kr/data/15051426/fileData.do

Kaggle license category: `other` (the official source permission is stated above;
this package does not assign a new Creative Commons license).

This project-level review is not legal advice.
"""


def resources() -> list[dict]:
    main_schema = {"fields": COLUMNS}
    return [
        {
            "path": PARQUET_NAME,
            "description": (
                "Recommended analytics file: the complete normalized 2015-2026 KPX "
                "5-minute dataset in one ZSTD Parquet file with 1,008,249,180 rows."
            ),
            "schema": main_schema,
        },
        {
            "path": CSV_NAME,
            "description": (
                "Compatibility export: the same 1,008,249,180 normalized rows as the "
                "Parquet file in one UTF-8 CSV. Parquet is recommended for efficient analysis."
            ),
            "schema": main_schema,
        },
        {
            "path": "README.md",
            "description": "Quick start, unified schema, coverage, caveats, and source/reuse notes.",
        },
        {
            "path": "DATA_DICTIONARY.md",
            "description": "Four-column unified schema, types, units, source semantics, and candidate grain.",
        },
        {
            "path": "SOURCE_LICENSE.md",
            "description": "Official KPX/data.go.kr provenance, attribution, and permission notes.",
        },
        {
            "path": "missing_source_months.csv",
            "description": "Eight official source-month attachments that were unavailable and not fabricated.",
            "schema": {"fields": MISSING_SOURCE_MONTHS_COLUMNS},
        },
        {
            "path": "missingness_summary.csv",
            "description": "Source-level summary of missing five-minute timestamps across the release period.",
            "schema": {"fields": MISSINGNESS_SUMMARY_COLUMNS},
        },
        {
            "path": "normalization_exceptions.json",
            "description": "Evidence-backed record for the ambiguous 2016-06 state-estimation snapshot exclusion.",
        },
        {
            "path": "release_manifest.json",
            "description": "V2 file sizes, SHA-256 hashes, row counts, build commit, and upstream V1 lineage.",
        },
    ]


def metadata() -> dict:
    resource_items = resources()
    return {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "description": (
            "## Analysis-ready South Korea power-grid operations data\n\n"
            "This dataset provides normalized **Korea Power Exchange (KPX)** five-minute "
            "operating data from 2015-08 through 2026-07 in a simple unified long schema. "
            "Version 2 replaces hundreds of monthly analytics files with two equivalent "
            "full-history files: one compact ZSTD Parquet file and one plain UTF-8 CSV. "
            "Both contain **1,008,249,180 rows** with the columns `timestamp`, `source`, "
            "`generator_id`, and `value_mw`.\n\n"
            "### Source semantics\n\n"
            "`source=demand` stores the five-minute system demand forecast and has no "
            "generator ID. `source=dispatch` stores generator economic-dispatch BASEPOINT "
            "targets. `source=state_estimation` stores state-estimated generator output. "
            "All values are MW. Generator codes remain source-native and are not joined by "
            "a guessed crosswalk.\n\n"
            "### Data-quality policy\n\n"
            "Missing timestamps are preserved as missing, eight unavailable official "
            "source-month attachments are documented explicitly, and exact duplicates are "
            "removed only under a documented candidate-key rule. One ambiguous historical "
            "state-estimation timestamp with two conflicting full-generator snapshots is "
            "excluded rather than arbitrarily selecting a version. Timestamps are timezone-"
            "naive because verified timezone metadata is not present in the source files.\n\n"
            "### Which file should I use?\n\n"
            "Use the Parquet file for normal Python/Polars/DuckDB/Spark analysis; it is far "
            "smaller and typed. The CSV is supplied as a single compatibility/export file "
            "for tools that prefer CSV. See the included README and data dictionary before "
            "analysis.\n\n"
            "### Provenance\n\n"
            "The original provider is **Korea Power Exchange (한국전력거래소, KPX)**. This "
            "is a cleaned derivative dataset, not an official KPX distribution channel. "
            "Official data.go.kr records were re-checked before release and report "
            "`이용허락범위 제한 없음`; Kaggle license metadata therefore remains `other`."
        ),
        "id": DATASET_ID,
        "licenses": [{"name": "other"}],
        "keywords": KEYWORDS,
        "expectedUpdateFrequency": "monthly",
        "userSpecifiedSources": SOURCE_TEXT,
        "image": "dataset-cover-image.png",
        "resources": resource_items,
    }


def main() -> int:
    qa = load_json(QA_PATH)
    if qa.get("status") != "PASS":
        raise RuntimeError("Unified V2 data QA has not passed")
    license_audit = load_json(LICENSE_PATH)
    if license_audit.get("status") != "PASS":
        raise RuntimeError("Release license QA has not passed")

    V2_ROOT.mkdir(parents=True, exist_ok=True)
    copy_support_files()
    (V2_ROOT / "README.md").write_text(readme(qa), encoding="utf-8")
    (V2_ROOT / "DATA_DICTIONARY.md").write_text(data_dictionary(), encoding="utf-8")
    (V2_ROOT / "SOURCE_LICENSE.md").write_text(
        source_license(license_audit), encoding="utf-8"
    )

    release_manifest = {
        "release": "v2-unified",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "dataset_id": DATASET_ID,
        "period": {"start": "2015-08", "end": "2026-07", "months": 132},
        "logical_source_month_records": 396,
        "source_unavailable_records": 8,
        "rows": qa["observed"]["rows"],
        "source_rows": qa["observed"]["source_rows"],
        "schema": COLUMNS,
        "files": {
            "parquet": qa["observed"]["parquet"],
            "csv": qa["observed"]["csv"],
        },
        "upstream_v1": {
            "manifest": "data/release/v1/release_manifest.json",
            "manifest_sha256": sha256(V1_ROOT / "release_manifest.json"),
        },
        "license_review": {
            "checked_at_asia_seoul": license_audit["checked_at_asia_seoul"],
            "status": license_audit["status"],
            "kaggle_license_category": "other",
        },
    }
    (V2_ROOT / "release_manifest.json").write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    meta = metadata()
    (V2_ROOT / "dataset-metadata.json").write_text(
        json.dumps(meta, ensure_ascii=True, indent=2), encoding="ascii"
    )

    print(
        json.dumps(
            {
                "release": "v2-unified",
                "root": str(V2_ROOT),
                "rows": qa["observed"]["rows"],
                "parquet_bytes": qa["observed"]["parquet"]["bytes"],
                "csv_bytes": qa["observed"]["csv"]["bytes"],
                "upload_resources": len(meta["resources"]),
                "git_commit": release_manifest["git_commit"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
