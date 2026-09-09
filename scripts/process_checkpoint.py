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
