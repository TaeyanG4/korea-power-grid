from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from pilot_audit import normalize, read_source

ROOT = Path(__file__).resolve().parents[1]


def expected(month: str) -> pd.DatetimeIndex:
    start = pd.Timestamp(f"{month}-01 00:00:00")
    end = start + pd.offsets.MonthBegin(1) - pd.Timedelta(minutes=5)
    return pd.date_range(start, end, freq="5min")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    months = sorted(
        p.name for p in (ROOT / "data/raw/demand").iterdir()
        if p.is_dir() and args.start <= p.name <= args.end
    )
    sources = ("demand", "dispatch", "state_estimation")
    details = []
    signatures = {s: defaultdict(list) for s in sources}
    total = len(months) * len(sources)
    n = 0

    for month in months:
        exp = expected(month)
        exp_set = set(exp.to_pydatetime())
        for source in sources:
            n += 1
            print(f"[{n}/{total}] {month} {source}", flush=True)
            path = ROOT / "data/raw" / source / month / f"{source}_{month.replace('-', '_')}.zip"
            raw, physical = read_source(source, path)
            canonical, schema = normalize(source, raw)
            ts = canonical["timestamp"]
            valid = pd.DatetimeIndex(ts.dropna().unique()).sort_values()
            valid_set = set(valid.to_pydatetime())
            missing = sorted(exp_set - valid_set)
            outside = sorted(valid_set - exp_set)
            duplicate_rows = int(canonical.duplicated(schema["candidate_grain"], keep=False).sum())
            sig = {
                "columns": schema["original_columns"],
                "physical_format": physical["physical_format"],
                "encoding": physical.get("encoding_used_for_full_parse"),
                "reader": physical.get("reader"),
            }
            sig_key = json.dumps(sig, ensure_ascii=False, sort_keys=True)
            signatures[source][sig_key].append(month)
            details.append({
                "source": source,
                "month": month,
                "row_count": int(len(canonical)),
                "schema": sig,
                "timestamp_parse_failure_count": int(ts.isna().sum()),
                "unique_timestamp_count": int(len(valid)),
                "expected_timestamp_count": int(len(exp)),
                "missing_timestamp_count": len(missing),
                "missing_examples": [x.isoformat() for x in missing[:20]],
                "outside_timestamp_count": len(outside),
                "outside_examples": [x.isoformat() for x in outside[:20]],
                "duplicate_candidate_key_row_count": duplicate_rows,
            })
            del raw, canonical

    anomalies = [d for d in details if d["timestamp_parse_failure_count"] or d["missing_timestamp_count"] or d["outside_timestamp_count"] or d["duplicate_candidate_key_row_count"]]
    summary = {
        "start": args.start,
        "end": args.end,
        "months": len(months),
        "records": len(details),
        "schema_signatures": {
            s: [{"signature": json.loads(k), "months": v} for k, v in groups.items()]
            for s, groups in signatures.items()
        },
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "details": details,
    }
    out = ROOT / "data/audits" / f"content_qa_{args.start}_{args.end}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "months": len(months),
        "records": len(details),
        "schema_signature_counts": {s: len(v) for s, v in signatures.items()},
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
