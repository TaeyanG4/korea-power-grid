from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

from korea_power_grid.collector import (
    content_disposition_filename,
    wrap_direct_attachment,
)


def test_content_disposition_filename_percent_decoding() -> None:
    value = (
        "attachment;filename=%EB%B0%9C%EC%A0%84%EA%B8%B0%EB%B3%84_"
        "5%EB%B6%84_%EA%B2%BD%EC%A0%9C%EA%B8%89%EC%A0%84.txt"
    )
    assert content_disposition_filename(value) == "발전기별_5분_경제급전.txt"


def test_direct_attachment_wrapper_preserves_payload_and_is_deterministic() -> None:
    project_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(dir=project_root) as temp_dir:
        temp_path = Path(temp_dir)
        payload = temp_path / "payload.txt"
        payload.write_bytes(
            "시간,발전기CODE,BASEPOINT\n2020/01/01,1,0\n".encode("cp949")
        )
        first = temp_path / "first.zip"
        second = temp_path / "second.zip"

        wrap_direct_attachment(payload, first, "발전기별_5분_경제급전자료.txt")
        wrap_direct_attachment(payload, second, "발전기별_5분_경제급전자료.txt")

        assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
            second.read_bytes()
        ).digest()
        with zipfile.ZipFile(first) as archive:
            assert archive.namelist() == ["발전기별_5분_경제급전자료.txt"]
            assert archive.read(archive.namelist()[0]) == payload.read_bytes()
