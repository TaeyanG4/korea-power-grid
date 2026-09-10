from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "data" / "release" / "v1"
OUT = ROOT / "data" / "audits" / "kaggle_v1_remote_qa.json"
DATASET = "taeyangg4/south-korea-power-grid-5-minute"


def load_remote_metadata(api: KaggleApi) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        meta_path = Path(api.dataset_metadata(DATASET, temp_dir))
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    return payload.get("info") or payload


def load_remote_files(api: KaggleApi) -> dict[str, int]:
    files: dict[str, int] = {}
    page_token: str | None = None
    while True:
        response = api.dataset_list_files(
            DATASET,
            page_token=page_token,
            page_size=200,
        )
        if response.error_message:
            raise RuntimeError(response.error_message)
        for item in response.files or []:
            files[str(item.name)] = int(item.total_bytes)
        page_token = response.next_page_token
        if not page_token:
            break
    return files


def main() -> int:
    api = KaggleApi()
    api.authenticate()

    local_metadata = json.loads(
        (RELEASE_ROOT / "dataset-metadata.json").read_text(encoding="utf-8")
    )
    status = json.loads(api.dataset_status(DATASET, format="json"))
    remote_metadata = load_remote_metadata(api)
    remote_files = load_remote_files(api)

    local_files = {
        path.name: int(path.stat().st_size)
        for path in RELEASE_ROOT.iterdir()
        if path.is_file() and path.name != "dataset-metadata.json"
    }

    missing_remote = sorted(set(local_files) - set(remote_files))
    unexpected_remote = sorted(set(remote_files) - set(local_files))
    size_mismatches = [
        {
            "name": name,
            "local_bytes": local_files[name],
            "remote_bytes": remote_files[name],
        }
        for name in sorted(set(local_files) & set(remote_files))
        if local_files[name] != remote_files[name]
    ]

    remote_licenses = [
        str(item.get("name")) if isinstance(item, dict) else str(item)
        for item in (remote_metadata.get("licenses") or [])
    ]
    remote_description = str(remote_metadata.get("description") or "")

    checks = {
        "dataset_status_ready": status.get("status") == "ready",
        "dataset_version_1": int(status.get("current_version_number", 0)) == 1,
        "remote_is_private": bool(remote_metadata.get("isPrivate")) is True,
        "remote_title_matches": remote_metadata.get("title") == local_metadata.get("title"),
        "remote_subtitle_matches": remote_metadata.get("subtitle")
        == local_metadata.get("subtitle"),
        "remote_license_other": "other" in {value.lower() for value in remote_licenses},
        "remote_description_mentions_kpx": "Korea Power Exchange" in remote_description,
        "remote_description_contains_permission_text": "이용허락범위 제한 없음"
        in remote_description,
        "local_upload_files_395": len(local_files) == 395,
        "remote_upload_files_395": len(remote_files) == 395,
        "remote_filename_set_exact": not missing_remote and not unexpected_remote,
        "remote_file_sizes_exact": not size_mismatches,
        "remote_total_bytes_exact": sum(remote_files.values()) == sum(local_files.values()),
    }
    passed = all(checks.values())

    report = {
        "release": "v1",
        "dataset": DATASET,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "problems": {
            "missing_remote": missing_remote,
            "unexpected_remote": unexpected_remote,
            "size_mismatches": size_mismatches,
        },
        "observed": {
            "dataset_status": status.get("status"),
            "current_version_number": status.get("current_version_number"),
            "is_private": bool(remote_metadata.get("isPrivate")),
            "title": remote_metadata.get("title"),
            "subtitle": remote_metadata.get("subtitle"),
            "licenses": remote_licenses,
            "local_upload_file_count": len(local_files),
            "remote_upload_file_count": len(remote_files),
            "local_total_bytes": sum(local_files.values()),
            "remote_total_bytes": sum(remote_files.values()),
        },
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
