from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from korea_power_grid.collector import collect_range  # noqa: E402
from korea_power_grid.sources import SOURCES  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect official monthly KPX V1 source files")
    parser.add_argument("--start", required=True, help="Oldest month, YYYY-MM")
    parser.add_argument("--end", required=True, help="Newest month, YYYY-MM")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=sorted(SOURCES),
        default=list(SOURCES),
        help="Sources to collect (default: all V1 sources)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover and plan only; do not download")
    parser.add_argument("--max-retries", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = collect_range(
        root=ROOT,
        start=args.start,
        end=args.end,
        source_keys=args.sources,
        dry_run=args.dry_run,
        max_retries=args.max_retries,
    )
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({"records": len(results), "status_counts": counts}, ensure_ascii=False, indent=2))
    return 1 if any(status.startswith("failed") for status in counts) else 0


if __name__ == "__main__":
    raise SystemExit(main())

