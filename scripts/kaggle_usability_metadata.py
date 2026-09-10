from __future__ import annotations

import json
from pathlib import Path

from build_release import RELEASE_ROOT, dataset_metadata


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads(
        (RELEASE_ROOT / "release_manifest.json").read_text(encoding="utf-8")
    )
    entries = manifest["files"]
    metadata = dataset_metadata(entries)
    out = RELEASE_ROOT / "dataset-metadata.json"
    out.write_text(
        json.dumps(metadata, ensure_ascii=True, indent=2),
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "metadata_path": str(out),
                "description_chars": len(metadata["description"]),
                "keywords": metadata["keywords"],
                "expected_update_frequency": metadata["expectedUpdateFrequency"],
                "provenance_chars": len(metadata["userSpecifiedSources"]),
                "resources": len(metadata["resources"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
