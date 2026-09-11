from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.dataset as ds

from build_release_v2 import (
    COLUMNS,
    LICENSE_PATH,
    MISSINGNESS_SUMMARY_COLUMNS,
    MISSING_SOURCE_MONTHS_COLUMNS,
    PARQUET_NAME,
    QA_PATH,
    SOURCE_TEXT,
    load_json,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
V1_ROOT = ROOT / "data" / "release" / "v1"
V2_ROOT = ROOT / "data" / "release" / "v2"
V4_ROOT = ROOT / "data" / "release" / "v4"
COVER_PATH = ROOT / "docs" / "assets" / "dataset-cover-image.png"

CSV_NAME = "south_korea_power_grid_5min_2026_07.csv"
CSV_START = datetime(2026, 7, 1)
CSV_END = datetime(2026, 8, 1)
CSV_ROWS = 10_060_444
DATASET_ID = "taeyangg4/south-korea-power-grid-5-minute"
TITLE = "South Korea Power Grid 5-Minute Data 2015-2026"
SUBTITLE = "1B+ KPX rows in Parquet + July 2026 CSV sample"
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


def build_csv_sample(parquet_source: Path, destination: Path) -> dict:
    dataset = ds.dataset(parquet_source, format="parquet")
    predicate = (
        (ds.field("timestamp") >= CSV_START)
        & (ds.field("timestamp") < CSV_END)
    )
    scanner = dataset.scanner(
        columns=["timestamp", "source", "generator_id", "value_mw"],
        filter=predicate,
        batch_size=131_072,
    )
    output_schema = pa.schema(
        [
            ("timestamp", pa.string()),
            ("source", pa.string()),
            ("generator_id", pa.string()),
            ("value_mw", pa.float64()),
        ]
    )
    rows = 0
    source_rows: dict[str, int] = {
        "demand": 0,
        "dispatch": 0,
        "state_estimation": 0,
    }
    with pacsv.CSVWriter(destination, output_schema) as writer:
        for batch in scanner.to_batches():
            formatted_timestamp = pc.cast(
                pc.cast(batch.column(0), pa.timestamp("s")), pa.string()
            )
            output = pa.RecordBatch.from_arrays(
                [
                    formatted_timestamp,
                    batch.column(1),
                    batch.column(2),
                    batch.column(3),
                ],
                schema=output_schema,
            )
            writer.write_batch(output)
            rows += output.num_rows
            counts = pc.value_counts(batch.column(1))
            for item in counts.to_pylist():
                source_rows[str(item["values"])] += int(item["counts"])

    if rows != CSV_ROWS:
        raise RuntimeError(f"CSV sample row count changed: expected {CSV_ROWS}, got {rows}")
    return {
        "path": CSV_NAME,
        "period": {"start": "2026-07-01", "end_exclusive": "2026-08-01"},
        "rows": rows,
        "source_rows": source_rows,
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }


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
                "UTF-8 CSV compatibility slice for 2026-07 with all three sources and "
                "10,060,444 rows. Use the Parquet file for the complete 2015-2026 history."
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
            "five-minute rows from 2015-08 through 2026-07** in one compact ZSTD Parquet "
            "file. A separate UTF-8 CSV contains the complete **2026-07 month** across all "
            "three sources (10,060,444 rows) for CSV-only tools and quick interoperability "
            "tests. Both files use the columns `timestamp`, `source`, `generator_id`, and "
            "`value_mw`.\n\n"
            "Use `south_korea_power_grid_5min.parquet` for the full history. The July 2026 "
            "CSV is intentionally a bounded compatibility slice rather than a duplicate "
            "50+ GB copy of the entire table. For exploratory analysis, notebooks, DuckDB, "
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
    expected_parquet_bytes = int(qa["observed"]["parquet"]["bytes"])
    if parquet_source.stat().st_size != expected_parquet_bytes:
        raise RuntimeError("Local Parquet size no longer matches verified QA")

    V4_ROOT.mkdir(parents=True, exist_ok=True)
    for path in V4_ROOT.iterdir():
        if path.is_file():
            path.unlink()

    link_or_copy(parquet_source, V4_ROOT / PARQUET_NAME)
    csv_info = build_csv_sample(parquet_source, V4_ROOT / CSV_NAME)
    shutil.copyfile(V1_ROOT / "missing_source_months.csv", V4_ROOT / "missing_source_months.csv")
    shutil.copyfile(V1_ROOT / "missingness_summary.csv", V4_ROOT / "missingness_summary.csv")
    shutil.copyfile(COVER_PATH, V4_ROOT / "dataset-cover-image.png")

    manifest = {
        "release": "v4-parquet-plus-july-csv",
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
            "csv_sample": csv_info,
        },
        "packaging_rationale": (
            "Keep one canonical full-history Parquet and add a bounded July 2026 UTF-8 CSV "
            "compatibility slice instead of duplicating the full 50+ GB table."
        ),
        "license_review": {
            "checked_at_asia_seoul": license_audit["checked_at_asia_seoul"],
            "status": license_audit["status"],
            "kaggle_license_category": "other",
        },
    }
    (V4_ROOT / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (V4_ROOT / "dataset-metadata.json").write_text(
        json.dumps(metadata(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "release": manifest["release"],
                "root": str(V4_ROOT),
                "rows": manifest["rows"],
                "parquet_bytes": expected_parquet_bytes,
                "csv_sample_rows": csv_info["rows"],
                "csv_sample_bytes": csv_info["bytes"],
                "total_data_bytes": expected_parquet_bytes + csv_info["bytes"],
                "release_code_commit": manifest["release_code_commit"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
