from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "data" / "release" / "v1"
FINAL_AUDIT = ROOT / "data" / "audits" / "phase3_checkpoint5_summary.json"
LICENSE_AUDIT = ROOT / "data" / "audits" / "release_license_check_2026-09-10.json"
EXCEPTIONS = ROOT / "data" / "manifests" / "normalization_exceptions.json"

PROCESSED_ROOTS = (
    ROOT / "data" / "processed" / "checkpoint_full_extension",
    ROOT / "data" / "processed" / "checkpoint_10y_extension",
    ROOT / "data" / "processed" / "checkpoint_8y_extension",
    ROOT / "data" / "processed" / "checkpoint_5y_extension",
    ROOT / "data" / "processed" / "checkpoint_3y",
)

SOURCE_INFO = {
    "demand": {
        "label": "5-minute demand forecast",
        "kpx_board": "https://www.kpx.or.kr/board.es?mid=a10109020700&bid=0065",
        "data_go_kr": "https://www.data.go.kr/data/15051432/fileData.do",
        "schema": ["timestamp", "demand_forecast_mw"],
    },
    "dispatch": {
        "label": "generator-level 5-minute economic dispatch",
        "kpx_board": "https://www.kpx.or.kr/board.es?mid=a10109020200&bid=0070",
        "data_go_kr": "https://www.data.go.kr/data/15051425/fileData.do",
        "schema": ["timestamp", "generator_id", "dispatch_mw"],
    },
    "state_estimation": {
        "label": "generator-level 5-minute state estimation",
        "kpx_board": "https://www.kpx.or.kr/board.es?mid=a10109020400&bid=0068",
        "data_go_kr": "https://www.data.go.kr/data/15051426/fileData.do",
        "schema": ["timestamp", "generator_id", "estimated_generation_mw"],
    },
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def processed_manifests() -> list[tuple[Path, dict]]:
    rows: list[tuple[Path, dict]] = []
    for processed_root in PROCESSED_ROOTS:
        for path in processed_root.rglob("manifest.json"):
            rows.append((path, load_json(path)))
    return sorted(rows, key=lambda item: (item[1]["month"], item[1]["source"]))


def ensure_hardlink(source: Path, target: Path) -> None:
    if target.exists():
        if not os.path.samefile(source, target):
            raise RuntimeError(
                f"Release target already exists but is not the expected hard link: {target}"
            )
        return
    os.link(source, target)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def release_readme(final_audit: dict, license_audit: dict) -> str:
    logical = final_audit["logical_full_history_dataset"]
    return f"""# South Korea Power Grid 5-Minute Data (2015-2026)

Normalized monthly power-grid operating data from the Korea Power Exchange
(KPX), covering the observed board history from **2015-08 through 2026-07**.

This package is a cleaned/normalized derivative prepared from official KPX
source attachments. **It is not an official KPX distribution channel and does
not imply KPX endorsement.**

## Contents

- demand forecast: `demand_YYYY_MM.parquet`
- generator economic dispatch: `dispatch_YYYY_MM.parquet`
- generator state estimation: `state_estimation_YYYY_MM.parquet`
- lineage and integrity metadata: `release_manifest.json`
- known unavailable source months: `missing_source_months.csv`
- source-level missingness summary: `missingness_summary.csv`
- normalization exception record: `normalization_exceptions.json`

Logical coverage is {logical['source_month_records']} source-month records
(132 months × 3 sources). Eight official source-month attachments are currently
unavailable and therefore have no fabricated Parquet placeholder.

## Important data notes

- timestamps are stored as **naive timestamps**; no timezone is asserted because
  the source files do not provide verified timezone metadata
- generator identifiers are retained in source-native form; no guessed mapping
  between dispatch and state-estimation identifier systems is applied
- missing timestamps are not silently imputed
- exact duplicate rows are removed only when candidate-key duplicates are exact
- one ambiguous source timestamp, `state_estimation 2016-06-03 17:20`, is
  excluded rather than arbitrarily choosing between conflicting duplicate rows;
  see `normalization_exceptions.json`

## Measured release size

- output rows: {1_008_249_180:,}
- Parquet bytes: {2_661_216_619:,}
- timestamp parse failures after normalization: 0
- remaining candidate-key duplicates: 0

## Source and permission

Provider: **Korea Power Exchange (한국전력거래소, KPX)**.

The three official data.go.kr records were re-checked at
`{license_audit['checked_at_asia_seoul']}` and each reported `무료` and
`이용허락범위 제한 없음`. Kaggle metadata therefore uses the `other` category
and this package states the official source condition rather than assigning a
different Creative Commons license.

See `SOURCE_LICENSE.md` and `release_manifest.json` for the official URLs and
verification metadata.
"""


def data_dictionary() -> str:
    return """# Data Dictionary

All files are ZSTD-compressed Parquet and are partitioned into one flat file per
available source-month.

## demand_YYYY_MM.parquet

| Column | Meaning |
|---|---|
| `timestamp` | Source timestamp, stored as a naive datetime |
| `demand_forecast_mw` | Five-minute electricity demand forecast in MW |

Candidate grain: `timestamp`.

## dispatch_YYYY_MM.parquet

| Column | Meaning |
|---|---|
| `timestamp` | Source timestamp, stored as a naive datetime |
| `generator_id` | Source-native generator CODE |
| `dispatch_mw` | Economic dispatch BASEPOINT / target value in MW |

Candidate grain: `timestamp, generator_id`.

## state_estimation_YYYY_MM.parquet

| Column | Meaning |
|---|---|
| `timestamp` | Source timestamp, stored as a naive datetime |
| `generator_id` | Source-native generator CODE |
| `estimated_generation_mw` | State-estimated generator output in MW |

Candidate grain: `timestamp, generator_id`.

Dispatch and state-estimation generator IDs are not assumed to share the same
identifier namespace. No prefix stripping or guessed crosswalk is applied.
"""


def source_license(license_audit: dict) -> str:
    checked = license_audit["checked_at_asia_seoul"]
    lines = [
        "# Source, Attribution, and Permission Notes",
        "",
        "Provider: **Korea Power Exchange (한국전력거래소, KPX)**.",
        "",
        "This release is a normalized derivative and is not an official KPX distribution channel.",
        "",
        f"Final permission metadata re-check: `{checked}`.",
        "",
        "At that check, all three official data.go.kr records reported `비용부과유무 = 무료` and `이용허락범위 = 이용허락범위 제한 없음`.",
        "",
    ]
    for source, cfg in SOURCE_INFO.items():
        lines.extend(
            [
                f"## {source}",
                "",
                f"- KPX board: {cfg['kpx_board']}",
                f"- data.go.kr: {cfg['data_go_kr']}",
                "",
            ]
        )
    lines.extend(
        [
            "Kaggle license category: `other` (source permission is described above; no new Creative Commons license is asserted by this package).",
            "",
            "This project-level review is not legal advice.",
            "",
        ]
    )
    return "\n".join(lines)


def dataset_metadata() -> dict:
    return {
        "title": "South Korea Power Grid 5-Minute Data 2015-2026",
        "subtitle": "KPX demand, dispatch and state estimation at 5-minute resolution",
        "description": (
            "Normalized Korea Power Exchange (KPX) 5-minute demand forecasts, "
            "generator economic dispatch, and generator state-estimation data "
            "covering 2015-08 through 2026-07. Source-unavailable months, "
            "missing timestamps, duplicate handling, and one ambiguous historical "
            "snapshot are documented explicitly. This is a derivative dataset, "
            "not an official KPX distribution channel. Official data.go.kr records "
            "were re-checked before packaging and state 이용허락범위 제한 없음."
        ),
        "id": "taeyangg4/south-korea-power-grid-5-minute",
        "licenses": [{"name": "other"}],
    }


def main() -> int:
    final_audit = load_json(FINAL_AUDIT)
    license_audit = load_json(LICENSE_AUDIT)
    if final_audit.get("status") != "PASS_WITH_OBSERVATIONS":
        raise RuntimeError("Full-history checkpoint has not passed")
    if license_audit.get("status") != "PASS":
        raise RuntimeError("Release license gate has not passed")

    manifests = processed_manifests()
    if len(manifests) != 396:
        raise RuntimeError(f"Expected 396 processed manifests, found {len(manifests)}")

    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    unavailable_rows: list[dict] = []

    for manifest_path, manifest in manifests:
        source = str(manifest["source"])
        month = str(manifest["month"])
        status = str(manifest["status"])
        entry = {
            "source": source,
            "month": month,
            "status": status,
            "processed_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
            "output_rows": int(manifest["output_rows"]),
            "timestamp_parse_failure_count": int(manifest["timestamp_parse_failure_count"]),
            "remaining_candidate_key_duplicate_rows": int(
                manifest["remaining_candidate_key_duplicate_rows"]
            ),
            "exact_duplicate_rows_removed": int(manifest["exact_duplicate_rows_removed"]),
            "normalization_exception_rows_removed": int(
                manifest.get("normalization_exception_rows_removed", 0)
            ),
        }

        if status == "source_unavailable":
            download_manifest_path = ROOT / str(manifest["source_download_manifest"])
            download_manifest = load_json(download_manifest_path)
            entry.update(
                {
                    "release_file": None,
                    "parquet_size_bytes": 0,
                    "sha256": None,
                    "source_unavailable_evidence": manifest.get(
                        "source_unavailable_evidence"
                    ),
                    "source_article_url": download_manifest.get("source_url"),
                }
            )
            unavailable_rows.append(
                {
                    "source": source,
                    "month": month,
                    "evidence": manifest.get("source_unavailable_evidence"),
                    "source_article_url": download_manifest.get("source_url"),
                }
            )
        elif status == "success":
            source_path = ROOT / str(manifest["output_parquet"])
            release_name = f"{source}_{month.replace('-', '_')}.parquet"
            target = RELEASE_ROOT / release_name
            ensure_hardlink(source_path, target)
            entry.update(
                {
                    "release_file": release_name,
                    "parquet_size_bytes": int(target.stat().st_size),
                    "sha256": sha256(target),
                }
            )
        else:
            raise RuntimeError(
                f"Unsupported persisted processed status {status!r} for {source} {month}"
            )
        entries.append(entry)

    available_entries = [item for item in entries if item["status"] == "success"]
    if len(available_entries) != 388 or len(unavailable_rows) != 8:
        raise RuntimeError(
            "Expected 388 available Parquet files and 8 unavailable source-months, "
            f"found {len(available_entries)} and {len(unavailable_rows)}"
        )

    shutil.copyfile(EXCEPTIONS, RELEASE_ROOT / "normalization_exceptions.json")
    (RELEASE_ROOT / "README.md").write_text(
        release_readme(final_audit, license_audit), encoding="utf-8"
    )
    (RELEASE_ROOT / "DATA_DICTIONARY.md").write_text(
        data_dictionary(), encoding="utf-8"
    )
    (RELEASE_ROOT / "SOURCE_LICENSE.md").write_text(
        source_license(license_audit), encoding="utf-8"
    )
    (RELEASE_ROOT / "dataset-metadata.json").write_text(
        json.dumps(dataset_metadata(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(
        RELEASE_ROOT / "missing_source_months.csv",
        unavailable_rows,
        ["source", "month", "evidence", "source_article_url"],
    )
    missingness_rows = [
        {"source": source, **values}
        for source, values in final_audit["source_level_missingness"].items()
    ]
    write_csv(
        RELEASE_ROOT / "missingness_summary.csv",
        missingness_rows,
        [
            "source",
            "months",
            "months_with_missing",
            "missing_timestamps",
            "normalization_exception_timestamps_removed",
            "max_monthly_missing",
            "max_missing_month",
        ],
    )

    release_manifest = {
        "release": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "period": {"start": "2015-08", "end": "2026-07", "months": 132},
        "logical_source_month_records": 396,
        "available_parquet_files": len(available_entries),
        "source_unavailable_records": len(unavailable_rows),
        "output_rows": sum(int(item["output_rows"]) for item in entries),
        "parquet_size_bytes": sum(
            int(item["parquet_size_bytes"]) for item in available_entries
        ),
        "exact_duplicate_rows_removed": sum(
            int(item["exact_duplicate_rows_removed"]) for item in entries
        ),
        "normalization_exception_rows_removed": sum(
            int(item["normalization_exception_rows_removed"]) for item in entries
        ),
        "license_review": {
            "audit": str(LICENSE_AUDIT.relative_to(ROOT)).replace("\\", "/"),
            "checked_at_asia_seoul": license_audit["checked_at_asia_seoul"],
            "status": license_audit["status"],
            "kaggle_license_category": "other",
        },
        "sources": SOURCE_INFO,
        "files": entries,
    }
    (RELEASE_ROOT / "release_manifest.json").write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "release_root": str(RELEASE_ROOT),
                "logical_source_month_records": 396,
                "available_parquet_files": len(available_entries),
                "source_unavailable_records": len(unavailable_rows),
                "output_rows": release_manifest["output_rows"],
                "parquet_size_bytes": release_manifest["parquet_size_bytes"],
                "git_commit": release_manifest["git_commit"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
