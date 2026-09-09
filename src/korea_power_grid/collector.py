from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup
import requests
import zipfile

from .sources import BASE_URL, SOURCES, SourceConfig, month_range_desc, parse_month_from_title


USER_AGENT = "korea-power-grid/0.1 (+research dataset; official KPX sources)"


@dataclass
class PostRecord:
    source: str
    month: str
    title: str
    article_url: str
    attachment_url: str | None = None


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_text(session: requests.Session, url: str, timeout: tuple[int, int] = (20, 60)) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def discover_posts(
    session: requests.Session,
    source: SourceConfig,
    max_pages: int = 20,
) -> dict[str, PostRecord]:
    records: dict[str, PostRecord] = {}
    no_new_pages = 0

    for page in range(1, max_pages + 1):
        url = f"{source.board_url}&nPage={page}"
        soup = BeautifulSoup(fetch_text(session, url), "html.parser")
        found_this_page = 0
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            if "act=view" not in href or "list_no=" not in href:
                continue
            title = anchor.get_text(" ", strip=True)
            row = anchor.find_parent("tr")
            row_text = row.get_text(" ", strip=True) if row else ""
            month = parse_month_from_title(title, published_date=row_text)
            if month is None:
                continue
            article_url = urljoin(BASE_URL, href.replace("&amp;", "&"))
            if month not in records:
                records[month] = PostRecord(
                    source=source.key,
                    month=month,
                    title=title,
                    article_url=article_url,
                )
                found_this_page += 1

        if found_this_page == 0:
            no_new_pages += 1
        else:
            no_new_pages = 0
        if no_new_pages >= 2:
            break

    return records


def resolve_attachment(session: requests.Session, record: PostRecord) -> PostRecord:
    soup = BeautifulSoup(fetch_text(session, record.article_url), "html.parser")
    candidates: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if "boardDownload.es" in href:
            candidates.append(urljoin(BASE_URL, href.replace("&amp;", "&")))
    if not candidates:
        raise RuntimeError(f"No KPX attachment found for {record.source} {record.month}: {record.article_url}")
    record.attachment_url = candidates[0]
    return record


def build_source_index(
    session: requests.Session,
    source_keys: list[str],
    max_pages: int = 20,
) -> dict[str, dict[str, PostRecord]]:
    index: dict[str, dict[str, PostRecord]] = {}
    for key in source_keys:
        source = SOURCES[key]
        records = discover_posts(session, source, max_pages=max_pages)
        index[key] = records
    return index


def write_index(index: dict[str, dict[str, PostRecord]], path: Path) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            source: {month: asdict(record) for month, record in sorted(records.items())}
            for source, records in index.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_valid_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


DIRECT_ATTACHMENT_EXTENSIONS = {".csv", ".txt", ".xls", ".xlsx"}


def content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    utf8_match = re.search(r"filename\*=UTF-8''([^;]+)", value, flags=re.IGNORECASE)
    plain_match = re.search(r'filename="?([^";]+)"?', value, flags=re.IGNORECASE)
    raw = utf8_match.group(1) if utf8_match else (plain_match.group(1) if plain_match else None)
    if raw is None:
        return None
    name = unquote(raw).replace("\\", "/").split("/")[-1].strip()
    return name or None


def wrap_direct_attachment(payload: Path, target: Path, member_name: str) -> None:
    """Store an unchanged direct source payload in a deterministic ZIP wrapper."""
    info = zipfile.ZipInfo(member_name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    info.create_system = 3

    with zipfile.ZipFile(target, "w") as archive:
        with payload.open("rb") as source_handle, archive.open(info, "w") as member_handle:
            shutil.copyfileobj(source_handle, member_handle, length=1024 * 1024)


def existing_manifest_with_file_state(
    manifest_path: Path,
    *,
    source: str,
    month: str,
    source_url: str,
    attachment_url: str | None,
    target: Path,
) -> dict:
    existing: dict = {}
    if manifest_path.exists():
        try:
            candidate = json.loads(manifest_path.read_text(encoding="utf-8"))
            if candidate.get("source") == source and candidate.get("month") == month:
                existing = candidate
        except (OSError, json.JSONDecodeError):
            existing = {}

    existing.update(
        {
            "source": source,
            "month": month,
            "source_url": source_url,
            "attachment_url": attachment_url,
            "downloaded_at": existing.get("downloaded_at")
            or datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat(),
            "file_size": target.stat().st_size,
            "sha256": sha256(target),
            "status": "skipped_existing",
            "retry_count": 0,
        }
    )
    return existing


def _manifest_path(root: Path, source: str, month: str) -> Path:
    return root / "data" / "manifests" / "downloads" / source / f"{month}.json"


def _checkpoint_path(root: Path) -> Path:
    return root / "data" / "manifests" / "checkpoint.json"


def _raw_path(root: Path, source: str, month: str) -> Path:
    return root / "data" / "raw" / source / month / f"{source}_{month.replace('-', '_')}.zip"


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def download_record(
    session: requests.Session,
    root: Path,
    record: PostRecord,
    max_retries: int = 4,
    timeout: tuple[int, int] = (20, 300),
) -> dict:
    if not record.attachment_url:
        resolve_attachment(session, record)

    target = _raw_path(root, record.source, record.month)
    manifest_path = _manifest_path(root, record.source, record.month)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and target.stat().st_size > 0 and is_valid_zip(target):
        manifest = existing_manifest_with_file_state(
            manifest_path,
            source=record.source,
            month=record.month,
            source_url=record.article_url,
            attachment_url=record.attachment_url,
            target=target,
        )
        write_json_atomic(manifest_path, manifest)
        return manifest

    temp = target.with_suffix(target.suffix + ".download.part")
    wrapper_temp = target.with_suffix(target.suffix + ".part")
    last_error: Exception | None = None
    retry_count = 0

    for attempt in range(max_retries + 1):
        retry_count = attempt
        try:
            if temp.exists():
                temp.unlink()
            if wrapper_temp.exists():
                wrapper_temp.unlink()
            response_filename = None
            with session.get(record.attachment_url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                response_filename = content_disposition_filename(
                    response.headers.get("Content-Disposition")
                )
                with temp.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
            if temp.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty")

            source_payload_size = temp.stat().st_size
            source_payload_sha256 = sha256(temp)
            if is_valid_zip(temp):
                os.replace(temp, target)
                delivery_metadata = {
                    "source_delivery_format": "zip",
                    "source_attachment_filename": response_filename,
                    "source_payload_size": source_payload_size,
                    "source_payload_sha256": source_payload_sha256,
                    "local_storage_format": "source_zip",
                }
            else:
                suffix = Path(response_filename or "").suffix.lower()
                if suffix not in DIRECT_ATTACHMENT_EXTENSIONS:
                    raise RuntimeError(
                        "Downloaded payload is neither a ZIP archive nor a supported "
                        f"direct attachment: filename={response_filename!r}, "
                        f"size={source_payload_size}"
                    )
                if source_payload_size < 32:
                    raise RuntimeError(
                        "Downloaded direct attachment is implausibly small: "
                        f"filename={response_filename!r}, size={source_payload_size}"
                    )
                wrap_direct_attachment(temp, wrapper_temp, response_filename)
                if not is_valid_zip(wrapper_temp):
                    raise RuntimeError("Local direct-attachment ZIP wrapper failed validation")
                os.replace(wrapper_temp, target)
                temp.unlink()
                delivery_metadata = {
                    "source_delivery_format": "direct_file",
                    "source_attachment_filename": response_filename,
                    "source_payload_size": source_payload_size,
                    "source_payload_sha256": source_payload_sha256,
                    "local_storage_format": "single_member_zip_wrapper",
                }

            manifest = {
                "source": record.source,
                "month": record.month,
                "source_url": record.article_url,
                "attachment_url": record.attachment_url,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "file_size": target.stat().st_size,
                "sha256": sha256(target),
                "status": "success",
                "retry_count": retry_count,
                **delivery_metadata,
            }
            write_json_atomic(manifest_path, manifest)
            return manifest
        except Exception as exc:  # network/filesystem errors are recorded and retried
            last_error = exc
            if attempt < max_retries:
                time.sleep(min(2**attempt, 8))

    if temp.exists():
        temp.unlink()
    if wrapper_temp.exists():
        wrapper_temp.unlink()
    manifest = {
        "source": record.source,
        "month": record.month,
        "source_url": record.article_url,
        "attachment_url": record.attachment_url,
        "downloaded_at": None,
        "file_size": None,
        "sha256": None,
        "status": "failed",
        "retry_count": retry_count,
        "error": repr(last_error),
    }
    write_json_atomic(manifest_path, manifest)
    return manifest


def collect_range(
    root: Path,
    start: str,
    end: str,
    source_keys: list[str],
    dry_run: bool = False,
    max_retries: int = 4,
    retry_failed_only: bool = False,
) -> list[dict]:
    months = month_range_desc(start, end)
    session = make_session()
    index = build_source_index(session, source_keys)
    index_path = root / "data" / "manifests" / "source_index.json"
    write_index(index, index_path)

    planned: list[tuple[str, str, PostRecord]] = []
    missing: list[dict] = []
    for month in months:
        for source in source_keys:
            record = index[source].get(month)
            if record is None:
                missing.append({"source": source, "month": month, "status": "missing_post"})
            else:
                if retry_failed_only:
                    manifest_path = _manifest_path(root, source, month)
                    if not manifest_path.exists():
                        continue
                    try:
                        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if not str(existing.get("status", "")).startswith("failed"):
                        continue
                planned.append((month, source, record))

    write_json_atomic(
        root / "data" / "manifests" / "missing_posts.json",
        {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "records": missing},
    )

    if dry_run:
        return [
            {
                "month": month,
                "source": source,
                "article_url": record.article_url,
                "status": "planned",
            }
            for month, source, record in planned
        ] + missing

    results: list[dict] = []
    total = len(planned)
    for position, (month, source, record) in enumerate(planned, start=1):
        print(f"[{position}/{total}] {month} {source}", flush=True)
        try:
            resolve_attachment(session, record)
            result = download_record(
                session,
                root=root,
                record=record,
                max_retries=max_retries,
            )
        except Exception as exc:
            result = {
                "source": source,
                "month": month,
                "source_url": record.article_url,
                "status": "failed_before_download",
                "retry_count": 0,
                "error": repr(exc),
            }
            write_json_atomic(_manifest_path(root, source, month), result)
        results.append(result)
        write_json_atomic(
            _checkpoint_path(root),
            {
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                "requested_start": start,
                "requested_end": end,
                "sources": source_keys,
                "completed_records": len(results),
                "planned_records": total,
                "last_result": result,
            },
        )

    results.extend(missing)
    return results
