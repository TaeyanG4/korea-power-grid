from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv


ROOT = Path(__file__).resolve().parents[1]
V4_ROOT = ROOT / "data" / "release" / "v4"
DATA_QA = ROOT / "data" / "audits" / "unified_v2_data_qa.json"
OUT = ROOT / "data" / "audits" / "release_v4_qa.json"

PARQUET = "south_korea_power_grid_5min.parquet"
CSV = "south_korea_power_grid_5min_2026_07.csv"
EXPECTED_CSV_ROWS = 10_060_444
EXPECTED_CSV_SOURCE_ROWS = {
    "demand": 8_928,
    "dispatch": 4_679_698,
    "state_estimation": 5_371_818,
}
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


def git_commit_exists(commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def git_commit_is_ancestor(commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    qa = load_json(DATA_QA)
    metadata = load_json(V4_ROOT / "dataset-metadata.json")
    manifest = load_json(V4_ROOT / "release_manifest.json")
    actual_files = {path.name for path in V4_ROOT.iterdir() if path.is_file()}
    resources = metadata.get("resources") or []
    by_path = {str(item.get("path")): item for item in resources}
    release_commit = str(manifest.get("release_code_commit") or "")

    csv_rows = 0
    csv_source_rows = {key: 0 for key in EXPECTED_CSV_SOURCE_ROWS}
    csv_reader = pacsv.open_csv(
        V4_ROOT / CSV,
        convert_options=pacsv.ConvertOptions(
            column_types={
                "timestamp": pa.string(),
                "source": pa.string(),
                "generator_id": pa.string(),
                "value_mw": pa.float64(),
            }
        ),
    )
    for batch in csv_reader:
        csv_rows += batch.num_rows
        counts = pc.value_counts(batch.column(1))
        for item in counts.to_pylist():
            csv_source_rows[str(item["values"])] += int(item["counts"])

    checks = {
        "unified_data_qa_pass": qa.get("status") == "PASS",
        "package_filename_set_exact": actual_files == EXPECTED_PACKAGE_FILES,
        "resource_paths_exact": set(by_path) == EXPECTED_RESOURCES,
        "manifest_rows_exact": manifest.get("rows") == 1_008_249_180,
        "manifest_release_code_commit_exists": bool(release_commit)
        and git_commit_exists(release_commit),
        "manifest_release_code_is_ancestor_of_head": bool(release_commit)
        and git_commit_is_ancestor(release_commit),
        "parquet_size_exact": (V4_ROOT / PARQUET).stat().st_size
        == int(qa["observed"]["parquet"]["bytes"]),
        "csv_sample_rows_exact": csv_rows == EXPECTED_CSV_ROWS,
        "csv_sample_source_rows_exact": csv_source_rows == EXPECTED_CSV_SOURCE_ROWS,
        "manifest_parquet_hash_expected": manifest.get("files", {})
        .get("parquet", {})
        .get("sha256")
        == qa.get("observed", {}).get("parquet", {}).get("sha256"),
        "manifest_csv_sample_rows_exact": manifest.get("files", {})
        .get("csv_sample", {})
        .get("rows")
        == EXPECTED_CSV_ROWS,
        "manifest_csv_sample_size_exact": manifest.get("files", {})
        .get("csv_sample", {})
        .get("bytes")
        == (V4_ROOT / CSV).stat().st_size,
        "manifest_csv_sample_hash_exact": manifest.get("files", {})
        .get("csv_sample", {})
        .get("sha256")
        == sha256(V4_ROOT / CSV),
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
        "release": "v4-parquet-plus-july-csv",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "observed": {
            "package_files": len(actual_files),
            "upload_resources": len(resources),
            "rows": qa["observed"]["rows"],
            "parquet_bytes": qa["observed"]["parquet"]["bytes"],
            "csv_sample_rows": csv_rows,
            "csv_sample_source_rows": csv_source_rows,
            "csv_sample_bytes": (V4_ROOT / CSV).stat().st_size,
            "total_data_bytes": int(qa["observed"]["parquet"]["bytes"])
            + (V4_ROOT / CSV).stat().st_size,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
