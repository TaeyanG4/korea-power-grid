from __future__ import annotations

import json
import textwrap
from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks" / "kaggle_v2_quickstart"
NOTEBOOK_PATH = NOTEBOOK_DIR / "south-korea-power-grid-v2-quickstart.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


def main() -> int:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3"},
    }

    nb["cells"] = [
        md(
            """
            # South Korea Power Grid V2: daily operations study

            This notebook turns the unified Korea Power Exchange (KPX) 5-minute dataset into a compact operations-analysis project. The current release provides the same 1B+ rows as both Parquet and CSV. The notebook deliberately uses **predicate-filtered slices from the Parquet file** instead of loading the 50+ GB compatibility CSV or materializing the full table in memory.

            We answer four practical questions:

            1. What does a recent week of the system demand forecast look like, and where are the sharpest 5-minute ramps?
            2. On the peak-demand day of that week, how do aggregate economic-dispatch BASEPOINT and aggregate state-estimated generation evolve?
            3. Which generator IDs contribute the most observed 5-minute energy within each generator-level source?
            4. How complete is the selected operating-day slice?

            **Important:** demand is a forecast, dispatch is BASEPOINT, and state estimation is estimated generation. Differences between these aggregates are operational diagnostics, **not** direct measurements of physical system imbalance. Generator IDs remain source-native, so this notebook never joins dispatch and state-estimation rows by generator ID.
            """
        ),
        code(
            """
            from pathlib import Path
            import json
            import os

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
            import pyarrow.dataset as ds
            import pyarrow.parquet as pq


            def find_input_file(filename: str) -> Path:
                # Find a dataset file on Kaggle or in a local test directory.
                roots = []
                override = os.environ.get("KPX_DATASET_DIR")
                if override:
                    roots.append(Path(override))

                kaggle_root = Path("/kaggle/input")
                if kaggle_root.exists():
                    roots.append(kaggle_root)

                for root in roots:
                    direct = root / filename
                    if direct.exists():
                        return direct
                    matches = sorted(root.rglob(filename))
                    if matches:
                        return matches[0]

                visible = []
                if kaggle_root.exists():
                    visible = sorted(p.name for p in kaggle_root.iterdir())
                raise FileNotFoundError(
                    f"Could not find {filename}. Kaggle input folders: {visible[:30]}"
                )


            PARQUET = find_input_file("south_korea_power_grid_5min.parquet")
            CSV = find_input_file("south_korea_power_grid_5min.csv")
            MANIFEST = find_input_file("release_manifest.json")
            DATA_DIR = PARQUET.parent

            print(f"Parquet: {PARQUET}")
            print(f"CSV compatibility export: {CSV}")
            print(f"Manifest: {MANIFEST}")
            """
        ),
        md(
            """
            ## Release shape and schema

            Parquet metadata gives the row count and typed schema without scanning a billion rows. The release manifest provides verified source-level row counts produced by the release QA pipeline.
            """
        ),
        code(
            """
            pf = pq.ParquetFile(PARQUET)
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

            print(f"Rows: {pf.metadata.num_rows:,}")
            print(f"Row groups: {pf.metadata.num_row_groups:,}")
            print(f"Parquet size: {PARQUET.stat().st_size / 1e9:.2f} GB")
            print(f"CSV size: {CSV.stat().st_size / 1e9:.2f} GB")
            print(pf.schema_arrow)

            source_counts = (
                pd.Series(manifest["source_rows"], name="rows")
                .rename_axis("source")
                .to_frame()
            )
            source_counts["share_pct"] = (
                100 * source_counts["rows"] / source_counts["rows"].sum()
            )
            source_counts
            """
        ),
        md(
            """
            ## Memory-conscious reader

            Arrow predicates restrict both the source and timestamp interval. Only the requested columns are materialized. This is the preferred pattern for this release; avoid `pd.read_csv()` on the 50+ GB compatibility CSV for exploratory work.

            The CSV is still useful for interoperability. When you only need to verify its schema or feed a CSV-only downstream tool, read it incrementally or in chunks rather than loading the full file into pandas.
            """
        ),
        code(
            """
            csv_preview = pd.read_csv(CSV, nrows=5)
            csv_preview
            """
        ),
        code(
            """
            grid = ds.dataset(PARQUET, format="parquet")


            def load_window(source: str, start, end, columns):
                start = pd.Timestamp(start).to_pydatetime()
                end = pd.Timestamp(end).to_pydatetime()
                predicate = (
                    (ds.field("source") == source)
                    & (ds.field("timestamp") >= start)
                    & (ds.field("timestamp") < end)
                )
                frame = grid.to_table(columns=columns, filter=predicate).to_pandas()
                if "timestamp" in frame:
                    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
                    frame = frame.sort_values("timestamp").reset_index(drop=True)
                return frame
            """
        ),
        md(
            """
            ## 1) One week of demand: load shape and ramp events

            We use 2026-07-01 through 2026-07-07. This is only about two thousand demand rows at 5-minute resolution, but it is enough to demonstrate daily load shape, peak selection, and ramp analysis.
            """
        ),
        code(
            """
            STUDY_START = pd.Timestamp("2026-07-01")
            STUDY_END = pd.Timestamp("2026-07-08")

            demand = load_window(
                "demand",
                STUDY_START,
                STUDY_END,
                ["timestamp", "value_mw"],
            ).dropna(subset=["timestamp", "value_mw"])

            demand["date"] = demand["timestamp"].dt.date
            demand["ramp_mw_5m"] = demand["value_mw"].diff()
            demand["abs_ramp_mw_5m"] = demand["ramp_mw_5m"].abs()

            daily = demand.groupby("date").agg(
                observations=("value_mw", "size"),
                min_mw=("value_mw", "min"),
                mean_mw=("value_mw", "mean"),
                max_mw=("value_mw", "max"),
            )
            daily["peak_to_trough_mw"] = daily["max_mw"] - daily["min_mw"]
            daily
            """
        ),
        code(
            """
            fig, ax = plt.subplots(figsize=(14, 5))
            ax.plot(demand["timestamp"], demand["value_mw"], linewidth=1.4)
            ax.set_title("KPX demand forecast - first week of July 2026")
            ax.set_ylabel("MW")
            ax.set_xlabel("timestamp")
            ax.grid(alpha=0.2)
            plt.tight_layout()
            """
        ),
        code(
            """
            top_demand_ramps = demand.nlargest(10, "abs_ramp_mw_5m")[[
                "timestamp", "value_mw", "ramp_mw_5m", "abs_ramp_mw_5m"
            ]].reset_index(drop=True)
            top_demand_ramps
            """
        ),
        md(
            """
            ## 2) Peak-day operations: demand vs dispatch vs state estimation

            The peak-demand day is selected from the one-week slice. We then read only that 24-hour interval for dispatch and state estimation. Aggregation is performed by timestamp; there is **no generator-ID crosswalk** between the two sources.
            """
        ),
        code(
            """
            peak_row = demand.loc[demand["value_mw"].idxmax()]
            PEAK_DAY = peak_row["timestamp"].normalize()
            NEXT_DAY = PEAK_DAY + pd.Timedelta(days=1)

            print(f"Peak study day: {PEAK_DAY.date()}")
            print(f"Peak demand forecast: {peak_row['value_mw']:,.1f} MW at {peak_row['timestamp']}")

            dispatch = load_window(
                "dispatch",
                PEAK_DAY,
                NEXT_DAY,
                ["timestamp", "generator_id", "value_mw"],
            )
            state = load_window(
                "state_estimation",
                PEAK_DAY,
                NEXT_DAY,
                ["timestamp", "generator_id", "value_mw"],
            )
            demand_day = demand[
                (demand["timestamp"] >= PEAK_DAY) & (demand["timestamp"] < NEXT_DAY)
            ][["timestamp", "value_mw"]].copy()

            print(f"Demand rows: {len(demand_day):,}")
            print(f"Dispatch rows: {len(dispatch):,}")
            print(f"State-estimation rows: {len(state):,}")
            """
        ),
        code(
            """
            def aggregate_generation(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
                clean = frame.dropna(subset=["timestamp", "value_mw"])
                out = clean.groupby("timestamp")["value_mw"].agg(["sum", "count"]).reset_index()
                return out.rename(columns={
                    "sum": f"{prefix}_total_mw",
                    "count": f"{prefix}_generator_rows",
                })


            dispatch_agg = aggregate_generation(dispatch, "dispatch")
            state_agg = aggregate_generation(state, "state")

            operations = (
                demand_day.rename(columns={"value_mw": "demand_forecast_mw"})
                .merge(dispatch_agg, on="timestamp", how="outer")
                .merge(state_agg, on="timestamp", how="outer")
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

            operations["dispatch_minus_demand_mw"] = (
                operations["dispatch_total_mw"] - operations["demand_forecast_mw"]
            )
            operations["state_minus_demand_mw"] = (
                operations["state_total_mw"] - operations["demand_forecast_mw"]
            )
            operations["state_minus_dispatch_mw"] = (
                operations["state_total_mw"] - operations["dispatch_total_mw"]
            )
            operations.head()
            """
        ),
        code(
            """
            fig, ax = plt.subplots(figsize=(14, 5))
            ax.plot(operations["timestamp"], operations["demand_forecast_mw"], label="Demand forecast")
            ax.plot(operations["timestamp"], operations["dispatch_total_mw"], label="Dispatch BASEPOINT total")
            ax.plot(operations["timestamp"], operations["state_total_mw"], label="State-estimation total")
            ax.set_title(f"Aggregate operating signals - {PEAK_DAY.date()}")
            ax.set_ylabel("MW")
            ax.set_xlabel("timestamp")
            ax.legend()
            ax.grid(alpha=0.2)
            plt.tight_layout()
            """
        ),
        md(
            """
            The three series are useful for timing and co-movement diagnostics, but their gaps must be interpreted carefully: demand is a forecast and the generator-level sources can have different coverage and semantics. The next table summarizes observed aggregate gaps rather than labeling them as imbalance.
            """
        ),
        code(
            """
            gap_summary = operations[[
                "dispatch_minus_demand_mw",
                "state_minus_demand_mw",
                "state_minus_dispatch_mw",
            ]].agg(["count", "mean", "median", "min", "max"]).T
            gap_summary
            """
        ),
        md(
            """
            ## 3) Fast-ramp diagnostics on the peak day

            Five-minute changes identify moments that deserve closer operational inspection. We compute ramps independently for each aggregate signal.
            """
        ),
        code(
            """
            ramp_columns = {
                "demand_forecast_mw": "demand_ramp_mw_5m",
                "dispatch_total_mw": "dispatch_ramp_mw_5m",
                "state_total_mw": "state_ramp_mw_5m",
            }
            for source_col, ramp_col in ramp_columns.items():
                operations[ramp_col] = operations[source_col].diff()

            ramp_events = []
            for ramp_col in ramp_columns.values():
                event = operations.loc[
                    operations[ramp_col].abs().nlargest(5).index,
                    ["timestamp", ramp_col],
                ].copy()
                event["signal"] = ramp_col
                event = event.rename(columns={ramp_col: "ramp_mw_5m"})
                ramp_events.append(event)

            top_operating_ramps = (
                pd.concat(ramp_events, ignore_index=True)
                .assign(abs_ramp_mw_5m=lambda x: x["ramp_mw_5m"].abs())
                .sort_values("abs_ramp_mw_5m", ascending=False)
                .reset_index(drop=True)
            )
            top_operating_ramps
            """
        ),
        md(
            """
            ## 4) Generator concentration inside each source

            Generator IDs are analyzed **within their own source only**. The energy value below is an observed-row proxy: `MW * 5/60` summed over available 5-minute records for the selected day. It is not used to map dispatch generators to state-estimation generators.
            """
        ),
        code(
            """
            def generator_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, float]:
                clean = frame.dropna(subset=["generator_id", "value_mw"]).copy()
                summary = clean.groupby("generator_id").agg(
                    observations=("value_mw", "size"),
                    mean_mw=("value_mw", "mean"),
                    max_mw=("value_mw", "max"),
                    mw_sum=("value_mw", "sum"),
                )
                summary["observed_energy_mwh"] = summary["mw_sum"] * (5.0 / 60.0)
                total = summary["observed_energy_mwh"].sum()
                summary["share_pct"] = np.where(
                    total != 0,
                    100 * summary["observed_energy_mwh"] / total,
                    np.nan,
                )
                hhi = float(((summary["share_pct"] / 100.0) ** 2).sum() * 10000)
                return summary.sort_values("observed_energy_mwh", ascending=False), hhi


            dispatch_generators, dispatch_hhi = generator_summary(dispatch)
            state_generators, state_hhi = generator_summary(state)

            print(f"Dispatch generator IDs observed: {len(dispatch_generators):,}; HHI proxy: {dispatch_hhi:,.1f}")
            print(f"State-estimation generator IDs observed: {len(state_generators):,}; HHI proxy: {state_hhi:,.1f}")
            display(dispatch_generators.head(15))
            display(state_generators.head(15))
            """
        ),
        code(
            """
            fig, ax = plt.subplots(figsize=(12, 5))
            dispatch_generators.head(15).sort_values("observed_energy_mwh").plot.barh(
                y="observed_energy_mwh", ax=ax, legend=False
            )
            ax.set_title(f"Top dispatch generator IDs by observed energy proxy - {PEAK_DAY.date()}")
            ax.set_xlabel("Observed MWh proxy")
            ax.set_ylabel("generator_id")
            plt.tight_layout()
            """
        ),
        code(
            """
            fig, ax = plt.subplots(figsize=(12, 5))
            state_generators.head(15).sort_values("observed_energy_mwh").plot.barh(
                y="observed_energy_mwh", ax=ax, legend=False
            )
            ax.set_title(f"Top state-estimation generator IDs by observed energy proxy - {PEAK_DAY.date()}")
            ax.set_xlabel("Observed MWh proxy")
            ax.set_ylabel("generator_id")
            plt.tight_layout()
            """
        ),
        md(
            """
            ## 5) Coverage check for the selected day

            A complete 5-minute day has 288 timestamps. The dataset intentionally preserves source missingness, so this check is more informative than silently filling gaps.
            """
        ),
        code(
            """
            expected_timestamps = 24 * 60 // 5
            coverage = pd.DataFrame({
                "source": ["demand", "dispatch", "state_estimation"],
                "unique_timestamps": [
                    demand_day["timestamp"].nunique(),
                    dispatch["timestamp"].nunique(),
                    state["timestamp"].nunique(),
                ],
            })
            coverage["expected_timestamps"] = expected_timestamps
            coverage["missing_timestamps"] = (
                coverage["expected_timestamps"] - coverage["unique_timestamps"]
            )
            coverage["coverage_pct"] = (
                100 * coverage["unique_timestamps"] / coverage["expected_timestamps"]
            )
            coverage
            """
        ),
        md(
            """
            ## What else can be built with this dataset?

            This compact project demonstrates the core access pattern. The same unified Parquet can support substantially larger studies without loading all 1B+ rows at once:

            - **Demand seasonality and peak-risk studies:** filter only `source=demand` across months or years and model hour-of-day, weekday, seasonal, and holiday patterns.
            - **Ramp-event detection:** rank 5-minute demand, dispatch, or state-estimation changes and study recurring high-ramp windows.
            - **Generator portfolio structure:** measure within-source concentration, persistence, and changes in active generator counts over time.
            - **Aggregate operating-signal diagnostics:** compare demand forecast, total BASEPOINT, and total state estimation at matching timestamps while respecting their different semantics.
            - **Missingness and source-quality monitoring:** use the documented unavailable source-months and timestamp gaps to build data-quality dashboards.
            - **Scalable ML features:** train models on filtered demand windows or sampled generator windows using Parquet predicate pushdown rather than the 50+ GB CSV.

            For broader historical work, keep the same rule used here: **filter by source, time range, and columns before converting to pandas**. DuckDB, Polars, Spark, or PyArrow can extend the same approach to larger slices.

            ### Data-quality reminders

            - Timestamps are timezone-naive because verified timezone metadata is not present in the source files.
            - Missing five-minute timestamps remain missing; they are not silently imputed.
            - Eight official source-month attachments were unavailable and are listed in `missing_source_months.csv`.
            - Exact duplicates were removed under the documented candidate-key rule.
            - The ambiguous state-estimation snapshot at `2016-06-03 17:20` was excluded rather than choosing arbitrarily between conflicting full-generator snapshots.
            - Generator IDs are source-native. Do not assume a dispatch/state-estimation crosswalk unless independently validated.
            """
        ),
    ]

    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK_PATH)

    # Keep the file ASCII-safe for Windows/CLI tooling while preserving Unicode escapes.
    payload = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    NOTEBOOK_PATH.write_text(
        json.dumps(payload, ensure_ascii=True, indent=1),
        encoding="ascii",
    )

    print(f"WROTE {NOTEBOOK_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
