from korea_power_grid.sources import month_range_desc, parse_month_from_title


def test_parse_month_from_title() -> None:
    assert parse_month_from_title("2026년 7월 5분단위경제급전") == "2026-07"
    assert parse_month_from_title("2026년도 7월 5분 수요예측 자료") == "2026-07"
    assert parse_month_from_title("5분수요예측_201509") == "2015-09"
    assert parse_month_from_title("상태추정_201508") == "2015-08"
    assert parse_month_from_title("8월분 실적", "2015/09/30") == "2015-08"
    assert parse_month_from_title("12월분 실적", "2016/01/28") == "2015-12"
    assert parse_month_from_title("2015년 8월 발전기별 상태추정") == "2015-08"
    assert parse_month_from_title("unrelated") is None


def test_month_range_desc() -> None:
    assert month_range_desc("2026-05", "2026-07") == ["2026-07", "2026-06", "2026-05"]
    assert month_range_desc("2025-12", "2026-02") == ["2026-02", "2026-01", "2025-12"]
