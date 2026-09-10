from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath
from matplotlib.patches import Circle, PathPatch, Polygon


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELEASE_ROOT = ROOT / "data" / "release" / "v1"
TARGET_RELEASE_ROOT = ROOT / "data" / "release" / "v2"
ASSET_ROOT = ROOT / "docs" / "assets"
ASSET_PATH = ASSET_ROOT / "dataset-cover-image.png"
RELEASE_PATH = TARGET_RELEASE_ROOT / "dataset-cover-image.png"


def draw_curve(ax, start, control, end, color, linewidth=1.0, alpha=0.55):
    path = MplPath(
        [start, control, end],
        [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3],
    )
    ax.add_patch(
        PathPatch(
            path,
            fill=False,
            edgecolor=color,
            linewidth=linewidth,
            alpha=alpha,
        )
    )


def draw_pylon(ax, x, base_y, height, scale=1.0):
    top = base_y + height
    shoulder = base_y + height * 0.64
    mid = base_y + height * 0.36
    half = 0.024 * scale
    color = "#020713"
    lw = 2.0 * scale

    ax.plot([x, x - half, x + half, x], [top, base_y, base_y, top], color=color, lw=lw)
    ax.plot([x - half * 0.78, x + half * 0.78], [shoulder, shoulder], color=color, lw=lw)
    ax.plot([x - half * 0.56, x + half * 0.56], [mid, mid], color=color, lw=lw)
    ax.plot([x - half * 0.56, x + half * 0.56], [shoulder, mid], color=color, lw=lw * 0.8)
    ax.plot([x + half * 0.56, x - half * 0.56], [shoulder, mid], color=color, lw=lw * 0.8)
    ax.plot([x - half * 1.15, x + half * 1.15], [shoulder, shoulder], color=color, lw=lw * 0.8)


def main() -> int:
    demand_path = SOURCE_RELEASE_ROOT / "demand_2026_07.parquet"
    frame = pd.read_parquet(demand_path, columns=["timestamp", "demand_forecast_mw"])
    frame = frame.dropna().sort_values("timestamp")
    first_day = frame["timestamp"].dt.normalize().iloc[0]
    sample = frame[frame["timestamp"].dt.normalize() == first_day].copy()

    ASSET_ROOT.mkdir(parents=True, exist_ok=True)

    # Kaggle CLI 2.2.x submits fixed crop rectangles for dataset covers:
    # 560x280 for the header and a centered 280x280 thumbnail (x=140..420).
    # Render at exactly that canvas size so Kaggle does not crop an arbitrary
    # top-left region from a larger landscape image.
    width_px = 560
    height_px = 280
    fig = plt.figure(figsize=(5.6, 2.8), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()

    # Deep navy vertical/radial-style gradient background.
    y = np.linspace(0, 1, height_px)[:, None]
    x = np.linspace(0, 1, width_px)[None, :]
    glow = np.exp(-(((x - 0.56) / 0.42) ** 2 + ((y - 0.52) / 0.62) ** 2))
    blue_glow = np.exp(-(((x - 0.86) / 0.25) ** 2 + ((y - 0.44) / 0.42) ** 2))
    bg = np.zeros((height_px, width_px, 3), dtype=float)
    bg[..., 0] = 0.018 + 0.014 * glow
    bg[..., 1] = 0.055 + 0.080 * glow + 0.045 * blue_glow
    bg[..., 2] = 0.105 + 0.150 * glow + 0.130 * blue_glow
    ax.imshow(np.clip(bg, 0, 1), extent=[0, 1, 0, 1], origin="lower", aspect="auto")

    # Subtle grid gives the whole card structure without relying on text.
    for gx in np.linspace(0.03, 0.97, 25):
        ax.plot([gx, gx], [0.09, 0.96], color="#3f7fb4", lw=0.45, alpha=0.12)
    for gy in np.linspace(0.12, 0.94, 13):
        ax.plot([0.02, 0.98], [gy, gy], color="#3f7fb4", lw=0.45, alpha=0.12)

    # Decorative generation bars distributed across the width.
    rng = np.random.default_rng(20260910)
    bar_x = np.linspace(0.035, 0.965, 56)
    bar_h = 0.08 + 0.30 * rng.random(len(bar_x))
    envelope = 0.35 + 0.65 * (
        np.exp(-((bar_x - 0.20) / 0.20) ** 2)
        + 0.75 * np.exp(-((bar_x - 0.73) / 0.26) ** 2)
    )
    bar_h *= np.clip(envelope, 0.35, 1.0)
    ax.bar(
        bar_x,
        bar_h,
        width=0.008,
        bottom=0.17,
        color="#2f8fd7",
        edgecolor="none",
        alpha=0.25,
    )

    # Central smart-grid mesh: dense enough to avoid an empty middle.
    center = np.array([0.53, 0.52])
    theta = rng.uniform(0, 2 * np.pi, 40)
    radius = np.sqrt(rng.uniform(0.03, 1.0, 40))
    nodes = np.column_stack(
        [
            center[0] + 0.26 * radius * np.cos(theta),
            center[1] + 0.24 * radius * np.sin(theta),
        ]
    )
    nodes = np.vstack(
        [
            nodes,
            [0.53, 0.52],
            [0.42, 0.58],
            [0.63, 0.61],
            [0.60, 0.39],
            [0.45, 0.39],
        ]
    )

    distances = np.sqrt(((nodes[:, None, :] - nodes[None, :, :]) ** 2).sum(axis=2))
    for i in range(len(nodes)):
        neighbors = np.argsort(distances[i])[1:4]
        for j in neighbors:
            if j <= i:
                continue
            ax.plot(
                [nodes[i, 0], nodes[j, 0]],
                [nodes[i, 1], nodes[j, 1]],
                color="#4dc5ff",
                lw=0.8,
                alpha=0.32,
            )

    for nx, ny in nodes:
        ax.add_patch(Circle((nx, ny), 0.0045, facecolor="#5ad2ff", edgecolor="none", alpha=0.86))
        ax.add_patch(Circle((nx, ny), 0.0105, facecolor="none", edgecolor="#5ad2ff", lw=0.5, alpha=0.18))

    # Broad energy-flow arcs crossing the card and converging on the network mesh.
    for offset, alpha in [(0.0, 0.56), (0.06, 0.34), (-0.06, 0.28), (0.12, 0.22)]:
        draw_curve(
            ax,
            (-0.04, 0.80 + offset),
            (0.24, 0.23 + offset * 0.5),
            (0.55, 0.52),
            "#4dc5ff",
            linewidth=1.1,
            alpha=alpha,
        )
        draw_curve(
            ax,
            (0.55, 0.52),
            (0.78, 0.80 - offset * 0.3),
            (1.04, 0.69 + offset),
            "#55c9ff",
            linewidth=1.0,
            alpha=alpha * 0.9,
        )

    # Warm control/dispatch paths add visual distinction without labels.
    warm_points = nodes[rng.choice(len(nodes), size=11, replace=False)]
    for i, (nx, ny) in enumerate(warm_points):
        target = warm_points[(i + 3) % len(warm_points)]
        ax.plot([nx, target[0]], [ny, target[1]], color="#ffbf55", lw=0.85, alpha=0.44)
        ax.add_patch(Circle((nx, ny), 0.0055, facecolor="#ffd36b", edgecolor="#fff2bf", lw=0.45, alpha=0.95))

    # Actual July 1 demand profile becomes the lower visual backbone.
    values = sample["demand_forecast_mw"].to_numpy(dtype=float)
    vmin = float(np.nanmin(values))
    vmax = float(np.nanmax(values))
    normalized = (values - vmin) / max(vmax - vmin, 1.0)
    demand_x = np.linspace(0.06, 0.94, len(normalized))
    demand_y = 0.18 + normalized * 0.24
    ax.fill_between(demand_x, 0.145, demand_y, color="#2f9bdd", alpha=0.09)
    ax.plot(demand_x, demand_y, color="#5bd2ff", lw=2.0, alpha=0.92)
    ax.plot(demand_x, demand_y - 0.008, color="#ffd067", lw=0.85, alpha=0.65)

    # Low skyline/terrain band and transmission infrastructure anchor the bottom edge.
    terrain_x = np.linspace(0, 1, 110)
    terrain = 0.075 + 0.014 * np.sin(terrain_x * 17) + 0.008 * np.sin(terrain_x * 43)
    polygon = np.column_stack([terrain_x, terrain])
    polygon = np.vstack([polygon, [1, 0], [0, 0]])
    ax.add_patch(Polygon(polygon, closed=True, facecolor="#020711", edgecolor="none", alpha=0.98))

    for bx in np.linspace(0.05, 0.86, 46):
        bw = rng.uniform(0.006, 0.013)
        bh = rng.uniform(0.025, 0.085)
        base = 0.075
        ax.add_patch(
            Polygon(
                [[bx - bw / 2, base], [bx - bw / 2, base + bh], [bx + bw / 2, base + bh], [bx + bw / 2, base]],
                closed=True,
                facecolor="#07111f",
                edgecolor="#173b5d",
                linewidth=0.4,
                alpha=0.98,
            )
        )
        if bh > 0.045:
            for wy in np.arange(base + 0.012, base + bh - 0.005, 0.015):
                ax.add_patch(Circle((bx, wy), 0.0017, facecolor="#ffcc68", edgecolor="none", alpha=0.65))

    draw_pylon(ax, 0.84, 0.055, 0.20, 0.80)
    draw_pylon(ax, 0.91, 0.047, 0.28, 1.00)
    draw_pylon(ax, 0.975, 0.040, 0.36, 1.18)
    ax.plot([0.81, 1.02], [0.19, 0.30], color="#020713", lw=1.15, alpha=0.95)
    ax.plot([0.81, 1.02], [0.15, 0.24], color="#020713", lw=1.15, alpha=0.95)

    # No text, labels, ticks, legends, or logos: the image remains reusable as a card/banner.
    fig.savefig(
        ASSET_PATH,
        dpi=100,
        facecolor="#071426",
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)
    shutil.copyfile(ASSET_PATH, RELEASE_PATH)

    print(f"WROTE {ASSET_PATH}")
    print(f"COPIED {RELEASE_PATH}")
    print(f"SIZE {width_px}x{height_px}")
    print(f"SOURCE_DEMAND_DAY {first_day:%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
