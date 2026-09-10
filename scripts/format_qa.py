from __future__ import annotations

import argparse
import codecs
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "scripts").resolve()))

from pilot_audit import (  # noqa: E402
    detect_text_encoding,
    inspect_three_column_text_header,
    select_source_zip_member,
)


SOURCES = ("demand", "dispatch", "state_estimation")
OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
OOXML_MAGIC = b"PK\x03\x04"


def inspect_demand(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict:
    with archive.open(info) as handle:
        probe = handle.read(65536)

    if probe[:8] == OLE_MAGIC:
        return {
            "physical_format": "xls-ole",
            "encoding": None,
            "preamble_rows": 0,
        }
    if probe[:4] == OOXML_MAGIC:
        return {
            "physical_format": "xlsx-ooxml",
            "encoding": None,
            "preamble_rows": 0,
        }

    encoding = detect_text_encoding(probe[:4096])
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    lines = decoder.decode(probe, final=False).splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines[:20])
            if "," in line
            and ("시간" in line or line.lstrip("\ufeff").upper().startswith("TIME,"))
        ),
        None,
    )
    if header_index is None:
        raise RuntimeError(
            f"demand: header not found in first 20 lines; encoding={encoding}"
        )
    return {
        "physical_format": "comma-delimited text",
        "encoding": encoding,
        "preamble_rows": header_index,
    }


def inspect_three_column_source(
    source: str,
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    label: str,
) -> dict:
    with archive.open(info) as handle:
        magic = handle.read(8)

    if magic[:8] == OLE_MAGIC:
        raise RuntimeError(f"{source}: unsupported OLE Excel member")

    if magic[:4] == OOXML_MAGIC:
        if source == "dispatch":
            return {
                "physical_format": "xlsx-ooxml",
                "encoding": None,
                "preamble_rows": None,
            }
        raise RuntimeError(f"{source}: unsupported OOXML Excel member")

    with archive.open(info) as handle:
        encoding, columns, preamble_rows = inspect_three_column_text_header(
            source,
            handle,
            label=label,
        )
    return {
        "physical_format": "comma-delimited text",
        "encoding": encoding,
        "preamble_rows": preamble_rows,
        "columns": columns,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lightweight physical-format/header QA without full parsing"
    )
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    details: list[dict] = []
    problems: list[dict] = []
    unavailable: list[dict] = []
    signatures: Counter[str] = Counter()

    months = sorted(
        path.name
        for path in (ROOT / "data" / "raw" / "demand").iterdir()
        if path.is_dir() and args.start <= path.name <= args.end
    )

    for month in months:
        for source in SOURCES:
            manifest_path = (
                ROOT / "data" / "manifests" / "downloads" / source / f"{month}.json"
            )
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("status") == "source_unavailable":
                    unavailable.append(
                        {
                            "source": source,
                            "month": month,
                            "status": "source_unavailable",
                            "evidence": manifest.get("evidence"),
                        }
                    )
                    continue
            path = (
                ROOT
                / "data"
                / "raw"
                / source
                / month
                / f"{source}_{month.replace('-', '_')}.zip"
            )
            try:
                with zipfile.ZipFile(path) as archive:
                    infos = archive.infolist()
                    info, ignored_members = select_source_zip_member(source, archive)
                    if source == "demand":
                        physical = inspect_demand(archive, info)
                    else:
                        physical = inspect_three_column_source(
                            source,
                            archive,
                            info,
                            label=str(path),
                        )

                detail = {
                    "source": source,
                    "month": month,
                    "member_name": info.filename,
                    "member_size_bytes": info.file_size,
                    "outer_zip_member_count": len(infos),
                    "ignored_outer_zip_members": ignored_members,
                    **physical,
                }
                details.append(detail)
                signature = json.dumps(
                    {
                        "source": source,
                        "physical_format": physical["physical_format"],
                        "encoding": physical.get("encoding"),
                        "preamble_rows": physical.get("preamble_rows"),
                        "columns": physical.get("columns"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                signatures[signature] += 1
            except Exception as exc:  # noqa: BLE001
                problems.append(
                    {
                        "source": source,
                        "month": month,
                        "path": str(path.relative_to(ROOT)),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    summary = {
        "start": args.start,
        "end": args.end,
        "months": len(months),
        "records_expected": len(months) * len(SOURCES),
        "records_inspected": len(details),
        "records_accounted": len(details) + len(unavailable),
        "source_unavailable_count": len(unavailable),
        "source_unavailable_records": unavailable,
        "problem_count": len(problems),
        "signature_counts": [
            {"signature": json.loads(signature), "records": count}
            for signature, count in sorted(signatures.items())
        ],
        "problems": problems,
        "details": details,
    }

    out = ROOT / "data" / "audits" / f"format_qa_{args.start}_{args.end}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "months": summary["months"],
                "records_expected": summary["records_expected"],
                "records_inspected": summary["records_inspected"],
                "records_accounted": summary["records_accounted"],
                "source_unavailable_count": summary["source_unavailable_count"],
                "problem_count": summary["problem_count"],
                "signature_counts": summary["signature_counts"],
                "problems": summary["problems"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"WROTE {out}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
