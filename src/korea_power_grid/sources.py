from __future__ import annotations

from dataclasses import dataclass
import re


BASE_URL = "https://www.kpx.or.kr"
MONTH_RE = re.compile(r"(20\d{2})\s*년(?:도)?\s*(\d{1,2})\s*월")
COMPACT_MONTH_RE = re.compile(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])(?!\d)")
MONTH_ONLY_RE = re.compile(r"(?<!\d)(1[0-2]|0?[1-9])\s*\uc6d4")
PUBLISHED_DATE_RE = re.compile(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})")


@dataclass(frozen=True)
class SourceConfig:
    key: str
    mid: str
    bid: str
    label: str

    @property
    def board_url(self) -> str:
        return f"{BASE_URL}/board.es?mid={self.mid}&bid={self.bid}"


SOURCES: dict[str, SourceConfig] = {
    "demand": SourceConfig(
        key="demand",
        mid="a10109020700",
        bid="0065",
        label="5-minute demand forecast",
    ),
    "dispatch": SourceConfig(
        key="dispatch",
        mid="a10109020200",
        bid="0070",
        label="generator 5-minute economic dispatch",
    ),
    "state_estimation": SourceConfig(
        key="state_estimation",
        mid="a10109020400",
        bid="0068",
        label="generator 5-minute state estimation",
    ),
}


def parse_month_from_title(title: str, published_date: str | None = None) -> str | None:
    match = MONTH_RE.search(title)
    if match:
        year, month = match.groups()
        return f"{int(year):04d}-{int(month):02d}"

    compact = COMPACT_MONTH_RE.search(title)
    if compact:
        year, month = compact.groups()
        return f"{int(year):04d}-{int(month):02d}"
    if published_date:
        month_only = MONTH_ONLY_RE.search(title)
        published = PUBLISHED_DATE_RE.search(published_date)
        if month_only and published:
            target_month = int(month_only.group(1))
            publication_year = int(published.group(1))
            publication_month = int(published.group(2))
            target_year = publication_year - 1 if target_month > publication_month else publication_year
            return f"{target_year:04d}-{target_month:02d}"
    return None


def validate_month(month: str) -> tuple[int, int]:
    match = re.fullmatch(r"(20\d{2})-(\d{2})", month)
    if not match:
        raise ValueError(f"Invalid month {month!r}; expected YYYY-MM")
    year, mon = map(int, match.groups())
    if not 1 <= mon <= 12:
        raise ValueError(f"Invalid month {month!r}")
    return year, mon


def month_range_desc(start: str, end: str) -> list[str]:
    sy, sm = validate_month(start)
    ey, em = validate_month(end)
    start_num = sy * 12 + sm - 1
    end_num = ey * 12 + em - 1
    if start_num > end_num:
        raise ValueError("start must be earlier than or equal to end")
    months: list[str] = []
    for value in range(end_num, start_num - 1, -1):
        year, zero_mon = divmod(value, 12)
        months.append(f"{year:04d}-{zero_mon + 1:02d}")
    return months
