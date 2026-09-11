from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V4_ROOT = ROOT / "data" / "release" / "v4"
DATA_QA = ROOT / "data" / "audits" / "unified_v2_data_qa.json"
OUT = ROOT / "data" / "audits" / "release_v4_qa.json"

PARQUET = "south_korea_power_grid_5min.parquet"
CSV = "south_korea_power_grid_5min.csv"
EXPECTED_RESOURCES = {
    PARQUET,
    CSV,
    "missing_source_months.csv",
    "missingness_summary.csv",
    "release_manifest.json",
}
EXPECTED_PACKAGE_FILES = EXPECTED_RESOURCES | {
    "dataset-metadata.json",
    "dataset-cover-image.png",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def main() -> int:
    qa = load_json(DATA_QA)
    metadata = load_json(V4_ROOT / "dataset-metadata.json")
    manifest = load_json(V4_ROOT / "release_manifest.json")
    actual_files = {path.name for path in V4_ROOT.iterdir() if path.is_file()}
    resources = metadata.get("resources") or []
    by_path = {str(item.get("path")): item for item in resources}

    checks = {
        "unified_data_qa_pass": qa.get("status") == "PASS",
        "package_filename_set_exact": actual_files == EXPECTED_PACKAGE_FILES,
        "resource_paths_exact": set(by_path) == EXPECTED_RESOURCES,
        "manifest_rows_exact": manifest.get("rows") == 1_008_249_180,
        "manifest_release_code_is_current_head": manifest.get("release_code_commit")
        == git_head(),
        "parquet_size_exact": (V4_ROOT / PARQUET).stat().st_size
        == int(qa["observed"]["parquet"]["bytes"]),
        "csv_size_exact": (V4_ROOT / CSV).stat().st_size
        == int(qa["observed"]["csv"]["bytes"]),
        "manifest_parquet_hash_expected": manifest.get("files", {})
        .get("parquet", {})
        .get("sha256")
        == qa.get("observed", {}).get("parquet", {}).get("sha256"),
        "manifest_csv_hash_expected": manifest.get("files", {})
        .get("csv", {})
        .get("sha256")
        == qa.get("observed", {}).get("csv", {}).get("sha256"),
        "metadata_id_expected": metadata.get("id")
        == "taeyangg4/south-korea-power-grid-5-minute",
        "metadata_subtitle_valid": 20 <= len(metadata.get("subtitle", "")) <= 80,
        "metadata_description_present": len(metadata.get("description", "")) >= 1000,
        "all_resource_descriptions_present": all(
            str(item.get("description") or "").strip() for item in resources
        ),
        "main_schemas_exact": all(
            [field.get("name") for field in by_path[name]["schema"]["fields"]]
            == ["timestamp", "source", "generator_id", "value_mw"]
            for name in (PARQUET, CSV)
        ),
        "main_column_descriptions_complete": all(
            all(str(field.get("description") or "").strip() for field in by_path[name]["schema"]["fields"])
            for name in (PARQUET, CSV)
        ),
    }
    passed = all(checks.values())
    report = {
        "release": "v4-parquet-csv",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "observed": {
            "package_files": len(actual_files),
            "upload_resources": len(resources),
            "rows": qa["observed"]["rows"],
            "parquet_bytes": qa["observed"]["parquet"]["bytes"],
            "csv_bytes": qa["observed"]["csv"]["bytes"],
            "total_data_bytes": int(qa["observed"]["parquet"]["bytes"])
            + int(qa["observed"]["csv"]["bytes"]),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
