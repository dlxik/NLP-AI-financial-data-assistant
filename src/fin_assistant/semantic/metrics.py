"""Engine tính chỉ số (lớp 1–3) với quy tắc số liệu khó 4.3 và thời gian 4.4.

Một lời gọi = (chỉ số, mã, kỳ, cửa sổ, phép so sánh). Điều phối (kiểm tra mã, nhóm doanh nghiệp,
kỳ gần nhất, nhiều mã) nằm ở :mod:`fin_assistant.semantic.api`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .catalog import (
    BANK_REVENUE_CANDIDATES,
    CHANGE_LAG,
    FLOW,
    ITEMS,
    METRICS,
    STOCK,
    WINDOW_Q,
    WINDOW_TTM,
    WINDOW_YTD,
    MetricDef,
    Transform,
)
from .fmt import format_value
from .periods import Period, to_date
from .result import InputRef, MetricResult, MetricWarning, Status, WarnCode
from .rules import RuleConfig, growth_rate, safe_ratio
from .store import Fact, FactStore


def _fmt_vnd(value: float) -> str:
    return format_value(value, "VND")


def _item_of(ref: str) -> str:
    """Tên chỉ số lớp 1 → item_code; item_code giữ nguyên."""
    if ref in METRICS:
        code = METRICS[ref].item_code
        assert code is not None
        return code
    return ref


def _name(item_code: str) -> str:
    return ITEMS[item_code].name_vi if item_code in ITEMS else item_code


def window_label(window: str, period: Period) -> str:
    if window == WINDOW_YTD:
        return f"lũy kế {period.quarter * 3} tháng {period.year}"
    if window == WINDOW_TTM:
        return f"4 quý đến {period.label()}"
    return period.label()


class _Collector:
    """Gom ô số đầu vào và cảnh báo cụ thể trong quá trình tính một chỉ số."""

    def __init__(self, store: FactStore, ticker: str, as_of: date | str | None) -> None:
        self.store = store
        self.ticker = ticker.upper()
        self.as_of = to_date(as_of)
        self.inputs: list[InputRef] = []
        self.warnings: list[MetricWarning] = []

    # --- cảnh báo -------------------------------------------------------------
    def warn(
        self,
        code: WarnCode,
        message: str,
        *,
        period: Period | None = None,
        item_code: str | None = None,
        severity: str = "warning",
    ) -> None:
        self.warnings.append(
            MetricWarning(
                code=code,
                message=message,
                ticker=self.ticker,
                period=period.label() if period else None,
                item_code=item_code,
                severity=severity,
            )
        )

    def missing(self, item_code: str, period: Period) -> None:
        """Phân biệt 'chưa công bố tại ngày hỏi' (T3) với 'khoảng trống dữ liệu'."""
        not_ended = self.as_of is not None and period.end_date() >= self.as_of
        if not_ended or self.store.is_published_later(self.ticker, period, self.as_of):
            self.warn(
                WarnCode.NOT_YET_PUBLISHED,
                f"{self.ticker}: BCTC {period.label()} chưa được công bố tại ngày hỏi {self.as_of}"
                f" — không có '{_name(item_code)}'.",
                period=period,
                item_code=item_code,
            )
        else:
            self.warn(
                WarnCode.MISSING_INPUT,
                f"{self.ticker}: thiếu số liệu '{_name(item_code)}' kỳ {period.label()}.",
                period=period,
                item_code=item_code,
            )

    # --- ô số -----------------------------------------------------------------
    def record(self, fact: Fact) -> float:
        self.inputs.append(
            InputRef(
                item_code=fact.item_code,
                ticker=fact.ticker,
                period=fact.period.label() if fact.period_type == "Q" else f"YTD {fact.period.label()}",
                value=fact.value,
                unit=fact.unit,
                source_ref=fact.source_ref,
                report_version=fact.report_version,
                as_of_date=fact.as_of_date.isoformat(),
                is_restated=fact.is_restated,
                derived_from=fact.derived_from,
            )
        )
        if fact.is_restated:
            self.warn(
                WarnCode.RESTATED_VALUE,
                f"{self.ticker}: '{_name(fact.item_code)}' {fact.period.label()} là số đã điều chỉnh hồi tố "
                f"(phiên bản {fact.report_version}, công bố {fact.as_of_date.isoformat()}).",
                period=fact.period,
                item_code=fact.item_code,
                severity="info",
            )
        if fact.derived_from:
            self.warn(
                WarnCode.DERIVED_VALUE,
                f"{self.ticker}: '{_name(fact.item_code)}' {fact.period.label()} là số suy ra ({fact.derived_from}).",
                period=fact.period,
                item_code=fact.item_code,
                severity="info",
            )
        return fact.value

    def fetch(
        self, item_code: str, period: Period, *, emit_missing: bool = True, period_type: str = "Q"
    ) -> float | None:
        fact = self.store.lookup(self.ticker, item_code, period, as_of=self.as_of, period_type=period_type)
        if fact is None:
            if emit_missing:
                self.missing(item_code, period)
            return None
        return self.record(fact)

    def equity_parent(self, period: Period, *, emit_missing: bool = True) -> float | None:
        """VCSH cổ đông mẹ: dùng BS.EQUITY_PARENT; nếu không có thì 400 − 429 (cả hai phải có)."""
        direct = self.store.lookup(self.ticker, "BS.EQUITY_PARENT", period, as_of=self.as_of)
        if direct is not None:
            return self.record(direct)
        total = self.store.lookup(self.ticker, "BS.EQUITY_TOTAL", period, as_of=self.as_of)
        nci = self.store.lookup(self.ticker, "BS.NCI", period, as_of=self.as_of)
        if total is not None and nci is not None:
            value = self.record(total) - self.record(nci)
            self.warn(
                WarnCode.DERIVED_VALUE,
                f"{self.ticker}: VCSH cổ đông mẹ {period.label()} = VCSH − lợi ích CĐ không kiểm soát.",
                period=period,
                item_code="BS.EQUITY_PARENT",
                severity="info",
            )
            return value
        if emit_missing:
            self.missing("BS.EQUITY_PARENT", period)
        return None

    # --- dựng kết quả ---------------------------------------------------------
    def result(
        self,
        metric: str,
        period: Period | None,
        status: Status,
        *,
        value: float | None = None,
        unit: str | None = None,
        formula: str = "",
        candidates: tuple[str, ...] = (),
        details: dict | None = None,
    ) -> MetricResult:
        return MetricResult(
            metric=metric,
            ticker=self.ticker,
            period=period.label() if period else None,
            status=status,
            value=value if status is Status.OK else None,
            unit=unit,
            formula=formula,
            inputs=tuple(self.inputs),
            warnings=tuple(self.warnings),
            candidates=candidates,
            details=details or {},
        )


@dataclass
class _Val:
    status: Status
    value: float | None = None
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lớp 1 + cửa sổ (lớp 3)
# ---------------------------------------------------------------------------
def _flow(c: _Collector, item_code: str, period: Period, window: str) -> float | None:
    """Giá trị flow theo cửa sổ. Thiếu bất kỳ quý nào → None (không ngoại suy — R7)."""
    if window == WINDOW_Q:
        return c.fetch(item_code, period)
    if window == WINDOW_YTD:
        # Ưu tiên cột "Lũy kế từ đầu năm" đúng như trên BCTC (T6); không có thì cộng các quý.
        reported = c.fetch(item_code, period, emit_missing=False, period_type="YTD")
        if reported is not None:
            return reported
        quarters = [Period(period.year, q) for q in range(1, period.quarter + 1)]
    else:  # TTM
        quarters = list(period.ttm_window())
    values = [c.fetch(item_code, p) for p in quarters]
    if any(v is None for v in values):
        return None
    if window == WINDOW_YTD and len(quarters) > 1:
        c.warn(
            WarnCode.DERIVED_VALUE,
            f"{c.ticker}: '{_name(item_code)}' {window_label(window, period)} = tổng các quý "
            f"{quarters[0].label()}..{quarters[-1].label()} (không có dòng lũy kế công bố).",
            period=period,
            item_code=item_code,
            severity="info",
        )
    return sum(v for v in values if v is not None)


def _stock(c: _Collector, item_code: str, period: Period, *, emit_missing: bool = True) -> float | None:
    if item_code == "BS.EQUITY_PARENT":
        return c.equity_parent(period, emit_missing=emit_missing)
    return c.fetch(item_code, period, emit_missing=emit_missing)


def _average_stock(
    c: _Collector, item_code: str, period: Period, config: RuleConfig
) -> tuple[bool, dict[Period, float], str]:
    """Số dư bình quân (R5) với quy tắc thiếu đầu kỳ (R6). Trả (đủ dữ liệu?, điểm dùng, phương pháp)."""
    if config.equity_avg_method == "two_point":
        points: tuple[Period, ...] = (period.shift(-4), period)
    else:
        points = tuple(period.shift(k) for k in range(-4, 1))
    values = {p: _stock(c, item_code, p, emit_missing=False) for p in points}
    missing = [p for p, v in values.items() if v is None]
    fallback = bool(missing) and config.allow_ending_equity_fallback and values[period] is not None
    if fallback:
        c.warn(
            WarnCode.FALLBACK_ENDING_EQUITY,
            f"{c.ticker}: thiếu '{_name(item_code)}' kỳ {', '.join(p.label() for p in missing)} — "
            f"dùng số cuối kỳ {period.label()} thay cho số bình quân.",
            period=missing[0],
            item_code=item_code,
        )
        return True, {period: values[period]}, "ending_only"  # type: ignore[dict-item]
    for p in missing:
        c.missing(item_code, p)
    used = {p: v for p, v in values.items() if v is not None}
    return not missing, used, config.equity_avg_method


def _ratio_warn(c: _Collector, outcome_code: WarnCode | None, mdef: MetricDef, period: Period,
                den_item: str, den_value: float, value: float | None) -> None:
    if outcome_code is WarnCode.NON_POSITIVE_BASE:
        c.warn(outcome_code,
               f"{c.ticker}: mẫu số '{_name(den_item)}' {period.label()} = {_fmt_vnd(den_value)} ≤ 0 — "
               f"'{mdef.name_vi}' không xác định.", period=period, item_code=den_item)
    elif outcome_code is WarnCode.NEGATIVE_EQUITY:
        c.warn(outcome_code,
               f"{c.ticker}: vốn chủ sở hữu {period.label()} = {_fmt_vnd(den_value)} ≤ 0 — "
               f"'{mdef.name_vi}' không xác định.", period=period, item_code=den_item)
    elif outcome_code is WarnCode.DENOMINATOR_NEAR_ZERO:
        c.warn(outcome_code,
               f"{c.ticker}: mẫu số '{_name(den_item)}' {period.label()} = {_fmt_vnd(den_value)} gần 0 — "
               f"'{mdef.name_vi}' không có ý nghĩa.", period=period, item_code=den_item)
    elif outcome_code is WarnCode.EXTREME_VALUE:
        c.warn(outcome_code,
               f"{c.ticker}: '{mdef.name_vi}' {period.label()} = {format_value(value, mdef.unit)} — "
               f"mẫu số rất nhỏ so với tử số, cần đọc thận trọng.", period=period, item_code=den_item)


def _metric_value(c: _Collector, mdef: MetricDef, period: Period, window: str, config: RuleConfig) -> _Val:
    """Giá trị một chỉ số (lớp 1 hoặc 2) tại một kỳ, theo cửa sổ."""
    if mdef.kind == FLOW:
        v = _flow(c, _item_of(mdef.id), period, window)
        return _Val(Status.OK, v) if v is not None else _Val(Status.MISSING_DATA)
    if mdef.kind == STOCK:
        v = _stock(c, _item_of(mdef.id), period)
        return _Val(Status.OK, v) if v is not None else _Val(Status.MISSING_DATA)

    assert mdef.numerator and mdef.denominator
    num_item, den_item = _item_of(mdef.numerator), _item_of(mdef.denominator)

    if mdef.kind == "ratio_window":
        num = _flow(c, num_item, period, window)
        den = _flow(c, den_item, period, window)
        if num is None or den is None:
            return _Val(Status.MISSING_DATA)
        details = {"numerator": num, "denominator": den}
        outcome = safe_ratio(num, den, config)
        _ratio_warn(c, outcome.code, mdef, period, den_item, den, outcome.value)
        return _Val(outcome.status, outcome.value, details)

    if mdef.kind == "ratio_stock":
        num = _stock(c, num_item, period)
        den = _stock(c, den_item, period)
        if num is None or den is None:
            return _Val(Status.MISSING_DATA)
        details = {"numerator": num, "denominator": den}
        outcome = safe_ratio(num, den, config, non_positive_code=WarnCode.NEGATIVE_EQUITY)
        _ratio_warn(c, outcome.code, mdef, period, den_item, den, outcome.value)
        return _Val(outcome.status, outcome.value, details)

    # ratio_ttm: Σ flow 4 quý / stock bình quân (ROE, ROA) — R4–R7
    num = _flow(c, num_item, period, WINDOW_TTM)
    ok, used, method = _average_stock(c, den_item, period, config)
    if num is None or not ok:
        return _Val(Status.MISSING_DATA)
    is_equity = den_item.startswith("BS.EQUITY")
    details: dict = {
        "numerator_ttm": num,
        "denominator_points": {p.label(): v for p, v in used.items()},
        "avg_method": method,
    }
    non_positive = [(p, v) for p, v in used.items() if v <= 0]
    if non_positive:
        listing = "; ".join(f"{p.label()}: {_fmt_vnd(v)}" for p, v in non_positive)
        code = WarnCode.NEGATIVE_EQUITY if is_equity else WarnCode.NON_POSITIVE_BASE
        c.warn(code,
               f"{c.ticker}: '{_name(den_item)}' ≤ 0 ({listing}) — '{mdef.name_vi}' không xác định, "
               f"không so sánh/xếp hạng chỉ số này của mã.", period=non_positive[0][0], item_code=den_item)
        return _Val(Status.NOT_MEANINGFUL, None, details)
    avg = sum(used.values()) / len(used)
    details["denominator_avg"] = avg
    outcome = safe_ratio(num, avg, config)
    _ratio_warn(c, outcome.code, mdef, period, den_item, avg, outcome.value)
    return _Val(outcome.status, outcome.value, details)


def _formula(mdef: MetricDef, period: Period, t: Transform, config: RuleConfig) -> str:
    if mdef.kind == "ratio_ttm":
        n = 2 if config.equity_avg_method == "two_point" else 5
        base = f"{mdef.formula_vi} ({window_label(WINDOW_TTM, period)}; bình quân {n} điểm)"
    else:
        base = f"{mdef.formula_vi} — {window_label(t.window, period)}"
    if t.change is None:
        return base
    ref = period.shift(CHANGE_LAG[t.change])
    if t.pp:
        return f"[{base}] − [cùng chỉ số kỳ {window_label(t.window, ref)}] (điểm %)"
    return f"([{base}] − [kỳ {window_label(t.window, ref)}]) / [kỳ {window_label(t.window, ref)}]"


def compute(
    store: FactStore,
    mdef: MetricDef,
    ticker: str,
    period: Period,
    t: Transform,
    as_of: date | str | None,
    config: RuleConfig,
) -> MetricResult:
    """Tính chỉ số đã qua kiểm tra danh mục/nhóm, tại kỳ đã xác định."""
    metric_id = f"{mdef.id}_{t.name}" if t.name else mdef.id
    formula = _formula(mdef, period, t, config)
    c = _Collector(store, ticker, as_of)

    if t.change is None:
        val = _metric_value(c, mdef, period, t.window, config)
        details = dict(val.details, window=t.window)
        return c.result(metric_id, period, val.status, value=val.value, unit=mdef.unit,
                        formula=formula, details=details)

    ref = period.shift(CHANGE_LAG[t.change])
    unit = "pp" if t.pp else "ratio"
    cur = _metric_value(c, mdef, period, t.window, config)
    base = _metric_value(c, mdef, ref, t.window, config)
    details = {"window": t.window, "current": cur.value, "base": base.value, "base_period": ref.label()}
    # Một đầu không xác định → phép so sánh không xác định dù đầu kia có đủ dữ liệu hay không.
    for status in (Status.NOT_MEANINGFUL, Status.MISSING_DATA):
        if status in (cur.status, base.status):
            return c.result(metric_id, period, status, unit=unit, formula=formula, details=details)
    assert cur.value is not None and base.value is not None
    details["abs_change"] = cur.value - base.value

    if t.pp:
        return c.result(metric_id, period, Status.OK, value=cur.value - base.value, unit=unit,
                        formula=formula, details=details)

    outcome = growth_rate(cur.value, base.value, config)
    where = window_label(t.window, ref)
    if outcome.code is WarnCode.NON_POSITIVE_BASE:
        c.warn(outcome.code,
               f"{c.ticker}: {mdef.name_vi} kỳ gốc {where} = {_fmt_vnd(base.value)} ≤ 0 — tăng trưởng % "
               f"không xác định; chênh lệch tuyệt đối = {_fmt_vnd(cur.value - base.value)}.",
               period=ref, item_code=mdef.item_code)
    elif outcome.code is WarnCode.DENOMINATOR_NEAR_ZERO:
        c.warn(outcome.code,
               f"{c.ticker}: {mdef.name_vi} kỳ gốc {where} = {_fmt_vnd(base.value)} gần 0 "
               f"(< ngưỡng {_fmt_vnd(config.near_zero_abs_vnd)}) — tăng trưởng % không có ý nghĩa.",
               period=ref, item_code=mdef.item_code)
    elif outcome.code is WarnCode.EXTREME_VALUE:
        c.warn(outcome.code,
               f"{c.ticker}: tăng trưởng {mdef.name_vi} {window_label(t.window, period)} so với {where} "
               f"là {outcome.value:.0%} — kỳ gốc nhỏ, cần đọc thận trọng.",
               period=period, item_code=mdef.item_code)
    return c.result(metric_id, period, outcome.status, value=outcome.value, unit=unit,
                    formula=formula, details=details)


# ---------------------------------------------------------------------------
# "Doanh thu thuần" của ngân hàng (R9)
# ---------------------------------------------------------------------------
def bank_revenue_clarification(
    store: FactStore, metric_id: str, ticker: str, period: Period | None
) -> MetricResult:
    """Ngân hàng không có dòng "Doanh thu thuần": hỏi làm rõ, liệt kê ứng viên, không trả số."""
    c = _Collector(store, ticker, None)
    options = "; ".join(f"'{METRICS[m].name_vi}' ({m})" for m in BANK_REVENUE_CANDIDATES)
    c.warn(
        WarnCode.BANK_NO_NET_REVENUE,
        f"{c.ticker} là ngân hàng: Báo cáo kết quả hoạt động của tổ chức tín dụng không có chỉ tiêu "
        f"'Doanh thu thuần'. Hệ thống không tự thay bằng chỉ tiêu khác — bạn muốn xem: {options}?",
        period=period,
        item_code="IS.NET_REVENUE",
    )
    return c.result(
        metric_id,
        period,
        Status.NEEDS_CLARIFICATION,
        formula="(không áp dụng — cần làm rõ chỉ tiêu)",
        candidates=BANK_REVENUE_CANDIDATES,
    )
