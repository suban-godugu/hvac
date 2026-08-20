"""Safe numeric formatters for ventilation KPIs (backend + test oracle)."""
from __future__ import annotations

import math
from typing import Any, Optional


def _finite(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(n) or math.isinf(n):
        return None
    return n


def as_percent_number(value: Any) -> Optional[float]:
    """Normalize 0.685 or 68.5 to a 0–100 percent quantity. Never 68.5 → 6850."""
    n = _finite(value)
    if n is None:
        return None
    if abs(n) <= 1.0:
        return round(n * 100.0, 1)
    if abs(n) > 1000:
        return None
    return round(n, 1)


def format_percent(value: Any) -> str:
    n = as_percent_number(value)
    if n is None:
        return "—"
    return f"{n:.1f}%"


def format_number(value: Any, digits: int = 1) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    return f"{n:.{digits}f}"


def format_cfm(value: Any) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    return f"{int(round(n)):,} CFM"


def format_kw(value: Any, signed: bool = False) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    if signed:
        return f"{n:+.2f} kW"
    return f"{n:.2f} kW"


def format_kwh(value: Any, per_day: bool = True) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    suffix = " kWh/day" if per_day else " kWh"
    return f"{n:.1f}{suffix}"


def format_ppm(value: Any) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    return f"{int(round(n))} ppm"


def format_temperature(value: Any) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    return f"{n:.1f}°C"


def format_enthalpy(value: Any) -> str:
    n = _finite(value)
    if n is None:
        return "—"
    return f"{n:.2f} kJ/kg"
