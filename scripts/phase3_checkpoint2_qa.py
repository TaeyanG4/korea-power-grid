from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("demand", "dispatch", "state_estimation")
EXTENSION_START = "2021-08"
EXTENSION_END = "2023-07"
FULL_START = "2021-08"
FULL_END = "2026-07"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def month_expected(month: str) -> pd.DatetimeIndex:
    start = pd.Timestamp(f"{month}-01 00:00:00")
    end = start + pd.offsets.MonthBegin(1)
    return pd.date_range(start, end, freq="5min", inclusive="left")


def expected_months(start: str, end: str) -> list[str]:
    return [str(period) for period in pd.period_range(start=start, end=end, freq="M")]


def processed_root_for_month(month: str) -> Path:
    if EXTENSION_START <= month <= EXTENSION_END:
        return ROOT / "data" / "processed" / "checkpoint_5y_extension"
    return ROOT / "data" / "processed" / "checkpoint_3y"


def parquet_missing(source: str, month: str) -> pd.DatetimeIndex:
    year, mon = month.split("-")
    path = (
        processed_root_for_month(month)
        / source
        / f"year={year}"
        / f"month={mon}"
        / "data.parquet"
    )
    timestamps = pd.DatetimeIndex(
        pd.read_parquet(path, columns=["timestamp"])["timestamp"].dropna().unique()
    ).sort_values()
    return month_expected(month).difference(timestamps)


def longest_contiguous_run(values: pd.DatetimeIndex) -> dict | None:
    if values.empty:
        return None

    step = pd.Timedelta(minutes=5)
    best_start = run_start = values[0]
    best_end = run_end = values[0]
    best_size = run_size = 1

    for value in values[1:]:
        if value - run_end == step:
            run_end = value
            run_size += 1
        else:
            if run_size > best_size:
                best_start, best_end, best_size = run_start, run_end, run_size
            run_start = run_end = value
            run_size = 1

    if run_size > best_size:
        best_start, best_end, best_size = run_start, run_end, run_size

    return {
        "start": best_start.isoformat(),
        "end": best_end.isoformat(),
        "timestamps": best_size,
    }


def manifest_months(manifests: list[dict], source: str) -> list[str]:
    return sorted(str(row["month"]) for row in manifests if row["source"] == source)


def main() -> int:
    download_qa = load_json(
        ROOT / "data" / "audits" / "checkpoint_2021-08_2023-07_qa.json"
    )
    extension_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2021-08_2023-07.json"
    )
    recent_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2023-08_2026-07.json"
    )
    checkpoint1 = load_json(
        ROOT / "data" / "audits" / "phase3_checkpoint1_summary.json"
    )
    extension_summary = load_json(
        ROOT / "data" / "processed" / "checkpoint_5y_extension" / "summary.json"
    )

    extension_manifest_paths = sorted(
        (ROOT / "data" / "processed" / "checkpoint_5y_extension").rglob(
            "manifest.json"
        )
    )
    recent_manifest_paths = sorted(
        (ROOT / "data" / "processed" / "checkpoint_3y").rglob("manifest.json")
    )
    extension_manifests = [load_json(path) for path in extension_manifest_paths]
    recent_manifests = [load_json(path) for path in recent_manifest_paths]
    all_manifests = extension_manifests + recent_manifests

    extension_status = Counter(str(row.get("status")) for row in extension_manifests)
    extension_parse_failures = sum(
        int(row["timestamp_parse_failure_count"]) for row in extension_manifests
    )
    extension_remaining_duplicates = sum(
        int(row["remaining_candidate_key_duplicate_rows"])
        for row in extension_manifests
    )
    extension_dedup_removed = sum(
        int(row["exact_duplicate_rows_removed"]) for row in extension_manifests
    )

    full_parse_failures = sum(
        int(row["timestamp_parse_failure_count"]) for row in all_manifests
    )
    full_remaining_duplicates = sum(
        int(row["remaining_candidate_key_duplicate_rows"]) for row in all_manifests
    )
    full_dedup_removed = sum(
        int(row["exact_duplicate_rows_removed"]) for row in all_manifests
    )

    expected_full_months = expected_months(FULL_START, FULL_END)
    per_source_month_coverage = {
        source: manifest_months(all_manifests, source) for source in SOURCES
    }

    combined_content_details = (
        list(extension_content_qa["details"]) + list(recent_content_qa["details"])
    )
    source_missingness: dict[str, dict] = {}
    key_gap_observations: dict[str, dict] = {}

    for source in SOURCES:
        rows = [row for row in combined_content_details if row["source"] == source]
        rows = sorted(rows, key=lambda row: row["month"])
        max_row = max(rows, key=lambda row: int(row["missing_timestamp_count"]))
        max_month = str(max_row["month"])
        max_missing = parquet_missing(source, max_month)

        source_missingness[source] = {
            "months": len(rows),
            "months_with_missing": sum(
                1 for row in rows if int(row["missing_timestamp_count"]) > 0
            ),
            "missing_timestamps": sum(
                int(row["missing_timestamp_count"]) for row in rows
            ),
            "max_monthly_missing": int(max_row["missing_timestamp_count"]),
            "max_missing_month": max_month,
        }
        key_gap_observations[source] = {
            "month": max_month,
            "missing_timestamp_count": len(max_missing),
            "longest_contiguous_gap": longest_contiguous_run(max_missing),
        }

    hard_checks = {
        "checkpoint1_passed": checkpoint1.get("status") == "PASS_WITH_OBSERVATIONS",
        "extension_download_records_72": int(download_qa["manifest_records"]) == 72,
        "extension_download_problem_count_zero": int(download_qa["problem_count"]) == 0,
        "extension_download_part_files_zero": int(download_qa["part_file_count"]) == 0,
        "extension_content_qa_records_72": int(extension_content_qa["records"]) == 72,
        "extension_processed_summary_records_72": int(extension_summary["records"]) == 72,
        "extension_processed_manifest_records_72": len(extension_manifests) == 72,
        "extension_processed_all_success": extension_status == Counter({"success": 72}),
        "extension_timestamp_parse_failures_zero": extension_parse_failures == 0,
        "extension_remaining_candidate_duplicates_zero": (
            extension_remaining_duplicates == 0
        ),
        "combined_manifest_records_180": len(all_manifests) == 180,
        "combined_timestamp_parse_failures_zero": full_parse_failures == 0,
        "combined_remaining_candidate_duplicates_zero": full_remaining_duplicates == 0,
        "combined_exact_month_coverage": all(
            per_source_month_coverage[source] == expected_full_months for source in SOURCES
        ),
    }
    passed = all(hard_checks.values())

    report = {
        "phase": "Phase 3",
        "checkpoint": "Checkpoint 2",
        "period": {"start": FULL_START, "end": FULL_END, "months": 60},
        "extension_period": {
            "start": EXTENSION_START,
            "end": EXTENSION_END,
            "months": 24,
        },
        "status": "PASS_WITH_OBSERVATIONS" if passed else "FAIL",
        "hard_checks": hard_checks,
        "downloads": {
            "extension_records": int(download_qa["manifest_records"]),
            "problem_count": int(download_qa["problem_count"]),
            "part_file_count": int(download_qa["part_file_count"]),
            "total_bytes": int(download_qa["total_bytes"]),
        },
        "processed_extension": {
            "records": len(extension_manifests),
            "status_counts": dict(extension_status),
            "input_rows": int(extension_summary["input_rows"]),
            "exact_duplicate_rows_removed": extension_dedup_removed,
            "output_rows": int(extension_summary["output_rows"]),
            "parquet_size_bytes": int(extension_summary["parquet_size_bytes"]),
            "timestamp_parse_failure_count": extension_parse_failures,
            "remaining_candidate_key_duplicate_rows": extension_remaining_duplicates,
        },
        "logical_five_year_dataset": {
            "source_month_records": len(all_manifests),
            "expected_source_month_records": 180,
            "per_source_months": {
                source: len(per_source_month_coverage[source]) for source in SOURCES
            },
            "timestamp_parse_failure_count": full_parse_failures,
            "exact_duplicate_rows_removed": full_dedup_removed,
            "remaining_candidate_key_duplicate_rows": full_remaining_duplicates,
            "roots": [
                "data/processed/checkpoint_5y_extension",
                "data/processed/checkpoint_3y",
            ],
        },
        "source_level_missingness": source_missingness,
        "key_gap_observations": key_gap_observations,
    }

    out = ROOT / "data" / "audits" / "phase3_checkpoint2_summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
