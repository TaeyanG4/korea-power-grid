import sys
from datetime import datetime
from pathlib import Path

import pyarrow as pa


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_unified_dataset import UNIFIED_SCHEMA, csv_table, normalize_batch


def test_normalize_demand_batch() -> None:
    batch = pa.record_batch(
        [
            pa.array([datetime(2026, 7, 1, 0, 0)], type=pa.timestamp("ns")),
            pa.array([59000.5], type=pa.float64()),
        ],
        names=["timestamp", "demand_forecast_mw"],
    )
    table = normalize_batch("demand", batch)
    assert table.schema == UNIFIED_SCHEMA
    assert table.to_pylist() == [
        {
            "timestamp": table["timestamp"][0].as_py(),
            "source": "demand",
            "generator_id": None,
            "value_mw": 59000.5,
        }
    ]


def test_normalize_dispatch_batch() -> None:
    batch = pa.record_batch(
        [
            pa.array([datetime(2026, 7, 1, 0, 0)], type=pa.timestamp("ns")),
            pa.array(["GEN001"]),
            pa.array([123.4], type=pa.float64()),
        ],
        names=["timestamp", "generator_id", "dispatch_mw"],
    )
    table = normalize_batch("dispatch", batch)
    assert table.schema == UNIFIED_SCHEMA
    assert table["source"][0].as_py() == "dispatch"
    assert table["generator_id"][0].as_py() == "GEN001"
    assert table["value_mw"][0].as_py() == 123.4


def test_csv_table_formats_timestamp_without_fractional_seconds() -> None:
    batch = pa.record_batch(
        [
            pa.array([datetime(2026, 7, 1, 0, 5)], type=pa.timestamp("ns")),
            pa.array(["state_estimation"]),
            pa.array(["GEN002"]),
            pa.array([42.0], type=pa.float64()),
        ],
        schema=UNIFIED_SCHEMA,
    )
    table = csv_table(batch)
    assert table["timestamp"][0].as_py() == "2026-07-01 00:05:00"
    assert table.column_names == ["timestamp", "source", "generator_id", "value_mw"]
