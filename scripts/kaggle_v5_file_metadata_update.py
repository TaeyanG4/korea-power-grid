from __future__ import annotations

from pathlib import Path

import kaggle_v2_file_metadata_update as sync


ROOT = Path(__file__).resolve().parents[1]

sync.V2_ROOT = ROOT / "data" / "release" / "v4"
sync.METADATA_PATH = sync.V2_ROOT / "dataset-metadata.json"
sync.OUT = ROOT / "data" / "audits" / "kaggle_v5_databundle_metadata.json"
sync.APPROVED_VERSION = 5


if __name__ == "__main__":
    try:
        raise SystemExit(sync.main())
    except sync.KaggleMetadataError as exc:
        print(f"ERROR: {exc}", file=sync.sys.stderr)
        raise SystemExit(1)
