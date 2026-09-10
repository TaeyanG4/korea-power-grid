from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "audits" / "kaggle_v2_usability_qa.json"
DATASET = "taeyangg4/south-korea-power-grid-5-minute"
EXPECTED_NOTEBOOK = "taeyangg4/south-korea-power-grid-v2-quickstart"


def main() -> int:
    api = KaggleApi()
    api.authenticate()

    matches = api.dataset_list(
        search="south-korea-power-grid-5-minute",
        user="taeyangg4",
    )
    dataset = next(
        (item for item in matches if str(getattr(item, "ref", "")) == DATASET),
        None,
    )
    if dataset is None:
        raise RuntimeError(f"Dataset not found in Kaggle search: {DATASET}")

    kernels = api.kernels_list(dataset=DATASET, page_size=100) or []
    linked = [
        {
            "ref": str(getattr(item, "ref", "")),
            "title": str(getattr(item, "title", "")),
            "is_private": getattr(item, "is_private", None),
        }
        for item in kernels
        if item is not None
    ]
    public_refs = {
        item["ref"] for item in linked if item.get("is_private") is not True
    }

    rating = float(getattr(dataset, "usability_rating", 0.0) or 0.0)
    checks = {
        "usability_rating_1": abs(rating - 1.0) < 1e-9,
        "quickstart_notebook_public_and_linked": EXPECTED_NOTEBOOK in public_refs,
    }
    passed = all(checks.values())
    report = {
        "release": "v2-unified",
        "dataset": DATASET,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "PENDING",
        "checks": checks,
        "observed": {
            "usability_rating": rating,
            "last_updated": str(getattr(dataset, "last_updated", None)),
            "linked_kernels": linked,
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
