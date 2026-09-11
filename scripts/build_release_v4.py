from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from build_release_v2 import (
    COLUMNS,
    LICENSE_PATH,
    MISSINGNESS_SUMMARY_COLUMNS,
    MISSING_SOURCE_MONTHS_COLUMNS,
    PARQUET_NAME,
    QA_PATH,
    SOURCE_TEXT,
    load_json,
)


ROOT = Path(__file__).resolve().parents[1]
V1_ROOT = ROOT / "data" / "release" / "v1"
V2_ROOT = ROOT / "data" / "release" / "v2"
V4_ROOT = ROOT / "data" / "release" / "v4"
COVER_PATH = ROOT / "docs" / "assets" / "dataset-cover-image.png"

CSV_NAME = "south_korea_power_grid_5min.csv"
DATASET_ID = "taeyangg4/south-korea-power-grid-5-minute"
TITLE = "South Korea Power Grid 5-Minute Data 2015-2026"
SUBTITLE = "1B+ KPX rows in Parquet + CSV at 5-minute resolution"
KEYWORDS = [
    "energy",
    "electricity",
    "government",
    "time series analysis",
    "tabular",
    "asia",
]


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def link_or_copy(source: Path, destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copyfile(source, destination)


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
                "Full-history UTF-8 compatibility export with the same 1,008,249,180 "
                "rows and four columns as the Parquet file. Prefer Parquet for analysis."
            ),
            "schema": main_schema,
        },
        {
            "path": "missing_source_months.csv",
            "description": (
                "Eight official source-month attachments that were unavailable and not fabricated."
            ),
            "schema": {"fields": MISSING_SOURCE_MONTHS_COLUMNS},
        },
        {
            "path": "missingness_summary.csv",
            "description": (
                "Source-level summary of missing five-minute timestamps across the release period."
            ),
            "schema": {"fields": MISSINGNESS_SUMMARY_COLUMNS},
        },
        {
            "path": "release_manifest.json",
            "description": (
                "V4 packaging manifest with row counts, source counts, Parquet/CSV checksums, "
                "lineage, and release-code Git commit."
            ),
        },
    ]


def metadata() -> dict:
    return {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "description": (
            "## Analysis-ready South Korea power-grid operations data\n\n"
            "Version 4 provides **1,008,249,180 normalized Korea Power Exchange (KPX) "
            "five-minute rows from 2015-08 through 2026-07** in two equivalent full-history "
            "formats. `south_korea_power_grid_5min.parquet` is the recommended analytics "
            "file; `south_korea_power_grid_5min.csv` is a plain UTF-8 compatibility export "
            "for tools and workflows that require CSV. Both use the columns `timestamp`, "
            "`source`, `generator_id`, and `value_mw`.\n\n"
            "The CSV is intentionally redundant for compatibility and is much larger than "
            "the typed ZSTD Parquet file. For exploratory analysis, notebooks, DuckDB, "
            "Polars, Spark, or PyArrow, use Parquet and filter by source/time before "
            "materializing rows.\n\n"
            "### Source semantics\n\n"
            "`source=demand` stores the five-minute system demand forecast and has no "
            "generator ID. `source=dispatch` stores generator economic-dispatch BASEPOINT "
            "targets. `source=state_estimation` stores state-estimated generator output. "
            "All values are MW. Generator codes remain source-native and are not joined by "
            "a guessed crosswalk.\n\n"
            "### Data-quality policy\n\n"
            "Missing timestamps remain missing, eight unavailable official source-month "
            "attachments are documented explicitly, exact duplicates are removed only "
            "under the documented candidate-key rule, and one ambiguous 2016-06 "
            "state-estimation timestamp with two conflicting full-generator snapshots is "
            "excluded rather than arbitrarily selecting a version. Timestamps are "
            "timezone-naive because verified timezone metadata is not present in the source files.\n\n"
            "### Provenance\n\n"
            "The original provider is **Korea Power Exchange (KPX), Republic of Korea**. "
            "This is a cleaned derivative dataset, not an official KPX distribution "
            "channel. Official KPX/data.go.kr source links are recorded in the provenance "
            "field; Kaggle license metadata remains `other`."
        ),
        "id": DATASET_ID,
        "id_no": 11_964_918,
        "licenses": [{"name": "other"}],
        "keywords": KEYWORDS,
        "expectedUpdateFrequency": "monthly",
        "userSpecifiedSources": SOURCE_TEXT,
        "image": "dataset-cover-image.png",
        "resources": resources(),
    }


def main() -> int:
    qa = load_json(QA_PATH)
    if qa.get("status") != "PASS":
        raise RuntimeError("Unified V2 data QA has not passed")
    license_audit = load_json(LICENSE_PATH)
    if license_audit.get("status") != "PASS":
        raise RuntimeError("Release license QA has not passed")

    parquet_source = V2_ROOT / PARQUET_NAME
    csv_source = V2_ROOT / CSV_NAME
    expected_parquet_bytes = int(qa["observed"]["parquet"]["bytes"])
    expected_csv_bytes = int(qa["observed"]["csv"]["bytes"])
    if parquet_source.stat().st_size != expected_parquet_bytes:
        raise RuntimeError("Local Parquet size no longer matches verified QA")
    if csv_source.stat().st_size != expected_csv_bytes:
        raise RuntimeError("Local CSV size no longer matches verified QA")

    V4_ROOT.mkdir(parents=True, exist_ok=True)
    for path in V4_ROOT.iterdir():
        if path.is_file():
            path.unlink()

    link_or_copy(parquet_source, V4_ROOT / PARQUET_NAME)
    link_or_copy(csv_source, V4_ROOT / CSV_NAME)
    shutil.copyfile(V1_ROOT / "missing_source_months.csv", V4_ROOT / "missing_source_months.csv")
    shutil.copyfile(V1_ROOT / "missingness_summary.csv", V4_ROOT / "missingness_summary.csv")
    shutil.copyfile(COVER_PATH, V4_ROOT / "dataset-cover-image.png")

    manifest = {
        "release": "v4-parquet-csv",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": DATASET_ID,
        "packaging_change_only": True,
        "release_code_commit": git_commit(),
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
        "packaging_rationale": (
            "Restore the complete UTF-8 CSV compatibility export alongside the canonical "
            "Parquet file. Parquet remains the recommended analysis format."
        ),
        "license_review": {
            "checked_at_asia_seoul": license_audit["checked_at_asia_seoul"],
            "status": license_audit["status"],
            "kaggle_license_category": "other",
        },
    }
    (V4_ROOT / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2), encoding="ascii"
    )
    (V4_ROOT / "dataset-metadata.json").write_text(
        json.dumps(metadata(), ensure_ascii=True, indent=2), encoding="ascii"
    )

    print(
        json.dumps(
            {
                "release": manifest["release"],
                "root": str(V4_ROOT),
                "rows": manifest["rows"],
                "parquet_bytes": expected_parquet_bytes,
                "csv_bytes": expected_csv_bytes,
                "total_data_bytes": expected_parquet_bytes + expected_csv_bytes,
                "release_code_commit": manifest["release_code_commit"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
