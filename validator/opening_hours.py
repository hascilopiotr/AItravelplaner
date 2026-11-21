"""
Minimal OSM opening_hours parser.
Handles the most common formats:
  Mo-Fr 09:00-18:00
  Mo-Su 10:00-20:00
  Mo-Fr 08:00-16:00; Sa 09:00-13:00
  24/7
"""

from __future__ import annotations

from datetime import time, datetime

DAY_MAP = {
    "Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6,
}


def _parse_time(s: str) -> time:
    h, m = s.strip().split(":")
    return time(int(h), int(m))


def _expand_days(day_expr: str) -> list[int]:
    """'Mo-Fr' -> [0,1,2,3,4],  'Sa' -> [5]"""
    day_expr = day_expr.strip()
    if "-" in day_expr:
        start, end = day_expr.split("-")
        s, e = DAY_MAP[start.strip()], DAY_MAP[end.strip()]
        return list(range(s, e + 1))
    if day_expr not in DAY_MAP:
        raise KeyError(day_expr)  # e.g. 'PH' -> caller treats as unknown
    return [DAY_MAP[day_expr]]


def is_open(opening_hours: str | None, dt: datetime) -> bool | None:
    """
    Returns True/False, or None if the string can't be parsed
    (caller treats None as 'unknown / assume open').
    """
    if not opening_hours:
        return None
    oh = opening_hours.strip()
    if oh == "24/7":
        return True

    weekday = dt.weekday()
    current = dt.time()

    for rule in oh.split(";"):
        rule = rule.strip()
        if not rule:
            continue
        parts = rule.split(" ", 1)
        if len(parts) != 2:
            return None
        day_part, time_part = parts
        if "-" not in time_part or ":" not in time_part:
            return None
        try:
            open_t, close_t = [_parse_time(t) for t in time_part.split("-")]
            days = _expand_days(day_part)
        except (ValueError, KeyError):
            return None

        if weekday in days and open_t <= current <= close_t:
            return True

    return False
