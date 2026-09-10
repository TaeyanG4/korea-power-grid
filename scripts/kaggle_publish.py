from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[1]
DATASET = "taeyangg4/south-korea-power-grid-5-minute"
OUT = ROOT / "data" / "audits" / "kaggle_v1_publish.json"
SEOUL = ZoneInfo("Asia/Seoul")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def remote_metadata(api: KaggleApi) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        meta_path = Path(api.dataset_metadata(DATASET, temp_dir))
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    return payload.get("info") or payload


def main() -> int:
    release_qa = load_json(ROOT / "data" / "audits" / "release_v1_qa.json")
    remote_qa = load_json(ROOT / "data" / "audits" / "kaggle_v1_remote_qa.json")
    license_qa = load_json(
        ROOT / "data" / "audits" / "release_license_check_2026-09-10.json"
    )

    checked_at = datetime.fromisoformat(license_qa["checked_at_asia_seoul"])
    now = datetime.now(SEOUL)
    prechecks = {
        "release_qa_pass": release_qa.get("status") == "PASS",
        "remote_qa_pass": remote_qa.get("status") == "PASS",
        "license_qa_pass": license_qa.get("status") == "PASS",
        "license_checked_today": checked_at.astimezone(SEOUL).date() == now.date(),
        "remote_qa_was_private": remote_qa.get("observed", {}).get("is_private") is True,
    }
    if not all(prechecks.values()):
        report = {
            "release": "v1",
            "dataset": DATASET,
            "status": "BLOCKED",
            "prechecks": prechecks,
        }
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    api = KaggleApi()
    api.authenticate()

    status_before = json.loads(api.dataset_status(DATASET, format="json"))
    metadata_before = remote_metadata(api)
    runtime_checks = {
        "dataset_ready_before": status_before.get("status") == "ready",
        "dataset_version_1_before": int(status_before.get("current_version_number", 0)) == 1,
        "dataset_private_before": metadata_before.get("isPrivate") is True,
    }
    if not all(runtime_checks.values()):
        report = {
            "release": "v1",
            "dataset": DATASET,
            "status": "BLOCKED",
            "prechecks": prechecks,
            "runtime_checks": runtime_checks,
        }
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    with tempfile.TemporaryDirectory() as temp_dir:
        meta_path = Path(api.dataset_metadata(DATASET, temp_dir))
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        info = payload.get("info") or payload
        info["isPrivate"] = False
        if "info" in payload:
            payload["info"] = info
        else:
            payload = info
        meta_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        api.dataset_metadata_update(DATASET, temp_dir)

    status_after = json.loads(api.dataset_status(DATASET, format="json"))
    metadata_after = remote_metadata(api)
    postchecks = {
        "dataset_ready_after": status_after.get("status") == "ready",
        "dataset_version_1_after": int(status_after.get("current_version_number", 0)) == 1,
        "dataset_public_after": metadata_after.get("isPrivate") is False,
    }
    passed = all(postchecks.values())

    report = {
        "release": "v1",
        "dataset": DATASET,
        "url": "https://www.kaggle.com/datasets/taeyangg4/south-korea-power-grid-5-minute",
        "status": "PUBLISHED" if passed else "FAIL",
        "published_at_asia_seoul": datetime.now(SEOUL).isoformat(),
        "prechecks": prechecks,
        "runtime_checks": runtime_checks,
        "postchecks": postchecks,
        "observed": {
            "status": status_after.get("status"),
            "current_version_number": status_after.get("current_version_number"),
            "is_private": metadata_after.get("isPrivate"),
            "title": metadata_after.get("title"),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
