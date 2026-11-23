"""Bộ hàm pilot cho 3 đại lượng (Giai đoạn 1, TV2).

1. Doanh thu thuần quý & tăng trưởng YoY — nhóm phi tài chính.
2. ROE TTM — cả phi tài chính và ngân hàng.
3. "Doanh thu thuần" hỏi cho ngân hàng — trả yêu cầu làm rõ, **không** tự thay bằng thu nhập
   lãi thuần hay chỉ tiêu nào khác.

Các hàm ở đây nhận kỳ đã chuẩn hóa; điều phối (kỳ gần nhất, kiểm tra nhóm, nhiều mã) nằm ở
:mod:`fin_assistant.semantic.api`.
"""

from __future__ import annotations

from datetime import date

from .catalog import BANK_REVENUE_CANDIDATES, ITEMS, METRICS, MetricDef
from .fmt import format_value
from .periods import Period, to_date
from .result import InputRef, MetricResult, MetricWarning, Status, WarnCode
from .rules import RuleConfig, growth_rate, safe_ratio
from .store import Fact, FactStore


def _fmt_vnd(value: float) -> str:
    return format_value(value, "VND")


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
        name = ITEMS[item_code].name_vi if item_code in ITEMS else item_code
        not_ended = self.as_of is not None and period.end_date() >= self.as_of
        if not_ended or self.store.is_published_later(self.ticker, period, self.as_of):
            self.warn(
                WarnCode.NOT_YET_PUBLISHED,
                f"{self.ticker}: BCTC {period.label()} chưa được công bố tại ngày hỏi {self.as_of}"
                f" — không có '{name}'.",
                period=period,
                item_code=item_code,
            )
        else:
            self.warn(
                WarnCode.MISSING_INPUT,
                f"{self.ticker}: thiếu số liệu '{name}' kỳ {period.label()}.",
                period=period,
                item_code=item_code,
            )

    # --- ô số -----------------------------------------------------------------
    def record(self, fact: Fact) -> float:
        self.inputs.append(
            InputRef(
                item_code=fact.item_code,
                ticker=fact.ticker,
                period=fact.period.label(),
                value=fact.value,
                unit=fact.unit,
                source_ref=fact.source_ref,
                report_version=fact.report_version,
                as_of_date=fact.as_of_date.isoformat(),
                is_restated=fact.is_restated,
                derived_from=fact.derived_from,
            )
        )
        name = ITEMS[fact.item_code].name_vi if fact.item_code in ITEMS else fact.item_code
        if fact.is_restated:
            self.warn(
                WarnCode.RESTATED_VALUE,
                f"{self.ticker}: '{name}' {fact.period.label()} là số đã điều chỉnh hồi tố "
                f"(phiên bản {fact.report_version}, công bố {fact.as_of_date.isoformat()}).",
                period=fact.period,
                item_code=fact.item_code,
                severity="info",
            )
        if fact.derived_from:
            self.warn(
                WarnCode.DERIVED_VALUE,
                f"{self.ticker}: '{name}' {fact.period.label()} là số suy ra ({fact.derived_from}).",
                period=fact.period,
                item_code=fact.item_code,
                severity="info",
            )
        return fact.value

    def fetch(self, item_code: str, period: Period, *, emit_missing: bool = True) -> float | None:
        fact = self.store.lookup(self.ticker, item_code, period, as_of=self.as_of)
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


# ---------------------------------------------------------------------------
# Lớp 1 — trường gốc theo quý
# ---------------------------------------------------------------------------
def _base_fetch(c: _Collector, mdef: MetricDef, period: Period) -> float | None:
    assert mdef.item_code is not None
    if mdef.item_code == "BS.EQUITY_PARENT":
        return c.equity_parent(period)
    return c.fetch(mdef.item_code, period)


def base_value(
    store: FactStore, mdef: MetricDef, ticker: str, period: Period, as_of: date | str | None
) -> MetricResult:
    """Giá trị quý đơn lẻ (flow) hoặc số dư cuối quý (stock) của một trường gốc."""
    c = _Collector(store, ticker, as_of)
    value = _base_fetch(c, mdef, period)
    if value is None:
        return c.result(mdef.id, period, Status.MISSING_DATA, unit=mdef.unit, formula=mdef.formula_vi)
    return c.result(mdef.id, period, Status.OK, value=value, unit=mdef.unit, formula=mdef.formula_vi)


# ---------------------------------------------------------------------------
# Lớp 3 — tăng trưởng YoY
# ---------------------------------------------------------------------------
def yoy(
    store: FactStore,
    mdef: MetricDef,
    ticker: str,
    period: Period,
    as_of: date | str | None,
    config: RuleConfig,
) -> MetricResult:
    """Tăng trưởng so với cùng kỳ năm trước, dạng tỷ lệ (0,15 = +15%)."""
    metric_id = f"{mdef.id}_yoy"
    base_period = period.same_quarter_last_year()
    formula = f"({mdef.name_vi} {period.label()} − {mdef.name_vi} {base_period.label()}) / {mdef.name_vi} {base_period.label()}"
    c = _Collector(store, ticker, as_of)
    current = _base_fetch(c, mdef, period)
    base = _base_fetch(c, mdef, base_period)
    if current is None or base is None:
        return c.result(metric_id, period, Status.MISSING_DATA, unit="ratio", formula=formula)

    details = {
        "current": current,
        "base": base,
        "base_period": base_period.label(),
        "abs_change": current - base,
    }
    outcome = growth_rate(current, base, config)
    if outcome.code is WarnCode.NON_POSITIVE_BASE:
        c.warn(
            outcome.code,
            f"{c.ticker}: {mdef.name_vi} kỳ gốc {base_period.label()} = {_fmt_vnd(base)} ≤ 0 — "
            f"tăng trưởng % không xác định; chênh lệch tuyệt đối = {_fmt_vnd(current - base)}.",
            period=base_period,
            item_code=mdef.item_code,
        )
    elif outcome.code is WarnCode.DENOMINATOR_NEAR_ZERO:
        c.warn(
            outcome.code,
            f"{c.ticker}: {mdef.name_vi} kỳ gốc {base_period.label()} = {_fmt_vnd(base)} gần 0 "
            f"(< ngưỡng {_fmt_vnd(config.near_zero_abs_vnd)}) — tăng trưởng % không có ý nghĩa.",
            period=base_period,
            item_code=mdef.item_code,
        )
    elif outcome.code is WarnCode.EXTREME_VALUE:
        c.warn(
            outcome.code,
            f"{c.ticker}: tăng trưởng {mdef.name_vi} {period.label()} so với {base_period.label()} "
            f"là {outcome.value:.0%} — kỳ gốc nhỏ, cần đọc thận trọng.",
            period=period,
            item_code=mdef.item_code,
        )
    return c.result(
        metric_id, period, outcome.status, value=outcome.value, unit="ratio", formula=formula, details=details
    )


# ---------------------------------------------------------------------------
# Lớp 2 — ROE TTM
# ---------------------------------------------------------------------------
def roe_ttm(
    store: FactStore, ticker: str, period: Period, as_of: date | str | None, config: RuleConfig
) -> MetricResult:
    """ROE TTM = Σ LNST cổ đông mẹ 4 quý (t−3..t) / VCSH cổ đông mẹ bình quân.

    - VCSH bình quân 2 điểm: (VCSH cuối t−4 + VCSH cuối t) / 2  (mặc định, R5);
      5 điểm: trung bình VCSH cuối các quý t−4..t.
    - Thiếu bất kỳ quý LNST nào → báo thiếu (không nhân 4 / không quy đổi năm từ ít quý hơn).
    - Thiếu VCSH đầu kỳ → báo thiếu; chỉ khi ``allow_ending_equity_fallback`` mới dùng VCSH
      cuối kỳ, kèm cảnh báo FALLBACK_ENDING_EQUITY (R6).
    - Bất kỳ điểm VCSH nào ≤ 0 → ROE không xác định (NEGATIVE_EQUITY, R4).
    """
    mdef = METRICS["roe_ttm"]
    c = _Collector(store, ticker, as_of)
    window = period.ttm_window()
    if config.equity_avg_method == "two_point":
        eq_periods: tuple[Period, ...] = (period.shift(-4), period)
    else:
        eq_periods = tuple(period.shift(k) for k in range(-4, 1))
    formula = (
        f"Σ LNST cổ đông mẹ ({window[0].label()}..{window[-1].label()}) / "
        f"VCSH cổ đông mẹ bình quân {len(eq_periods)} điểm ({eq_periods[0].label()}..{eq_periods[-1].label()})"
    )

    npats = [c.fetch("IS.NPAT_PARENT", p) for p in window]
    equities = {p: c.equity_parent(p, emit_missing=False) for p in eq_periods}
    missing_eq = [p for p, v in equities.items() if v is None]

    used: dict[Period, float]
    fallback = bool(missing_eq) and config.allow_ending_equity_fallback and equities[period] is not None
    if fallback:
        used = {period: equities[period]}  # type: ignore[dict-item]
        formula = (
            f"Σ LNST cổ đông mẹ ({window[0].label()}..{window[-1].label()}) / "
            f"VCSH cổ đông mẹ cuối kỳ {period.label()} (thay thế do thiếu đầu kỳ)"
        )
        c.warn(
            WarnCode.FALLBACK_ENDING_EQUITY,
            f"{c.ticker}: thiếu VCSH cổ đông mẹ kỳ {', '.join(p.label() for p in missing_eq)} — "
            f"ROE tính trên VCSH cuối kỳ {period.label()} thay cho VCSH bình quân.",
            period=missing_eq[0],
            item_code="BS.EQUITY_PARENT",
        )
    else:
        for p in missing_eq:
            c.missing("BS.EQUITY_PARENT", p)
        used = {p: v for p, v in equities.items() if v is not None}

    if any(v is None for v in npats) or (missing_eq and not fallback):
        return c.result(mdef.id, period, Status.MISSING_DATA, unit=mdef.unit, formula=formula)

    npat_ttm = sum(v for v in npats if v is not None)
    details: dict = {
        "npat_parent_ttm": npat_ttm,
        "equity_points": {p.label(): v for p, v in used.items()},
        "equity_avg_method": "ending_only" if len(used) == 1 else config.equity_avg_method,
    }

    negative = [(p, v) for p, v in used.items() if v <= 0]
    if negative:
        listing = "; ".join(f"{p.label()}: {_fmt_vnd(v)}" for p, v in negative)
        c.warn(
            WarnCode.NEGATIVE_EQUITY,
            f"{c.ticker}: vốn chủ sở hữu cổ đông mẹ ≤ 0 ({listing}) — ROE không xác định, "
            f"không so sánh/xếp hạng ROE của mã này.",
            period=negative[0][0],
            item_code="BS.EQUITY_PARENT",
        )
        return c.result(mdef.id, period, Status.NOT_MEANINGFUL, unit=mdef.unit, formula=formula, details=details)

    equity_avg = sum(used.values()) / len(used)
    details["equity_avg"] = equity_avg
    outcome = safe_ratio(npat_ttm, equity_avg, config, non_positive_code=WarnCode.NEGATIVE_EQUITY)
    if outcome.code is WarnCode.DENOMINATOR_NEAR_ZERO:
        c.warn(
            outcome.code,
            f"{c.ticker}: VCSH cổ đông mẹ bình quân = {_fmt_vnd(equity_avg)} gần 0 — ROE không có ý nghĩa.",
            period=period,
            item_code="BS.EQUITY_PARENT",
        )
    elif outcome.code is WarnCode.EXTREME_VALUE:
        c.warn(
            outcome.code,
            f"{c.ticker}: ROE TTM {period.label()} = {outcome.value:.0%} — VCSH rất nhỏ so với lợi nhuận, "
            f"cần đọc thận trọng.",
            period=period,
            item_code="BS.EQUITY_PARENT",
        )
    return c.result(
        mdef.id, period, outcome.status, value=outcome.value, unit=mdef.unit, formula=formula, details=details
    )


# ---------------------------------------------------------------------------
# Ca 3 — "doanh thu thuần" của ngân hàng
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
