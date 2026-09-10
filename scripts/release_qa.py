from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "data" / "release" / "v1"
EXPECTED_SCHEMAS = {
    "demand": ["timestamp", "demand_forecast_mw"],
    "dispatch": ["timestamp", "generator_id", "dispatch_mw"],
    "state_estimation": ["timestamp", "generator_id", "estimated_generation_mw"],
}
REQUIRED_AUXILIARY = {
    "dataset-metadata.json",
    "README.md",
    "DATA_DICTIONARY.md",
    "SOURCE_LICENSE.md",
    "missing_source_months.csv",
    "missingness_summary.csv",
    "normalization_exceptions.json",
    "release_manifest.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-hash",
        action="store_true",
        help="Skip re-hashing Parquet files; intended only for fast development checks",
    )
    args = parser.parse_args()

    problems: list[dict] = []
    manifest = load_json(RELEASE_ROOT / "release_manifest.json")
    metadata = load_json(RELEASE_ROOT / "dataset-metadata.json")
    final_audit = load_json(
        ROOT / "data" / "audits" / "phase3_checkpoint5_summary.json"
    )
    license_audit = load_json(
        ROOT / "data" / "audits" / "release_license_check_2026-09-10.json"
    )

    checks = {
        "full_history_checkpoint_passed": final_audit.get("status")
        == "PASS_WITH_OBSERVATIONS",
        "release_license_gate_passed": license_audit.get("status") == "PASS",
        "logical_records_396": manifest.get("logical_source_month_records") == 396,
        "available_parquet_files_388": manifest.get("available_parquet_files") == 388,
        "source_unavailable_records_8": manifest.get("source_unavailable_records") == 8,
        "output_rows_match_final_audit": manifest.get("output_rows") == 1_008_249_180,
        "parquet_bytes_match_final_measurement": manifest.get("parquet_size_bytes")
        == 2_661_216_619,
        "normalization_exception_rows_814": manifest.get(
            "normalization_exception_rows_removed"
        )
        == 814,
        "metadata_id_expected": metadata.get("id")
        == "taeyangg4/south-korea-power-grid-5-minute",
        "metadata_license_other": metadata.get("licenses") == [{"name": "other"}],
        "metadata_title_length_valid": 6 <= len(metadata.get("title", "")) <= 50,
        "metadata_subtitle_length_valid": 20
        <= len(metadata.get("subtitle", ""))
        <= 80,
        "license_timestamp_matches": manifest.get("license_review", {}).get(
            "checked_at_asia_seoul"
        )
        == license_audit.get("checked_at_asia_seoul"),
    }

    actual_names = {path.name for path in RELEASE_ROOT.iterdir() if path.is_file()}
    parquet_names = {name for name in actual_names if name.endswith(".parquet")}
    expected_parquet_names = {
        str(item["release_file"])
        for item in manifest["files"]
        if item["status"] == "success"
    }
    checks["parquet_filename_set_exact"] = parquet_names == expected_parquet_names
    checks["required_auxiliary_files_present"] = REQUIRED_AUXILIARY <= actual_names
    checks["no_unexpected_release_files"] = actual_names == (
        expected_parquet_names | REQUIRED_AUXILIARY
    )

    total_size = 0
    total_rows = 0
    per_source_files = {source: 0 for source in EXPECTED_SCHEMAS}
    for index, item in enumerate(manifest["files"], 1):
        if item["status"] != "success":
            continue
        path = RELEASE_ROOT / str(item["release_file"])
        if not path.exists():
            problems.append({"file": path.name, "problem": "missing"})
            continue
        size = path.stat().st_size
        total_size += size
        if size != int(item["parquet_size_bytes"]):
            problems.append(
                {"file": path.name, "problem": "size_mismatch", "actual": size}
            )

        parquet = pq.ParquetFile(path)
        rows = int(parquet.metadata.num_rows)
        total_rows += rows
        if rows != int(item["output_rows"]):
            problems.append(
                {"file": path.name, "problem": "row_count_mismatch", "actual": rows}
            )
        source = str(item["source"])
        per_source_files[source] += 1
        columns = parquet.schema_arrow.names
        if columns != EXPECTED_SCHEMAS[source]:
            problems.append(
                {
                    "file": path.name,
                    "problem": "schema_mismatch",
                    "actual": columns,
                    "expected": EXPECTED_SCHEMAS[source],
                }
            )

        if not args.skip_hash:
            actual_hash = sha256(path)
            if actual_hash != item["sha256"]:
                problems.append(
                    {"file": path.name, "problem": "sha256_mismatch"}
                )
        if index % 50 == 0:
            print(f"validated manifest record {index}/396", flush=True)

    checks["total_parquet_size_matches"] = total_size == manifest["parquet_size_bytes"]
    checks["total_rows_match"] = total_rows == manifest["output_rows"]
    checks["per_source_available_file_counts"] = per_source_files == {
        "demand": 128,
        "dispatch": 130,
        "state_estimation": 130,
    }

    with (RELEASE_ROOT / "missing_source_months.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        unavailable = list(csv.DictReader(handle))
    checks["missing_source_month_rows_8"] = len(unavailable) == 8

    with (RELEASE_ROOT / "missingness_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        missingness = list(csv.DictReader(handle))
    checks["missingness_sources_3"] = {row["source"] for row in missingness} == {
        "demand",
        "dispatch",
        "state_estimation",
    }

    exception_payload = load_json(RELEASE_ROOT / "normalization_exceptions.json")
    checks["normalization_exception_present"] = any(
        row.get("source") == "state_estimation"
        and row.get("month") == "2016-06"
        and "2016-06-03T17:20:00" in row.get("timestamps", [])
        for row in exception_payload.get("exceptions", [])
    )

    readme = (RELEASE_ROOT / "README.md").read_text(encoding="utf-8")
    source_license = (RELEASE_ROOT / "SOURCE_LICENSE.md").read_text(encoding="utf-8")
    checks["non_endorsement_statement_present"] = (
        "not an official KPX distribution channel" in readme
    )
    checks["official_permission_text_present"] = (
        "이용허락범위 제한 없음" in source_license
    )

    passed = all(checks.values()) and not problems
    audit = {
        "release": "v1",
        "status": "PASS" if passed else "FAIL",
        "hash_validation_performed": not args.skip_hash,
        "checks": checks,
        "problems": problems,
        "observed": {
            "parquet_files": len(parquet_names),
            "parquet_size_bytes": total_size,
            "rows": total_rows,
            "per_source_files": per_source_files,
            "auxiliary_files": sorted(actual_names - parquet_names),
        },
    }
    out = ROOT / "data" / "audits" / "release_v1_qa.json"
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
