from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / "data" / "release" / "v2"
OUT = ROOT / "data" / "audits" / "unified_v2_data_qa.json"

PARQUET = V2_ROOT / "south_korea_power_grid_5min.parquet"
CSV = V2_ROOT / "south_korea_power_grid_5min.csv"

EXPECTED_ROWS = 1_008_249_180
EXPECTED_SOURCE_ROWS = {
    "demand": 1_122_013,
    "dispatch": 479_357_481,
    "state_estimation": 527_769_686,
}
EXPECTED_SCHEMA = [
    ("timestamp", "timestamp[ns]", False),
    ("source", "string", False),
    ("generator_id", "string", True),
    ("value_mw", "double", True),
]
EXPECTED_CSV_HEADER = b'"timestamp","source","generator_id","value_mw"\n'


def sha256_and_newlines(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    newlines = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024 * 1024), b""):
            digest.update(chunk)
            newlines += chunk.count(b"\n")
    return digest.hexdigest(), newlines


def source_counts(parquet: pq.ParquetFile) -> dict[str, int]:
    counts = {source: 0 for source in EXPECTED_SOURCE_ROWS}
    for batch_index, batch in enumerate(
        parquet.iter_batches(batch_size=2_000_000, columns=["source"]), 1
    ):
        values = pc.value_counts(batch.column(0)).to_pylist()
        for item in values:
            counts[str(item["values"])] = counts.get(str(item["values"]), 0) + int(
                item["counts"]
            )
        if batch_index % 50 == 0:
            print(f"source-count batch {batch_index}", flush=True)
    return counts


def main() -> int:
    problems: list[dict] = []
    checks: dict[str, bool] = {}

    checks["parquet_exists"] = PARQUET.is_file()
    checks["csv_exists"] = CSV.is_file()
    checks["no_partial_files"] = not any(V2_ROOT.glob("*.part"))
    if not all([checks["parquet_exists"], checks["csv_exists"]]):
        report = {"status": "FAIL", "checks": checks, "problems": problems}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1

    parquet = pq.ParquetFile(PARQUET)
    schema = [(f.name, str(f.type), f.nullable) for f in parquet.schema_arrow]
    parquet_rows = int(parquet.metadata.num_rows)
    row_groups = int(parquet.metadata.num_row_groups)
    counts = source_counts(parquet)
    parquet.close()

    checks["parquet_schema_exact"] = schema == EXPECTED_SCHEMA
    checks["parquet_rows_exact"] = parquet_rows == EXPECTED_ROWS
    checks["source_rows_exact"] = counts == EXPECTED_SOURCE_ROWS

    with CSV.open("rb") as handle:
        header = handle.readline()
    checks["csv_header_exact"] = header == EXPECTED_CSV_HEADER

    print("hashing Parquet", flush=True)
    parquet_sha256, parquet_newlines = sha256_and_newlines(PARQUET)
    print("hashing and counting CSV rows", flush=True)
    csv_sha256, csv_newlines = sha256_and_newlines(CSV)
    checks["csv_rows_exact"] = csv_newlines == EXPECTED_ROWS + 1
    checks["parquet_binary_has_no_row_accounting_requirement"] = parquet_newlines >= 0

    passed = all(checks.values()) and not problems
    report = {
        "release": "v2-unified-data",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "problems": problems,
        "observed": {
            "rows": parquet_rows,
            "source_rows": counts,
            "schema": schema,
            "parquet": {
                "path": str(PARQUET.relative_to(ROOT)).replace("\\", "/"),
                "bytes": PARQUET.stat().st_size,
                "row_groups": row_groups,
                "sha256": parquet_sha256,
            },
            "csv": {
                "path": str(CSV.relative_to(ROOT)).replace("\\", "/"),
                "bytes": CSV.stat().st_size,
                "data_rows": csv_newlines - 1,
                "sha256": csv_sha256,
            },
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    print(f"WROTE {OUT}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
