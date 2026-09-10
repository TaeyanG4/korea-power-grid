from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
V1_ROOT = ROOT / "data" / "release" / "v1"
V2_ROOT = ROOT / "data" / "release" / "v2"
WORK_ROOT = ROOT / "data" / "working"
STATE_PATH = WORK_ROOT / "unified_v2_build_state.json"

PARQUET_NAME = "south_korea_power_grid_5min.parquet"
CSV_NAME = "south_korea_power_grid_5min.csv"

UNIFIED_SCHEMA = pa.schema(
    [
        pa.field("timestamp", pa.timestamp("ns"), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("generator_id", pa.string(), nullable=True),
        pa.field("value_mw", pa.float64(), nullable=True),
    ]
)

VALUE_COLUMNS = {
    "demand": "demand_forecast_mw",
    "dispatch": "dispatch_mw",
    "state_estimation": "estimated_generation_mw",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(payload: dict, state_path: Path = STATE_PATH) -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def atomic_replace(part_path: Path, final_path: Path) -> None:
    os.replace(part_path, final_path)


def normalize_batch(source: str, batch: pa.RecordBatch) -> pa.Table:
    if source not in VALUE_COLUMNS:
        raise ValueError(f"Unsupported source: {source}")

    table = pa.Table.from_batches([batch])
    rows = table.num_rows
    timestamp = table["timestamp"].cast(pa.timestamp("ns"))
    source_array = pa.array([source] * rows, type=pa.string())

    if source == "demand":
        generator_id = pa.nulls(rows, type=pa.string())
    else:
        generator_id = table["generator_id"].cast(pa.string())

    value_mw = table[VALUE_COLUMNS[source]].cast(pa.float64())
    return pa.Table.from_arrays(
        [timestamp, source_array, generator_id, value_mw],
        schema=UNIFIED_SCHEMA,
    )


def available_entries(start_month: str | None = None, end_month: str | None = None) -> list[dict]:
    manifest = load_json(V1_ROOT / "release_manifest.json")
    entries = [item for item in manifest["files"] if item["status"] == "success"]
    if start_month is None and end_month is None and len(entries) != 388:
        raise RuntimeError(f"Expected 388 available V1 files, found {len(entries)}")
    if start_month is not None:
        entries = [item for item in entries if str(item["month"]) >= start_month]
    if end_month is not None:
        entries = [item for item in entries if str(item["month"]) <= end_month]
    return entries


def build_parquet(
    batch_size: int,
    output_root: Path = V2_ROOT,
    start_month: str | None = None,
    end_month: str | None = None,
    state_path: Path = STATE_PATH,
) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    entries = available_entries(start_month=start_month, end_month=end_month)
    if not entries:
        raise RuntimeError("No available V1 files matched the requested range")
    final_path = output_root / PARQUET_NAME
    part_path = output_root / f"{PARQUET_NAME}.part"

    if part_path.exists():
        part_path.unlink()

    expected_rows = sum(int(item["output_rows"]) for item in entries)
    rows_written = 0
    per_source_rows = {source: 0 for source in VALUE_COLUMNS}

    writer = pq.ParquetWriter(
        part_path,
        UNIFIED_SCHEMA,
        compression="zstd",
        compression_level=6,
        use_dictionary=["source", "generator_id"],
        write_statistics=True,
    )
    try:
        for file_index, item in enumerate(entries, 1):
            source = str(item["source"])
            source_path = V1_ROOT / str(item["release_file"])
            parquet = pq.ParquetFile(source_path)
            for batch in parquet.iter_batches(batch_size=batch_size):
                unified = normalize_batch(source, batch)
                writer.write_table(unified, row_group_size=batch_size)
                rows_written += unified.num_rows
                per_source_rows[source] += unified.num_rows

            if file_index % 10 == 0 or file_index == len(entries):
                state = {
                    "stage": "parquet",
                    "status": "running",
                    "files_completed": file_index,
                    "files_total": len(entries),
                    "rows_written": rows_written,
                    "expected_rows": expected_rows,
                    "per_source_rows": per_source_rows,
                    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                write_state(state, state_path)
                print(
                    f"parquet {file_index}/{len(entries)} files, "
                    f"{rows_written:,}/{expected_rows:,} rows",
                    flush=True,
                )
    finally:
        writer.close()

    parquet = pq.ParquetFile(part_path)
    actual_schema = parquet.schema_arrow
    actual_rows = int(parquet.metadata.num_rows)
    parquet.close()
    if actual_schema != UNIFIED_SCHEMA:
        raise RuntimeError(f"Unified Parquet schema mismatch: {actual_schema}")
    if actual_rows != expected_rows or rows_written != expected_rows:
        raise RuntimeError(
            f"Unified Parquet row mismatch: metadata={actual_rows}, "
            f"written={rows_written}, expected={expected_rows}"
        )

    atomic_replace(part_path, final_path)
    result = {
        "stage": "parquet",
        "status": "complete",
        "path": str(final_path),
        "rows": rows_written,
        "bytes": final_path.stat().st_size,
        "row_groups": pq.ParquetFile(final_path).metadata.num_row_groups,
        "per_source_rows": per_source_rows,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_state(result, state_path)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return result


def csv_table(batch: pa.RecordBatch) -> pa.Table:
    table = pa.Table.from_batches([batch])
    # PyArrow strftime may require an external timezone database on Windows even
    # for naive timestamps. The source values are five-minute timestamps with
    # zero fractional seconds, so cast to ISO text and trim the nanosecond suffix.
    formatted_timestamp = pc.utf8_slice_codeunits(
        pc.cast(table["timestamp"], pa.string()), 0, 19
    )
    return pa.Table.from_arrays(
        [
            formatted_timestamp,
            table["source"],
            table["generator_id"],
            table["value_mw"],
        ],
        names=["timestamp", "source", "generator_id", "value_mw"],
    )


def build_csv(
    batch_size: int,
    resume: bool,
    output_root: Path = V2_ROOT,
    state_path: Path = STATE_PATH,
) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    parquet_path = output_root / PARQUET_NAME
    if not parquet_path.exists():
        raise RuntimeError(f"Unified Parquet is missing: {parquet_path}")

    final_path = output_root / CSV_NAME
    part_path = output_root / f"{CSV_NAME}.part"
    parquet = pq.ParquetFile(parquet_path)
    expected_rows = int(parquet.metadata.num_rows)

    start_batch_index = 0
    rows_written = 0
    truncate_to = 0
    if resume and part_path.exists() and state_path.exists():
        state = load_json(state_path)
        if state.get("stage") == "csv" and state.get("status") == "running":
            start_batch_index = int(state.get("batches_completed", 0))
            rows_written = int(state.get("rows_written", 0))
            truncate_to = int(state.get("csv_bytes", 0))
            with part_path.open("r+b") as handle:
                handle.truncate(truncate_to)
            print(
                f"resuming CSV after batch {start_batch_index}, "
                f"{rows_written:,} rows, byte offset {truncate_to:,}",
                flush=True,
            )
        else:
            part_path.unlink(missing_ok=True)
    else:
        part_path.unlink(missing_ok=True)

    sink_mode = "ab" if start_batch_index else "wb"
    batch_index = 0
    with part_path.open(sink_mode) as raw_sink:
        for batch in parquet.iter_batches(batch_size=batch_size):
            batch_index += 1
            if batch_index <= start_batch_index:
                continue

            table = csv_table(batch)
            buffer = pa.BufferOutputStream()
            pacsv.write_csv(
                table,
                buffer,
                write_options=pacsv.WriteOptions(include_header=(batch_index == 1)),
            )
            raw_sink.write(buffer.getvalue().to_pybytes())
            raw_sink.flush()
            rows_written += table.num_rows

            if batch_index % 20 == 0:
                csv_bytes = raw_sink.tell()
                state = {
                    "stage": "csv",
                    "status": "running",
                    "batches_completed": batch_index,
                    "rows_written": rows_written,
                    "expected_rows": expected_rows,
                    "csv_bytes": csv_bytes,
                    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                write_state(state, state_path)
                print(
                    f"csv batch {batch_index}, "
                    f"{rows_written:,}/{expected_rows:,} rows, "
                    f"{csv_bytes / 1e9:.2f} GB",
                    flush=True,
                )

    if rows_written != expected_rows:
        raise RuntimeError(
            f"Unified CSV row mismatch: written={rows_written}, expected={expected_rows}"
        )

    atomic_replace(part_path, final_path)
    result = {
        "stage": "csv",
        "status": "complete",
        "path": str(final_path),
        "rows": rows_written,
        "bytes": final_path.stat().st_size,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_state(result, state_path)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["parquet", "csv", "all"],
        default="all",
    )
    parser.add_argument("--batch-size", type=int, default=500_000)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=V2_ROOT,
    )
    parser.add_argument("--start-month")
    parser.add_argument("--end-month")
    parser.add_argument(
        "--resume-csv",
        action="store_true",
        help="Resume CSV generation from the last durable checkpoint",
    )
    args = parser.parse_args()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    state_path = (
        STATE_PATH
        if output_root.resolve() == V2_ROOT.resolve()
        else output_root / "build_state.json"
    )

    if args.stage in {"parquet", "all"}:
        build_parquet(
            args.batch_size,
            output_root=output_root,
            start_month=args.start_month,
            end_month=args.end_month,
            state_path=state_path,
        )
    if args.stage in {"csv", "all"}:
        build_csv(
            args.batch_size,
            resume=args.resume_csv,
            output_root=output_root,
            state_path=state_path,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
