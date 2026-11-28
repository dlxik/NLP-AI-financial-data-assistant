"""Hiển thị kết quả bằng tiếng Việt — kỳ luôn đứng ngay cạnh con số (yêu cầu demo M5)."""

from __future__ import annotations

from .catalog import METRICS, TransformError, parse_transform
from .result import MetricResult, MultiResult, Status


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
    if unit == "times":
        return f"{_vn_number(value, 2)} lần"
    return _vn_number(value, 2)


def metric_name(metric_id: str) -> str:
    """Tên tiếng Việt của ``metric[_transform]``, vd ``net_revenue_ytd_yoy``."""
    for mid in sorted(METRICS, key=len, reverse=True):
        name = METRICS[mid].name_vi
        if metric_id == mid:
            return name
        if not metric_id.startswith(mid + "_"):
            continue
        try:
            t = parse_transform(metric_id[len(mid) + 1:])
        except TransformError:
            continue
        if t.change == "yoy":
            return (f"Thay đổi {name[0].lower() + name[1:]} so với cùng kỳ" if t.pp
                    else f"Tăng trưởng {name[0].lower() + name[1:]} so với cùng kỳ")
        if t.change == "qoq":
            return (f"Thay đổi {name[0].lower() + name[1:]} so với quý trước" if t.pp
                    else f"Tăng trưởng {name[0].lower() + name[1:]} so với quý trước")
        return name
    return metric_id


def period_text(result: MetricResult) -> str:
    """Nhãn kỳ đứng cạnh con số: 'Q3/2024', 'lũy kế 9 tháng 2024', '4 quý đến Q3/2024'."""
    if not result.period:
        return ""
    window = result.details.get("window")
    if window == "ytd":
        q, year = result.period[1], result.period[3:]
        return f"lũy kế {int(q) * 3} tháng {year}"
    if window == "ttm":
        return f"4 quý đến {result.period}"
    return result.period


def describe(result: MetricResult) -> str:
    """Một dòng mô tả: '<chỉ số> <kỳ> của <mã>: <giá trị>' hoặc lý do không trả số."""
    name = metric_name(result.metric)
    where = f"{name} {period_text(result)} của {result.ticker}".replace("  ", " ")
    if result.status is Status.OK:
        text = f"{where}: {format_value(result.value, result.unit)}"
    else:
        reasons = " ".join(w.message for w in result.warnings if w.severity == "warning")
        text = f"{where}: không trả số ({result.status.value}). {reasons}".rstrip()
    extra = [w.message for w in result.warnings if result.status is Status.OK and w.severity == "warning"]
    if extra:
        text += " ⚠ " + " ".join(extra)
    return text


def describe_multi(result: MultiResult) -> str:
    """Nhiều dòng: mỗi mã một dòng (kèm hạng nếu có), rồi các cảnh báo chung."""
    lines: list[str] = []
    if result.status is Status.EMPTY_VALID:
        lines.append("Không có mã nào thỏa điều kiện (đã đánh giá đủ các mã).")
    for r in result.rows:
        prefix = f"{r.details['rank']}. " if "rank" in r.details else "- "
        lines.append(prefix + describe(r))
    for r in result.excluded:
        lines.append("× " + describe(r))
    lines += [f"⚠ {w.message}" for w in result.warnings]
    return "\n".join(lines)
