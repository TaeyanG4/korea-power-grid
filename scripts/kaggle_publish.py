from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
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

    was_private = metadata_before.get("isPrivate") is True
    if was_private:
        action = "set_public"
        with tempfile.TemporaryDirectory() as temp_dir:
            meta_path = Path(api.dataset_metadata(DATASET, temp_dir))
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            info = payload.get("info") or payload
            info["isPrivate"] = False
            if "info" in payload:
                payload["info"] = info
            else:
                payload = info
            meta_path.write_text(
                json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8"
            )
            api.dataset_metadata_update(DATASET, temp_dir)
    else:
        action = "already_public_verify_only"

    status_after = json.loads(api.dataset_status(DATASET, format="json"))
    metadata_after = remote_metadata(api)
    public_url = "https://www.kaggle.com/datasets/taeyangg4/south-korea-power-grid-5-minute"
    anonymous_response = requests.get(
        public_url,
        timeout=30,
        allow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    anonymous_title_present = (
        "South Korea Power Grid 5-Minute Data 2015-2026" in anonymous_response.text
    )
    anonymous_login_redirect = "/account/login" in anonymous_response.url.lower()
    postchecks = {
        "dataset_ready_after": status_after.get("status") == "ready",
        "dataset_version_1_after": int(status_after.get("current_version_number", 0)) == 1,
        # Kaggle omits isPrivate from downloaded metadata once it is false/public.
        "dataset_public_after": metadata_after.get("isPrivate") is not True,
        "anonymous_http_200": anonymous_response.status_code == 200,
        "anonymous_title_present": anonymous_title_present,
        "anonymous_no_login_redirect": not anonymous_login_redirect,
    }
    passed = all(postchecks.values())

    report = {
        "release": "v1",
        "dataset": DATASET,
        "url": public_url,
        "status": "PUBLISHED" if passed else "FAIL",
        "published_at_asia_seoul": datetime.now(SEOUL).isoformat(),
        "action": action,
        "prechecks": prechecks,
        "runtime_checks": runtime_checks,
        "postchecks": postchecks,
        "observed": {
            "status": status_after.get("status"),
            "current_version_number": status_after.get("current_version_number"),
            "is_private": metadata_after.get("isPrivate"),
            "title": metadata_after.get("title"),
            "anonymous_http_status": anonymous_response.status_code,
            "anonymous_final_url": anonymous_response.url,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
