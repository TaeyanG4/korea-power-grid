from __future__ import annotations

import io
import sys
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pilot_audit import (  # noqa: E402
    detect_text_encoding,
    inspect_three_column_text_header,
    read_dispatch_xlsx,
)


def test_detect_text_encoding_variants() -> None:
    assert detect_text_encoding(b"TIME,GEN_CODE,BASEPOINT\n") == "ascii"
    assert detect_text_encoding("\uc2dc\uac04,\ubc1c\uc804\uae30CODE,BASEPOINT\n".encode("cp949")) == "cp949"
    assert detect_text_encoding("\uc2dc\uac04,\ubc1c\uc804\uae30CODE,BASEPOINT\n".encode("utf-8")) == "utf-8"
    assert detect_text_encoding(b"\xef\xbb\xbf" + "\uc2dc\uac04,\ubc1c\uc804\uae30CODE,BASEPOINT\n".encode("utf-8")) == "utf-8-sig"


def test_cp949_dispatch_preamble_does_not_confuse_comma_text_for_header() -> None:
    text = (
        "\uc124\uba85,\uc911\uac04,\ucf64\ub9c8\uac00 \uc788\uc5b4\ub3c4 \ud5e4\ub354\uac00 \uc544\ub2d8\n"
        "\ucd94\uac00 \uc124\uba85\n"
        "\n"
        "\uc2dc\uac04,\ubc1c\uc804\uae30CODE,BASEPOINT\n"
        "2023-08-01,1,0\n"
    )
    stream = io.BytesIO(text.encode("cp949"))

    encoding, columns, preamble_rows = inspect_three_column_text_header(
        "dispatch",
        stream,
        label="dispatch.txt",
    )

    assert encoding == "cp949"
    assert columns == ["\uc2dc\uac04", "\ubc1c\uc804\uae30CODE", "BASEPOINT"]
    assert preamble_rows == 3
    assert stream.readline().decode("cp949").strip() == "2023-08-01,1,0"


def test_ascii_dispatch_header_without_preamble() -> None:
    stream = io.BytesIO(b"TIME,GEN_CODE,BASEPOINT\n2026-07-01 00:00:00,2,0\n")
    encoding, columns, preamble_rows = inspect_three_column_text_header("dispatch", stream)

    assert encoding == "ascii"
    assert columns == ["TIME", "GEN_CODE", "BASEPOINT"]
    assert preamble_rows == 0


def test_header_scan_is_bounded() -> None:
    stream = io.BytesIO(("\uc124\uba85\n" * 101).encode("cp949"))
    with pytest.raises(RuntimeError, match="first 100 lines"):
        inspect_three_column_text_header("dispatch", stream, label="broken.txt")


def test_dispatch_xlsx_with_preamble_and_headerless_followup_sheet() -> None:
    workbook = Workbook()
    first = workbook.active
    first.title = "first"
    first.append(["description"])
    first.append([None, "시간", "발전기CODE", "BASEPOINT"])
    first.append([None, datetime(2022, 1, 1, 0, 0), 1, 100.5])
    first.append([None, datetime(2022, 1, 1, 0, 5), 1, 101.5])

    second = workbook.create_sheet("second")
    second.append([datetime(2022, 1, 2, 0, 0), 2, 200.5])
    second.append([datetime(2022, 1, 2, 0, 5), 2, 201.5])

    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()

    frame, metadata = read_dispatch_xlsx(buffer.getvalue())

    assert list(frame.columns) == ["TIME", "GEN_CODE", "BASEPOINT"]
    assert len(frame) == 4
    assert frame.iloc[0].tolist() == [datetime(2022, 1, 1, 0, 0), 1, 100.5]
    assert frame.iloc[-1].tolist() == [datetime(2022, 1, 2, 0, 5), 2, 201.5]
    assert metadata["worksheet_count"] == 2
    assert metadata["worksheet_layout"][0]["header_row_1based"] == 2
    assert metadata["worksheet_layout"][0]["data_columns_1based"] == [2, 3, 4]
    assert metadata["worksheet_layout"][1]["header_row_1based"] is None
