from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / "data" / "release" / "v2"
DATA_QA = ROOT / "data" / "audits" / "unified_v2_data_qa.json"
OUT = ROOT / "data" / "audits" / "release_v2_qa.json"

EXPECTED_RESOURCE_PATHS = {
    "south_korea_power_grid_5min.parquet",
    "south_korea_power_grid_5min.csv",
    "README.md",
    "DATA_DICTIONARY.md",
    "SOURCE_LICENSE.md",
    "missing_source_months.csv",
    "missingness_summary.csv",
    "normalization_exceptions.json",
    "release_manifest.json",
}
EXPECTED_PACKAGE_FILES = EXPECTED_RESOURCE_PATHS | {
    "dataset-metadata.json",
    "dataset-cover-image.png",
}
EXPECTED_COLUMNS_BY_FILE = {
    "south_korea_power_grid_5min.parquet": [
        "timestamp",
        "source",
        "generator_id",
        "value_mw",
    ],
    "south_korea_power_grid_5min.csv": [
        "timestamp",
        "source",
        "generator_id",
        "value_mw",
    ],
    "missing_source_months.csv": [
        "source",
        "month",
        "evidence",
        "source_article_url",
    ],
    "missingness_summary.csv": [
        "source",
        "months",
        "months_with_missing",
        "missing_timestamps",
        "normalization_exception_timestamps_removed",
        "max_monthly_missing",
        "max_missing_month",
    ],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    data_qa = load_json(DATA_QA)
    metadata = json.loads(
        (V2_ROOT / "dataset-metadata.json").read_text(encoding="ascii")
    )
    manifest = load_json(V2_ROOT / "release_manifest.json")
    resources = metadata.get("resources", [])
    by_path = {str(item.get("path")): item for item in resources}
    actual_files = {path.name for path in V2_ROOT.iterdir() if path.is_file()}

    tabular_column_metadata_ok = True
    described_columns = 0
    expected_column_count = sum(len(names) for names in EXPECTED_COLUMNS_BY_FILE.values())
    for name, expected_columns in EXPECTED_COLUMNS_BY_FILE.items():
        resource = by_path.get(name, {})
        fields = resource.get("schema", {}).get("fields", [])
        if [field.get("name") for field in fields] != expected_columns:
            tabular_column_metadata_ok = False
        if not all(
            str(field.get("description") or field.get("title") or "").strip()
            for field in fields
        ):
            tabular_column_metadata_ok = False
        described_columns += sum(
            bool(str(field.get("description") or field.get("title") or "").strip())
            for field in fields
        )

    checks = {
        "unified_data_qa_pass": data_qa.get("status") == "PASS",
        "manifest_rows_exact": manifest.get("rows") == 1_008_249_180,
        "manifest_parquet_hash_matches": manifest.get("files", {})
        .get("parquet", {})
        .get("sha256")
        == data_qa.get("observed", {}).get("parquet", {}).get("sha256"),
        "manifest_csv_hash_matches": manifest.get("files", {})
        .get("csv", {})
        .get("sha256")
        == data_qa.get("observed", {}).get("csv", {}).get("sha256"),
        "package_filename_set_exact": actual_files == EXPECTED_PACKAGE_FILES,
        "metadata_id_expected": metadata.get("id")
        == "taeyangg4/south-korea-power-grid-5-minute",
        "metadata_license_other": metadata.get("licenses") == [{"name": "other"}],
        "metadata_subtitle_valid": 20 <= len(metadata.get("subtitle", "")) <= 80,
        "metadata_description_complete": len(metadata.get("description", "")) >= 1500,
        "metadata_keywords_6": len(metadata.get("keywords", [])) == 6,
        "metadata_update_frequency_monthly": metadata.get("expectedUpdateFrequency")
        == "monthly",
        "metadata_provenance_present": "Korea Power Exchange"
        in metadata.get("userSpecifiedSources", ""),
        "metadata_cover_declared": metadata.get("image") == "dataset-cover-image.png",
        "cover_exists": (V2_ROOT / "dataset-cover-image.png").is_file(),
        "resource_paths_exact": set(by_path) == EXPECTED_RESOURCE_PATHS,
        "all_resource_descriptions_present": all(
            str(item.get("description", "")).strip() for item in resources
        ),
        "all_tabular_column_descriptions_complete": tabular_column_metadata_ok,
        "all_19_tabular_columns_described": described_columns == expected_column_count == 19,
        "parquet_smaller_than_csv": int(
            data_qa["observed"]["parquet"]["bytes"]
        )
        < int(data_qa["observed"]["csv"]["bytes"]),
        "total_data_bytes_below_200gb": (
            int(data_qa["observed"]["parquet"]["bytes"])
            + int(data_qa["observed"]["csv"]["bytes"])
        )
        < 200_000_000_000,
    }

    passed = all(checks.values())
    report = {
        "release": "v2-unified",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "observed": {
            "package_files": len(actual_files),
            "upload_resources": len(resources),
            "data_rows": data_qa["observed"]["rows"],
            "parquet_bytes": data_qa["observed"]["parquet"]["bytes"],
            "csv_bytes": data_qa["observed"]["csv"]["bytes"],
            "total_data_bytes": int(data_qa["observed"]["parquet"]["bytes"])
            + int(data_qa["observed"]["csv"]["bytes"]),
            "resource_paths": sorted(by_path),
            "described_tabular_columns": described_columns,
            "expected_tabular_columns": expected_column_count,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
