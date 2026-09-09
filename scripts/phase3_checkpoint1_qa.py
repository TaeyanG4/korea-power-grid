from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("demand", "dispatch", "state_estimation")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def month_expected(month: str) -> pd.DatetimeIndex:
    start = pd.Timestamp(f"{month}-01 00:00:00")
    end = start + pd.offsets.MonthBegin(1)
    return pd.date_range(start, end, freq="5min", inclusive="left")


def parquet_missing(source: str, month: str) -> pd.DatetimeIndex:
    year, mon = month.split("-")
    path = (
        ROOT
        / "data"
        / "processed"
        / "checkpoint_3y"
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

    best_start = values[0]
    best_end = values[0]
    best_size = 1
    run_start = values[0]
    run_end = values[0]
    run_size = 1
    step = pd.Timedelta(minutes=5)

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


def main() -> int:
    download_qa = load_json(
        ROOT / "data" / "audits" / "checkpoint_2023-08_2026-07_qa.json"
    )
    content_qa = load_json(
        ROOT / "data" / "audits" / "content_qa_2023-08_2026-07.json"
    )
    processed_summary = load_json(
        ROOT / "data" / "processed" / "checkpoint_3y" / "summary.json"
    )

    manifest_paths = sorted(
        (ROOT / "data" / "processed" / "checkpoint_3y").rglob("manifest.json")
    )
    processed_manifests = [load_json(path) for path in manifest_paths]

    processed_status = Counter(str(row.get("status")) for row in processed_manifests)
    processed_parse_failures = sum(
        int(row["timestamp_parse_failure_count"]) for row in processed_manifests
    )
    processed_remaining_duplicates = sum(
        int(row["remaining_candidate_key_duplicate_rows"])
        for row in processed_manifests
    )
    processed_dedup_removed = sum(
        int(row["exact_duplicate_rows_removed"]) for row in processed_manifests
    )

    missingness: dict[str, dict] = {}
    for source in SOURCES:
        rows = [row for row in content_qa["details"] if row["source"] == source]
        missingness[source] = {
            "months": len(rows),
            "months_with_missing": sum(
                1 for row in rows if int(row["missing_timestamp_count"]) > 0
            ),
            "missing_timestamps": sum(
                int(row["missing_timestamp_count"]) for row in rows
            ),
            "max_monthly_missing": max(
                (int(row["missing_timestamp_count"]) for row in rows), default=0
            ),
        }

    state_may_missing = parquet_missing("state_estimation", "2026-05")
    june_missing = {
        source: parquet_missing(source, "2026-06") for source in SOURCES
    }
    june_shared = sorted(
        set(june_missing["demand"])
        & set(june_missing["dispatch"])
        & set(june_missing["state_estimation"])
    )

    source_index = load_json(ROOT / "data" / "manifests" / "source_index.json")
    extension_counts = {
        source: sum(
            1
            for month in source_index["sources"][source]
            if "2021-08" <= month <= "2023-07"
        )
        for source in SOURCES
    }

    hard_checks = {
        "download_records_108": int(download_qa["manifest_records"]) == 108,
        "download_problem_count_zero": int(download_qa["problem_count"]) == 0,
        "download_part_files_zero": int(download_qa["part_file_count"]) == 0,
        "processed_summary_records_108": int(processed_summary["records"]) == 108,
        "processed_manifest_records_108": len(processed_manifests) == 108,
        "processed_all_success": processed_status == Counter({"success": 108}),
        "processed_timestamp_parse_failures_zero": processed_parse_failures == 0,
        "processed_remaining_candidate_duplicates_zero": (
            processed_remaining_duplicates == 0
        ),
        "content_qa_records_108": int(content_qa["records"]) == 108,
        "extension_plan_records_72": sum(extension_counts.values()) == 72,
    }
    passed = all(hard_checks.values())

    report = {
        "phase": "Phase 3",
        "checkpoint": "Checkpoint 1",
        "period": {"start": "2023-08", "end": "2026-07", "months": 36},
        "status": "PASS_WITH_OBSERVATIONS" if passed else "FAIL",
        "hard_checks": hard_checks,
        "downloads": {
            "records": int(download_qa["manifest_records"]),
            "problem_count": int(download_qa["problem_count"]),
            "part_file_count": int(download_qa["part_file_count"]),
            "total_bytes": int(download_qa["total_bytes"]),
        },
        "processed": {
            "records": len(processed_manifests),
            "status_counts": dict(processed_status),
            "input_rows": int(processed_summary["input_rows"]),
            "exact_duplicate_rows_removed": processed_dedup_removed,
            "output_rows": int(processed_summary["output_rows"]),
            "parquet_size_bytes": int(processed_summary["parquet_size_bytes"]),
            "timestamp_parse_failure_count": processed_parse_failures,
            "remaining_candidate_key_duplicate_rows": processed_remaining_duplicates,
        },
        "source_level_missingness": missingness,
        "key_gap_observations": {
            "state_estimation_2026_05": {
                "missing_timestamp_count": len(state_may_missing),
                "longest_contiguous_gap": longest_contiguous_run(state_may_missing),
            },
            "shared_2026_06": {
                "per_source_missing_counts": {
                    source: len(values) for source, values in june_missing.items()
                },
                "shared_missing_timestamps": [value.isoformat() for value in june_shared],
            },
        },
        "next_checkpoint": {
            "target_window": "2021-08 through 2026-07",
            "extension_only_start": "2021-08",
            "extension_only_end": "2023-07",
            "extension_records": sum(extension_counts.values()),
            "extension_per_source": extension_counts,
            "decision": "GO" if passed else "HOLD",
        },
    }

    out = ROOT / "data" / "audits" / "phase3_checkpoint1_summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
