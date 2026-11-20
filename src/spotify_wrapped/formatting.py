"""Human friendly formatting shared by the statistics texts and the TUI."""

from __future__ import annotations


def format_number(value: float, digits: int = 0) -> str:
    """Format a number with thousands separators (``12345.6 -> '12,346'``)."""
    return f"{value:,.{digits}f}"


def format_duration(minutes: float) -> str:
    """Format a duration given in minutes (``1505 -> '1 d 1 h'``, ``3.5 -> '3 min 30 s'``)."""
    if minutes < 1:
        return f"{round(minutes * 60)} s"
    if minutes < 10:
        whole = int(minutes)
        seconds = round((minutes - whole) * 60)
        return f"{whole} min {seconds} s" if seconds else f"{whole} min"
    total = round(minutes)
    days, rest = divmod(total, 24 * 60)
    hours, mins = divmod(rest, 60)
    if days:
        return f"{days} d {hours} h" if hours else f"{days} d"
    if hours:
        return f"{hours} h {mins} min" if mins else f"{hours} h"
    return f"{mins} min"


def format_hours(minutes: float) -> str:
    """Format minutes as hours (``754 -> '12.6 h'``)."""
    return f"{minutes / 60:,.1f} h"


def plural(count: int, word: str, suffix: str = "s") -> str:
    """``plural(1, 'day') -> '1 day'``, ``plural(3, 'day') -> '3 days'``."""
    return f"{format_number(count)} {word}{'' if count == 1 else suffix}"
