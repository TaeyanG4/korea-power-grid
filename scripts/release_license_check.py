from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SEOUL = ZoneInfo("Asia/Seoul")

SOURCES = {
    "demand": {
        "name": "한국전력거래소_5분 단위 전력수요 예측자료",
        "url": "https://www.data.go.kr/data/15051432/fileData.do",
    },
    "dispatch": {
        "name": "한국전력거래소_발전기별 5분 단위 경제급전",
        "url": "https://www.data.go.kr/data/15051425/fileData.do",
    },
    "state_estimation": {
        "name": "한국전력거래소_발전기별 5분 단위 상태추정",
        "url": "https://www.data.go.kr/data/15051426/fileData.do",
    },
}


def normalized_text(html: bytes) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.stripped_strings)
    text = re.sub(r"\s+", " ", text)
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    return text, title


def inspect_source(session: requests.Session, key: str, cfg: dict) -> dict:
    response = session.get(cfg["url"], timeout=(20, 60))
    response.raise_for_status()
    text, title = normalized_text(response.content)

    provider_ok = "한국전력거래소" in text
    free_ok = bool(re.search(r"비용부과유무\s*무료", text))
    unrestricted_ok = bool(
        re.search(r"이용허락범위\s*이용허락범위\s*제한\s*없음", text)
        or re.search(r"이용허락범위\s*제한\s*없음", text)
    )

    return {
        "source": key,
        "dataset_name": cfg["name"],
        "url": cfg["url"],
        "http_status": response.status_code,
        "page_title": title,
        "provider": "Korea Power Exchange (한국전력거래소)" if provider_ok else None,
        "cost": "무료" if free_ok else None,
        "permission_scope": "이용허락범위 제한 없음" if unrestricted_ok else None,
        "checks": {
            "provider_kpx": provider_ok,
            "cost_free": free_ok,
            "permission_scope_unrestricted": unrestricted_ok,
        },
        "pass": provider_ok and free_ok and unrestricted_ok,
    }


def main() -> int:
    checked_at = datetime.now(SEOUL)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "korea-power-grid-release-license-check/1.0 "
                "(+https://github.com/TaeyanG4/korea-power-grid)"
            )
        }
    )

    results = [inspect_source(session, key, cfg) for key, cfg in SOURCES.items()]
    passed = all(item["pass"] for item in results)
    audit = {
        "checked_at_asia_seoul": checked_at.isoformat(),
        "purpose": "Final redistribution gate immediately before release packaging",
        "status": "PASS" if passed else "FAIL",
        "expected": {
            "provider": "Korea Power Exchange (한국전력거래소)",
            "cost": "무료",
            "permission_scope": "이용허락범위 제한 없음",
        },
        "sources": results,
        "note": (
            "This is a project-level metadata verification, not legal advice. "
            "Public release remains gated on package QA and accurate attribution."
        ),
    }

    out = (
        ROOT
        / "data"
        / "audits"
        / f"release_license_check_{checked_at:%Y-%m-%d}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
