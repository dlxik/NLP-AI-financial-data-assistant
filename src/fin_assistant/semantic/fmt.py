"""Hiển thị kết quả bằng tiếng Việt — kỳ luôn đứng ngay cạnh con số (yêu cầu demo M5)."""

from __future__ import annotations

from .catalog import METRICS
from .result import MetricResult, Status


def _vn_number(value: float, decimals: int) -> str:
    """1234567.891 → '1.234.567,89' (dấu chấm phân tách nghìn, dấu phẩy thập phân)."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


def format_value(value: float | None, unit: str | None) -> str:
    if value is None:
        return "—"
    if unit == "VND":
        return f"{_vn_number(value / 1e9, 1)} tỷ đồng"
    if unit == "ratio":
        return f"{_vn_number(value * 100, 2)}%"
    if unit == "pp":
        sign = "+" if value > 0 else ""
        return f"{sign}{_vn_number(value * 100, 2)} điểm %"
    return _vn_number(value, 2)


def _metric_name(metric_id: str) -> str:
    base, _, transform = metric_id.rpartition("_")
    if metric_id in METRICS:
        return METRICS[metric_id].name_vi
    if transform == "yoy" and base in METRICS:
        return f"Tăng trưởng {METRICS[base].name_vi.lower()} so với cùng kỳ"
    return metric_id


def describe(result: MetricResult) -> str:
    """Một dòng mô tả: '<chỉ số> <kỳ> của <mã>: <giá trị>' hoặc lý do không trả số."""
    name = _metric_name(result.metric)
    where = f"{name} {result.period or ''} của {result.ticker}".replace("  ", " ")
    if result.status is Status.OK:
        text = f"{where}: {format_value(result.value, result.unit)}"
    else:
        reasons = " ".join(w.message for w in result.warnings if w.severity == "warning")
        text = f"{where}: không trả số ({result.status.value}). {reasons}".rstrip()
    extra = [w.message for w in result.warnings if result.status is Status.OK and w.severity == "warning"]
    if extra:
        text += " ⚠ " + " ".join(extra)
    return text
