from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "scripts").resolve()))

from pilot_audit import normalize, read_source  # noqa: E402


SOURCES = ("demand", "dispatch", "state_estimation")
NORMALIZATION_EXCEPTIONS_PATH = (
    ROOT / "data" / "manifests" / "normalization_exceptions.json"
)


def month_dirs(start: str, end: str) -> list[str]:
    return sorted(
        p.name
        for p in (ROOT / "data" / "raw" / "demand").iterdir()
        if p.is_dir() and start <= p.name <= end
    )


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def load_normalization_exceptions() -> list[dict]:
    if not NORMALIZATION_EXCEPTIONS_PATH.exists():
        return []
    payload = json.loads(NORMALIZATION_EXCEPTIONS_PATH.read_text(encoding="utf-8"))
    return list(payload.get("exceptions", []))


def apply_normalization_exceptions(
    canonical: pd.DataFrame,
    schema: dict,
    source: str,
    month: str,
    *,
    exceptions: list[dict] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    configured = load_normalization_exceptions() if exceptions is None else exceptions
    applicable = [
        item
        for item in configured
        if item.get("source") == source and item.get("month") == month
    ]
    if not applicable:
        return canonical, []

    out = canonical
    applied: list[dict] = []
    key_cols = list(schema["candidate_grain"])
    value_col = str(schema["value_column"])

    for item in applicable:
        action = item.get("action")
        if action != "drop_ambiguous_duplicate_timestamp":
            raise RuntimeError(
                f"{source} {month}: unsupported normalization exception action {action!r}"
            )

        for raw_timestamp in item.get("timestamps", []):
            timestamp = pd.Timestamp(raw_timestamp)
            mask = out["timestamp"].eq(timestamp)
            selected = out.loc[mask]
            if selected.empty:
                raise RuntimeError(
                    f"{source} {month}: configured ambiguous timestamp {timestamp} is absent"
                )

            groups = selected.groupby(key_cols, dropna=False, sort=False)
            sizes = groups.size()
            if not sizes.eq(2).all():
                raise RuntimeError(
                    f"{source} {month} {timestamp}: expected every candidate key to have "
                    f"exactly two rows, got size counts {sizes.value_counts().to_dict()}"
                )
            if int(selected.duplicated(key_cols, keep=False).sum()) != len(selected):
                raise RuntimeError(
                    f"{source} {month} {timestamp}: not every row participates in a "
                    "candidate-key duplicate"
                )

            conflicting = groups[value_col].nunique(dropna=False).gt(1)
            conflicting_keys = int(conflicting.sum())
            if conflicting_keys == 0:
                raise RuntimeError(
                    f"{source} {month} {timestamp}: exception configured but all duplicate "
                    "candidate keys are exact"
                )

            expected = item.get("evidence", {})
            expected_rows = expected.get("rows_at_timestamp")
            expected_keys = expected.get("unique_candidate_keys")
            expected_conflicts = expected.get("conflicting_candidate_keys")
            if expected_rows is not None and int(expected_rows) != len(selected):
                raise RuntimeError(
                    f"{source} {month} {timestamp}: evidence row count changed "
                    f"({len(selected)} != {expected_rows})"
                )
            if expected_keys is not None and int(expected_keys) != len(sizes):
                raise RuntimeError(
                    f"{source} {month} {timestamp}: evidence candidate-key count changed "
                    f"({len(sizes)} != {expected_keys})"
                )
            if expected_conflicts is not None and int(expected_conflicts) != conflicting_keys:
                raise RuntimeError(
                    f"{source} {month} {timestamp}: evidence conflicting-key count changed "
                    f"({conflicting_keys} != {expected_conflicts})"
                )

            applied.append(
                {
                    "action": action,
                    "timestamp": timestamp.isoformat(),
                    "rows_removed": int(len(selected)),
                    "unique_candidate_keys": int(len(sizes)),
                    "conflicting_candidate_keys": conflicting_keys,
                    "exact_candidate_keys": int(len(sizes) - conflicting_keys),
                    "reason": item.get("reason"),
                    "evidence": expected,
                }
            )
            out = out.loc[~mask].copy()

    return out, applied


def process_one(source: str, month: str, out_root: Path) -> dict:
    input_path = (
        ROOT
        / "data"
        / "raw"
        / source
        / month
        / f"{source}_{month.replace('-', '_')}.zip"
    )
    year, mon = month.split("-")
    out_dir = out_root / source / f"year={year}" / f"month={mon}"
    out_path = out_dir / "data.parquet"
    manifest_path = out_dir / "manifest.json"

    download_manifest_path = (
        ROOT / "data" / "manifests" / "downloads" / source / f"{month}.json"
    )
    if download_manifest_path.exists():
        download_manifest = json.loads(
            download_manifest_path.read_text(encoding="utf-8")
        )
        if download_manifest.get("status") == "source_unavailable":
            out_dir.mkdir(parents=True, exist_ok=True)
            manifest = {
                "source": source,
                "month": month,
                "status": "source_unavailable",
                "input_zip": None,
                "output_parquet": None,
                "source_download_manifest": str(download_manifest_path.relative_to(ROOT)),
                "source_unavailable_evidence": download_manifest.get("evidence"),
                "physical": None,
                "original_columns": None,
                "candidate_grain": None,
                "input_rows": 0,
                "candidate_duplicate_extra_before_exceptions": 0,
                "exact_duplicate_extra_before_exceptions": 0,
                "normalization_exception_rows_removed": 0,
                "normalization_exceptions_applied": [],
                "exact_duplicate_rows_removed": 0,
                "output_rows": 0,
                "remaining_candidate_key_duplicate_rows": 0,
                "timestamp_parse_failure_count": 0,
                "timestamp_min": None,
                "timestamp_max": None,
                "parquet_size_bytes": 0,
                "elapsed_seconds": 0.0,
            }
            atomic_json(manifest_path, manifest)
            return manifest

    if out_path.exists() and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing["status"] = "skipped_existing"
        return existing

    started = time.perf_counter()
    raw, physical = read_source(source, input_path)
    canonical, schema = normalize(source, raw)
    del raw

    input_rows = len(canonical)
    key_cols = schema["candidate_grain"]
    candidate_dup_extra_before_exceptions = int(
        canonical.duplicated(key_cols, keep="first").sum()
    )
    exact_dup_extra_before_exceptions = int(
        canonical.duplicated(keep="first").sum()
    )
    canonical, normalization_exceptions_applied = apply_normalization_exceptions(
        canonical,
        schema,
        source,
        month,
    )
    normalization_exception_rows_removed = sum(
        int(item["rows_removed"]) for item in normalization_exceptions_applied
    )
    candidate_dup_extra = int(canonical.duplicated(key_cols, keep="first").sum())
    exact_dup_extra = int(canonical.duplicated(keep="first").sum())

    if candidate_dup_extra != exact_dup_extra:
        raise RuntimeError(
            f"{source} {month}: found non-exact duplicate candidate keys "
            f"(candidate extra={candidate_dup_extra}, exact extra={exact_dup_extra})"
        )

    if exact_dup_extra:
        canonical = canonical.drop_duplicates(ignore_index=True)

    remaining_key_dups = int(canonical.duplicated(key_cols, keep=False).sum())
    if remaining_key_dups:
        raise RuntimeError(
            f"{source} {month}: candidate-key duplicates remain after exact dedup: "
            f"{remaining_key_dups}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    temp_path = out_path.with_suffix(".parquet.part")
    canonical.to_parquet(temp_path, index=False, compression="zstd", engine="pyarrow")
    os.replace(temp_path, out_path)

    ts = canonical["timestamp"]
    manifest = {
        "source": source,
        "month": month,
        "status": "success",
        "input_zip": str(input_path.relative_to(ROOT)),
        "output_parquet": str(out_path.relative_to(ROOT)),
        "physical": physical,
        "original_columns": schema["original_columns"],
        "candidate_grain": key_cols,
        "input_rows": input_rows,
        "candidate_duplicate_extra_before_exceptions": candidate_dup_extra_before_exceptions,
        "exact_duplicate_extra_before_exceptions": exact_dup_extra_before_exceptions,
        "normalization_exception_rows_removed": normalization_exception_rows_removed,
        "normalization_exceptions_applied": normalization_exceptions_applied,
        "exact_duplicate_rows_removed": exact_dup_extra,
        "output_rows": len(canonical),
        "remaining_candidate_key_duplicate_rows": remaining_key_dups,
        "timestamp_parse_failure_count": int(ts.isna().sum()),
        "timestamp_min": None if ts.dropna().empty else ts.min().isoformat(),
        "timestamp_max": None if ts.dropna().empty else ts.max().isoformat(),
        "parquet_size_bytes": out_path.stat().st_size,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    atomic_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument(
        "--output-root",
        default="data/processed/checkpoint_3y",
        help="Repository-relative processed root",
    )
    args = parser.parse_args()

    out_root = ROOT / args.output_root
    months = month_dirs(args.start, args.end)
    planned = [(month, source) for month in months for source in SOURCES]
    records: list[dict] = []

    for index, (month, source) in enumerate(planned, 1):
        print(f"[{index}/{len(planned)}] {month} {source}", flush=True)
        result = process_one(source, month, out_root)
        records.append(result)
        print(
            f"  rows={result['output_rows']:,} "
            f"dedup={result['exact_duplicate_rows_removed']:,} "
            f"parquet={result['parquet_size_bytes']:,} bytes "
            f"status={result['status']}",
            flush=True,
        )

    summary = {
        "start": args.start,
        "end": args.end,
        "records": len(records),
        "sources": list(SOURCES),
        "months": len(months),
        "input_rows": sum(int(r["input_rows"]) for r in records),
        "normalization_exception_rows_removed": sum(
            int(r.get("normalization_exception_rows_removed", 0)) for r in records
        ),
        "exact_duplicate_rows_removed": sum(
            int(r["exact_duplicate_rows_removed"]) for r in records
        ),
        "output_rows": sum(int(r["output_rows"]) for r in records),
        "parquet_size_bytes": sum(int(r["parquet_size_bytes"]) for r in records),
        "per_source": {
            source: {
                "records": sum(1 for r in records if r["source"] == source),
                "input_rows": sum(
                    int(r["input_rows"]) for r in records if r["source"] == source
                ),
                "normalization_exception_rows_removed": sum(
                    int(r.get("normalization_exception_rows_removed", 0))
                    for r in records
                    if r["source"] == source
                ),
                "exact_duplicate_rows_removed": sum(
                    int(r["exact_duplicate_rows_removed"])
                    for r in records
                    if r["source"] == source
                ),
                "output_rows": sum(
                    int(r["output_rows"]) for r in records if r["source"] == source
                ),
                "parquet_size_bytes": sum(
                    int(r["parquet_size_bytes"])
                    for r in records
                    if r["source"] == source
                ),
            }
            for source in SOURCES
        },
    }
    atomic_json(out_root / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
