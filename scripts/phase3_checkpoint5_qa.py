from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from phase3_checkpoint4_qa import (
    allowed_status_accounting,
    expected_months,
    load_json,
    longest_contiguous_run,
    manifest_months,
    month_expected,
    read_manifests,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("demand", "dispatch", "state_estimation")
EXTENSION_START = "2015-08"
EXTENSION_END = "2016-07"
FULL_START = "2015-08"
FULL_END = "2026-07"
EXPECTED_EXTENSION_RECORDS = 36
EXPECTED_FULL_RECORDS = 396


def processed_root_for_month(month: str) -> Path:
    if EXTENSION_START <= month <= EXTENSION_END:
        return ROOT / "data" / "processed" / "checkpoint_full_extension"
    if "2016-08" <= month <= "2018-07":
        return ROOT / "data" / "processed" / "checkpoint_10y_extension"
    if "2018-08" <= month <= "2021-07":
        return ROOT / "data" / "processed" / "checkpoint_8y_extension"
    if "2021-08" <= month <= "2023-07":
        return ROOT / "data" / "processed" / "checkpoint_5y_extension"
    return ROOT / "data" / "processed" / "checkpoint_3y"


def parquet_missing(source: str, month: str) -> pd.DatetimeIndex:
    year, mon = month.split("-")
    root = processed_root_for_month(month)
    manifest_path = root / source / f"year={year}" / f"month={mon}" / "manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        if manifest.get("status") == "source_unavailable":
            return month_expected(month)

    parquet_path = root / source / f"year={year}" / f"month={mon}" / "data.parquet"
    timestamps = pd.DatetimeIndex(
        pd.read_parquet(parquet_path, columns=["timestamp"])["timestamp"]
        .dropna()
        .unique()
    ).sort_values()
    return month_expected(month).difference(timestamps)


def main() -> int:
    previous_checkpoint = load_json(
        ROOT / "data" / "audits" / "phase3_checkpoint4_summary.json"
    )
    download_qa = load_json(
        ROOT / "data" / "audits" / "checkpoint_2015-08_2016-07_qa.json"
    )
    format_qa = load_json(
        ROOT / "data" / "audits" / "format_qa_2015-08_2016-07.json"
    )
    extension_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2015-08_2016-07.json"
    )
    ten_year_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2016-08_2018-07.json"
    )
    eight_year_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2018-08_2021-07.json"
    )
    five_year_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2021-08_2023-07.json"
    )
    recent_content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2023-08_2026-07.json"
    )
    extension_summary = load_json(
        ROOT / "data" / "processed" / "checkpoint_full_extension" / "summary.json"
    )

    roots = [
        ROOT / "data" / "processed" / "checkpoint_full_extension",
        ROOT / "data" / "processed" / "checkpoint_10y_extension",
        ROOT / "data" / "processed" / "checkpoint_8y_extension",
        ROOT / "data" / "processed" / "checkpoint_5y_extension",
        ROOT / "data" / "processed" / "checkpoint_3y",
    ]
    extension_manifests = read_manifests(roots[0])
    all_manifests: list[dict] = []
    for root in roots:
        all_manifests.extend(read_manifests(root))

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

    content_reports = [
        extension_content_qa,
        ten_year_content_qa,
        eight_year_content_qa,
        five_year_content_qa,
        recent_content_qa,
    ]
    combined_content_details = [
        detail for report in content_reports for detail in report["details"]
    ]

    source_missingness: dict[str, dict] = {}
    key_gap_observations: dict[str, dict] = {}
    for source in SOURCES:
        rows = sorted(
            [row for row in combined_content_details if row["source"] == source],
            key=lambda row: row["month"],
        )
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

    download_unavailable = int(download_qa.get("source_unavailable_count", 0))
    format_unavailable = int(format_qa.get("source_unavailable_count", 0))
    content_unavailable = int(extension_content_qa.get("source_unavailable_count", 0))
    processed_unavailable = int(extension_status["source_unavailable"])
    extension_outside = sum(
        int(row["outside_timestamp_count"]) for row in extension_content_qa["details"]
    )

    hard_checks = {
        "checkpoint4_passed": previous_checkpoint.get("status")
        == "PASS_WITH_OBSERVATIONS",
        "extension_download_records_36": int(download_qa["manifest_records"])
        == EXPECTED_EXTENSION_RECORDS,
        "extension_download_problem_count_zero": int(download_qa["problem_count"]) == 0,
        "extension_download_part_files_zero": int(download_qa["part_file_count"]) == 0,
        "extension_format_qa_records_accounted_36": int(format_qa["records_accounted"])
        == EXPECTED_EXTENSION_RECORDS,
        "extension_format_qa_problem_count_zero": int(format_qa["problem_count"]) == 0,
        "extension_content_qa_records_36": int(extension_content_qa["records"])
        == EXPECTED_EXTENSION_RECORDS,
        "extension_content_outside_timestamp_count_zero": extension_outside == 0,
        "extension_source_unavailable_accounting_consistent": (
            download_unavailable
            == format_unavailable
            == content_unavailable
            == processed_unavailable
        ),
        "extension_processed_summary_records_36": int(extension_summary["records"])
        == EXPECTED_EXTENSION_RECORDS,
        "extension_processed_manifest_records_36": len(extension_manifests)
        == EXPECTED_EXTENSION_RECORDS,
        "extension_processed_status_accounting": allowed_status_accounting(
            extension_status, EXPECTED_EXTENSION_RECORDS
        ),
        "extension_timestamp_parse_failures_zero": extension_parse_failures == 0,
        "extension_remaining_candidate_duplicates_zero": (
            extension_remaining_duplicates == 0
        ),
        "combined_manifest_records_396": len(all_manifests) == EXPECTED_FULL_RECORDS,
        "combined_timestamp_parse_failures_zero": full_parse_failures == 0,
        "combined_remaining_candidate_duplicates_zero": full_remaining_duplicates == 0,
        "combined_exact_month_coverage": all(
            per_source_month_coverage[source] == expected_full_months for source in SOURCES
        ),
    }
    passed = all(hard_checks.values())

    report = {
        "phase": "Phase 3",
        "checkpoint": "Checkpoint 5",
        "period": {"start": FULL_START, "end": FULL_END, "months": 132},
        "extension_period": {
            "start": EXTENSION_START,
            "end": EXTENSION_END,
            "months": 12,
        },
        "status": "PASS_WITH_OBSERVATIONS" if passed else "FAIL",
        "hard_checks": hard_checks,
        "downloads": {
            "extension_records": int(download_qa["manifest_records"]),
            "problem_count": int(download_qa["problem_count"]),
            "part_file_count": int(download_qa["part_file_count"]),
            "total_bytes": int(download_qa["total_bytes"]),
            "source_unavailable_count": download_unavailable,
            "source_unavailable_records": download_qa.get(
                "source_unavailable_records", []
            ),
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
            "source_unavailable_records": processed_unavailable,
        },
        "logical_full_history_dataset": {
            "source_month_records": len(all_manifests),
            "expected_source_month_records": EXPECTED_FULL_RECORDS,
            "per_source_months": {
                source: len(per_source_month_coverage[source]) for source in SOURCES
            },
            "timestamp_parse_failure_count": full_parse_failures,
            "exact_duplicate_rows_removed": full_dedup_removed,
            "remaining_candidate_key_duplicate_rows": full_remaining_duplicates,
            "source_unavailable_records": sum(
                1 for row in all_manifests if row.get("status") == "source_unavailable"
            ),
            "roots": [str(root.relative_to(ROOT)) for root in roots],
        },
        "source_level_missingness": source_missingness,
        "key_gap_observations": key_gap_observations,
    }

    out = ROOT / "data" / "audits" / "phase3_checkpoint5_summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
