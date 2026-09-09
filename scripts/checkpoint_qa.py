from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import zipfile


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_root = root / "data" / "manifests" / "downloads"
    raw_root = root / "data" / "raw"

    records: list[dict] = []
    problems: list[dict] = []
    status_counts: Counter[str] = Counter()
    per_source_bytes: defaultdict[str, int] = defaultdict(int)
    per_source_records: Counter[str] = Counter()

    selected: list[tuple[Path, dict]] = []
    for manifest_path in sorted(manifest_root.rglob("*.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        month = data.get("month", "")
        if args.start <= month <= args.end:
            selected.append((manifest_path, data))

    for index, (manifest_path, data) in enumerate(selected, 1):
        source = data["source"]
        month = data["month"]
        zip_name = f"{source}_{month.replace('-', '_')}.zip"
        zip_path = raw_root / source / month / zip_name

        status_counts[str(data.get("status"))] += 1
        per_source_records[source] += 1
        record = {
            "source": source,
            "month": month,
            "manifest": str(manifest_path.relative_to(root)),
            "zip": str(zip_path.relative_to(root)),
            "exists": zip_path.exists(),
        }

        if data.get("status") == "source_unavailable":
            record["source_unavailable"] = True
            record["evidence"] = data.get("evidence")
            record["observed_payload_size"] = data.get("observed_payload_size")
            records.append(record)
            continue

        if not zip_path.exists():
            problems.append({**record, "problem": "missing_zip"})
            records.append(record)
            continue

        actual_size = zip_path.stat().st_size
        per_source_bytes[source] += actual_size
        record["actual_size"] = actual_size
        record["manifest_size"] = data.get("file_size")
        if actual_size != data.get("file_size"):
            problems.append({**record, "problem": "size_mismatch"})

        actual_sha = sha256_file(zip_path)
        record["sha256_match"] = actual_sha == data.get("sha256")
        if not record["sha256_match"]:
            problems.append({**record, "problem": "sha256_mismatch"})

        try:
            with zipfile.ZipFile(zip_path) as archive:
                bad_member = archive.testzip()
                member_count = len(archive.infolist())
            record["zip_member_count"] = member_count
            record["zip_crc_ok"] = bad_member is None
            if bad_member is not None:
                problems.append(
                    {**record, "problem": "zip_crc_failure", "bad_member": bad_member}
                )
        except Exception as exc:  # noqa: BLE001
            record["zip_crc_ok"] = False
            problems.append(
                {
                    **record,
                    "problem": "zip_open_failure",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        records.append(record)
        if index % 18 == 0 or index == len(selected):
            print(f"checked {index}/{len(selected)}")

    part_files = sorted(raw_root.rglob("*.part"))
    month_dirs = {
        source_dir.name: len([p for p in source_dir.iterdir() if p.is_dir()])
        for source_dir in raw_root.iterdir()
        if source_dir.is_dir()
    }

    summary = {
        "requested_start": args.start,
        "requested_end": args.end,
        "manifest_records": len(selected),
        "status_counts": dict(status_counts),
        "per_source_records": dict(per_source_records),
        "per_source_bytes": dict(per_source_bytes),
        "total_bytes": sum(per_source_bytes.values()),
        "month_dirs": month_dirs,
        "part_file_count": len(part_files),
        "problem_count": len(problems),
        "problems": problems,
        "source_unavailable_count": sum(
            1 for record in records if record.get("source_unavailable")
        ),
        "source_unavailable_records": [
            record for record in records if record.get("source_unavailable")
        ],
    }

    out_dir = root / "data" / "audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"checkpoint_{args.start}_{args.end}_qa.json"
    out_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"WROTE {out_path}")
    return 0 if not problems and not part_files else 1


if __name__ == "__main__":
    raise SystemExit(main())
