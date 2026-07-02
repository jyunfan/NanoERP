from __future__ import annotations

from datetime import date


MARKETS = [
    (1, "其餘市場"),
    (2, "建國市場"),
    (3, "南部市場"),
]

MARKET_NAMES = dict(MARKETS)

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


def format_work_date(work_date: str) -> str:
    try:
        parsed = date.fromisoformat(work_date)
    except ValueError:
        return f"作業日期 {work_date}"
    roc_year = parsed.year - 1911
    weekday = WEEKDAYS[parsed.weekday()]
    return f"作業日期 {roc_year}年 {parsed.month}月 {parsed.day}日 星期{weekday}"


def format_short_date(work_date: str) -> str:
    try:
        parsed = date.fromisoformat(work_date)
    except ValueError:
        return work_date
    return f"{parsed.month}-{parsed.day}"


def format_number(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
