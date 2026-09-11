from __future__ import annotations

import json
import tempfile
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.datasets.types.dataset_api_service import ApiListTreeDatasetFilesRequest


ROOT = Path(__file__).resolve().parents[1]
V4_ROOT = ROOT / "data" / "release" / "v4"
LOCAL_QA = ROOT / "data" / "audits" / "release_v4_qa.json"
OUT = ROOT / "data" / "audits" / "kaggle_v4_remote_qa.json"

DATASET = "taeyangg4/south-korea-power-grid-5-minute"
PUBLIC_URL = f"https://www.kaggle.com/datasets/{DATASET}"
EXPECTED_FILES = {
    "south_korea_power_grid_5min.parquet",
    "south_korea_power_grid_5min_2026_07.csv",
    "missing_source_months.csv",
    "missingness_summary.csv",
    "release_manifest.json",
}
MAIN_FILES = {
    "south_korea_power_grid_5min.parquet",
    "south_korea_power_grid_5min_2026_07.csv",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_remote_metadata(api: KaggleApi) -> dict:
    with tempfile.TemporaryDirectory(dir=ROOT / "data" / "audits") as temp_dir:
        meta_path = Path(api.dataset_metadata(DATASET, temp_dir))
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    return payload.get("info") or payload


def load_remote_files(api: KaggleApi) -> dict[str, int]:
    files: dict[str, int] = {}
    page_token: str | None = None
    while True:
        response = api.dataset_list_files(DATASET, page_token=page_token, page_size=200)
        if response.error_message:
            raise RuntimeError(response.error_message)
        for item in response.files or []:
            files[str(item.name)] = int(item.total_bytes)
        page_token = response.next_page_token
        if not page_token:
            return files


def load_tree_descriptions(api: KaggleApi, version: int) -> dict[str, str]:
    client = api.build_kaggle_client()
    descriptions: dict[str, str] = {}
    page_token: str | None = None
    while True:
        request = ApiListTreeDatasetFilesRequest()
        request.owner_slug = "taeyangg4"
        request.dataset_slug = "south-korea-power-grid-5-minute"
        request.dataset_version_number = version
        request.page_size = 200
        request.page_token = page_token
        response = client.datasets.dataset_api_client.list_tree_dataset_files(request)
        for item in response.files or []:
            descriptions[str(item.name)] = str(item.description or "")
        page_token = response.next_page_token
        if not page_token:
            return descriptions


def main() -> int:
    local_qa = load_json(LOCAL_QA)
    local_metadata = load_json(V4_ROOT / "dataset-metadata.json")
    local_files = {name: int((V4_ROOT / name).stat().st_size) for name in EXPECTED_FILES}

    api = KaggleApi()
    api.authenticate()
    status = json.loads(api.dataset_status(DATASET, format="json"))
    version = int(status.get("current_version_number", 0))
    remote_metadata = load_remote_metadata(api)
    remote_files = load_remote_files(api)
    tree_descriptions = load_tree_descriptions(api, version) if version else {}

    public_response = requests.get(
        PUBLIC_URL,
        timeout=30,
        allow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    soup = BeautifulSoup(public_response.text, "html.parser")
    og_image = soup.find("meta", attrs={"property": "og:image"})
    og_image_url = str(og_image.get("content") or "") if og_image else ""

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
    described_resources = {
        name for name, description in tree_descriptions.items() if description.strip()
    }

    checks = {
        "local_v4_qa_pass": local_qa.get("status") == "PASS",
        "dataset_status_ready": status.get("status") == "ready",
        "dataset_version_4": version == 4,
        "dataset_public": remote_metadata.get("isPrivate") is not True,
        "remote_resource_count_5": len(remote_files) == 5,
        "remote_filename_set_exact": not missing_remote and not unexpected_remote,
        "remote_file_sizes_exact": not size_mismatches,
        "remote_total_bytes_exact": sum(remote_files.values()) == sum(local_files.values()),
        "remote_title_matches": remote_metadata.get("title") == local_metadata.get("title"),
        "remote_subtitle_matches": remote_metadata.get("subtitle") == local_metadata.get("subtitle"),
        "remote_description_matches": remote_metadata.get("description") == local_metadata.get("description"),
        "main_file_descriptions_present": MAIN_FILES <= described_resources,
        "anonymous_http_200": public_response.status_code == 200,
        "anonymous_no_login_redirect": "/account/login" not in public_response.url.lower(),
        "public_og_image_nondefault": bool(og_image_url)
        and "default-background" not in og_image_url.lower(),
    }
    passed = all(checks.values())
    report = {
        "release": "v4-parquet-plus-july-csv",
        "dataset": DATASET,
        "url": PUBLIC_URL,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "problems": {
            "missing_remote": missing_remote,
            "unexpected_remote": unexpected_remote,
            "size_mismatches": size_mismatches,
            "resources_without_descriptions": sorted(set(remote_files) - described_resources),
        },
        "observed": {
            "dataset_status": status.get("status"),
            "current_version_number": status.get("current_version_number"),
            "remote_file_count": len(remote_files),
            "remote_total_bytes": sum(remote_files.values()),
            "file_descriptions": tree_descriptions,
            "og_image": og_image_url,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
