from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELEASE_ROOT = ROOT / "data" / "release" / "v1"
TARGET_RELEASE_ROOT = ROOT / "data" / "release" / "v2"
ASSET_ROOT = ROOT / "docs" / "assets"
ASSET_PATH = ASSET_ROOT / "dataset-cover-image.png"
RELEASE_PATH = TARGET_RELEASE_ROOT / "dataset-cover-image.png"


def main() -> int:
    demand_path = SOURCE_RELEASE_ROOT / "demand_2026_07.parquet"
    frame = pd.read_parquet(demand_path, columns=["timestamp", "demand_forecast_mw"])
    frame = frame.dropna().sort_values("timestamp")
    first_day = frame["timestamp"].dt.normalize().iloc[0]
    sample = frame[frame["timestamp"].dt.normalize() == first_day].copy()

    ASSET_ROOT.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(12, 6), dpi=100)
    fig.patch.set_facecolor("#0b1324")

    ax = fig.add_axes([0.06, 0.14, 0.88, 0.42])
    ax.set_facecolor("#101d35")
    ax.plot(sample["timestamp"], sample["demand_forecast_mw"], linewidth=2.4, color="#58c4ff")
    ax.fill_between(
        sample["timestamp"],
        sample["demand_forecast_mw"],
        sample["demand_forecast_mw"].min(),
        alpha=0.12,
        color="#58c4ff",
    )
    ax.set_ylabel("Demand forecast (MW)", color="#dbeafe", fontsize=11)
    ax.tick_params(axis="x", colors="#a5b4c8", labelsize=9)
    ax.tick_params(axis="y", colors="#a5b4c8", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#2b3b57")
    ax.grid(alpha=0.16, color="#dbeafe")

    fig.text(
        0.06,
        0.88,
        "South Korea Power Grid",
        color="white",
        fontsize=31,
        fontweight="bold",
        va="top",
    )
    fig.text(
        0.06,
        0.79,
        "5-minute KPX operations data  |  2015-08 to 2026-07",
        color="#b9c8dd",
        fontsize=15,
        va="top",
    )
    fig.text(
        0.06,
        0.67,
        "Demand Forecast   •   Economic Dispatch   •   State Estimation",
        color="#7dd3fc",
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.94,
        0.88,
        "1.0B+ rows\n1 Parquet + 1 CSV\nKorea Power Exchange",
        color="#dbeafe",
        fontsize=12,
        ha="right",
        va="top",
        linespacing=1.45,
    )
    fig.text(
        0.94,
        0.07,
        f"Illustrative demand profile: {first_day:%Y-%m-%d}",
        color="#8194ae",
        fontsize=9,
        ha="right",
    )

    fig.savefig(ASSET_PATH, facecolor=fig.get_facecolor(), bbox_inches=None)
    plt.close(fig)
    shutil.copyfile(ASSET_PATH, RELEASE_PATH)

    print(f"WROTE {ASSET_PATH}")
    print(f"COPIED {RELEASE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
