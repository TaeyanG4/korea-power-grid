from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urljoin

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
        manifest = {
            "source": record.source,
            "month": record.month,
            "source_url": record.article_url,
            "attachment_url": record.attachment_url,
            "downloaded_at": datetime.fromtimestamp(
                target.stat().st_mtime, timezone.utc
            ).isoformat(),
            "file_size": target.stat().st_size,
            "sha256": sha256(target),
            "status": "skipped_existing",
            "retry_count": 0,
        }
        write_json_atomic(manifest_path, manifest)
        return manifest

    temp = target.with_suffix(target.suffix + ".part")
    last_error: Exception | None = None
    retry_count = 0

    for attempt in range(max_retries + 1):
        retry_count = attempt
        try:
            if temp.exists():
                temp.unlink()
            with session.get(record.attachment_url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                with temp.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
            if temp.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty")
            if not is_valid_zip(temp):
                raise RuntimeError("Downloaded file is not a valid ZIP archive")
            os.replace(temp, target)
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
            }
            write_json_atomic(manifest_path, manifest)
            return manifest
        except Exception as exc:  # network/filesystem errors are recorded and retried
            last_error = exc
            if attempt < max_retries:
                time.sleep(min(2**attempt, 8))

    if temp.exists():
        temp.unlink()
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
