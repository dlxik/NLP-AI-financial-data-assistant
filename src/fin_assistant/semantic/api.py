"""Giao diện công khai của semantic layer: ``get_metric``, ``get_metric_multi``, ``rank``, ``screen``.

Đây là điểm gọi chung cho B0, phương pháp B (LLM sinh code gọi thư viện) và bộ thực thi C.
Thứ tự kiểm tra trong ``get_metric`` là cố định (đặc tả, mục 6):

1. Mã chỉ số / phép biến đổi có trong danh mục không (lỗi lập trình → ngoại lệ).
2. Mã cổ phiếu có trong phạm vi dữ liệu không → NOT_APPLICABLE.
3. Ngân hàng + chỉ số cần làm rõ ("doanh thu thuần") → NEEDS_CLARIFICATION.
4. Chỉ số có áp dụng cho nhóm doanh nghiệp không → NOT_APPLICABLE.
5. Xác định kỳ ("latest" → kỳ gần nhất đã công bố tại ngày hỏi).
6. Tính toán + quy tắc số liệu khó.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Iterable, Sequence

from .catalog import BANK, BANK_CLARIFY_METRICS, GROUPS, METRICS, Transform, check_transform, parse_transform
from .metrics import bank_revenue_clarification, compute
from .periods import LATEST, Period, PeriodLike, to_date
from .result import MetricResult, MetricWarning, MultiResult, Status, WarnCode
from .rules import DEFAULT_RULES, SCREEN_OPS, RuleConfig, compare
from .store import FactStore


class UnknownMetricError(KeyError):
    """Chỉ số không có trong danh mục (bộ phân tích phải kiểm tra trước)."""


def _check_metric(metric: str, transform: str | None) -> Transform:
    if metric not in METRICS:
        raise UnknownMetricError(f"chỉ số không có trong danh mục: {metric!r}; có: {sorted(METRICS)}")
    t = parse_transform(transform)
    check_transform(METRICS[metric], t)
    return t


def _simple(metric_id: str, ticker: str, status: Status, code: WarnCode, message: str,
            period: str | None = None) -> MetricResult:
    return MetricResult(
        metric=metric_id,
        ticker=ticker.upper(),
        period=period,
        status=status,
        warnings=(MetricWarning(code=code, message=message, ticker=ticker.upper(), period=period),),
    )


def get_metric(
    store: FactStore,
    metric: str,
    ticker: str,
    period: PeriodLike = LATEST,
    *,
    transform: str | None = None,
    as_of: date | str | None = None,
    config: RuleConfig | None = None,
) -> MetricResult:
    """Tính một chỉ số cho một mã tại một kỳ.

    Args:
        metric: mã chỉ số trong :data:`catalog.METRICS` (vd ``"net_revenue"``, ``"roe_ttm"``).
        ticker: mã cổ phiếu.
        period: ``Period``, chuỗi ``"2024Q3"`` / ``"Q3/2024"``, hoặc ``"latest"``.
        transform: phép biến đổi lớp 3, cú pháp ``[ytd|ttm][_][yoy|qoq][_pp]``
            (vd ``"yoy"``, ``"ytd"``, ``"ttm_yoy"``, ``"yoy_pp"``); ``None`` = quý đơn lẻ.
        as_of: ngày hỏi (``question_date``); chỉ dùng số liệu đã công bố tới ngày này.
        config: bộ ngưỡng quy tắc; mặc định :data:`rules.DEFAULT_RULES`.

    Raises:
        UnknownMetricError: chỉ số không có trong danh mục.
        TransformError: phép biến đổi sai cú pháp / không áp dụng cho chỉ số.
    """
    t = _check_metric(metric, transform)
    config = config or DEFAULT_RULES
    mdef = METRICS[metric]
    metric_id = f"{metric}_{t.name}" if t.name else metric
    ticker = ticker.upper()
    explicit = None if isinstance(period, str) and period == LATEST else Period.parse(period)
    explicit_label = explicit.label() if explicit else None

    if not store.has_ticker(ticker):
        return _simple(
            metric_id, ticker, Status.NOT_APPLICABLE, WarnCode.OUT_OF_SCOPE_TICKER,
            f"{ticker}: mã không thuộc phạm vi dữ liệu (VN30 đủ điều kiện).", explicit_label,
        )
    group = store.group_of(ticker)
    if group == BANK and metric in BANK_CLARIFY_METRICS:
        return bank_revenue_clarification(store, metric_id, ticker, explicit)
    if group not in mdef.groups:
        return _simple(
            metric_id, ticker, Status.NOT_APPLICABLE, WarnCode.METRIC_NOT_APPLICABLE,
            f"{ticker}: chỉ số '{mdef.name_vi}' không áp dụng cho nhóm doanh nghiệp '{group}'.",
            explicit_label,
        )

    resolved = explicit
    if resolved is None:
        resolved = store.latest_period(ticker, as_of)
        if resolved is None:
            return _simple(
                metric_id, ticker, Status.MISSING_DATA, WarnCode.MISSING_INPUT,
                f"{ticker}: chưa có BCTC nào được công bố tới ngày hỏi {to_date(as_of)}.",
            )

    result = compute(store, mdef, ticker, resolved, t, as_of, config)
    if explicit is None:
        result.details["period_resolved_from"] = LATEST
    return result


# ---------------------------------------------------------------------------
# Nhiều mã
# ---------------------------------------------------------------------------
UNIVERSES = ("all", "vn30", BANK, "non_financial")


def resolve_universe(store: FactStore, spec: str) -> list[str]:
    """Nhóm mã: ``"all"``/``"vn30"`` = toàn bộ danh mục; ``"bank"``; ``"non_financial"``."""
    spec = spec.lower()
    if spec in ("all", "vn30"):
        return store.tickers()
    if spec in GROUPS:
        return store.tickers(spec)
    raise ValueError(f"nhóm mã không hợp lệ: {spec!r}; chỉ nhận {UNIVERSES}")


_NO_ANSWER_PRIORITY = (
    Status.NEEDS_CLARIFICATION,
    Status.MISSING_DATA,
    Status.NOT_MEANINGFUL,
    Status.NOT_APPLICABLE,
)


def _dedupe(tickers: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for t in tickers:
        t = t.upper()
        if t not in seen:
            seen.append(t)
    return seen


def get_metric_multi(
    store: FactStore,
    metric: str,
    tickers: Sequence[str],
    period: PeriodLike = LATEST,
    *,
    transform: str | None = None,
    as_of: date | str | None = None,
    config: RuleConfig | None = None,
) -> MultiResult:
    """Tính một chỉ số cho nhiều mã (bảng so sánh).

    "Kỳ gần nhất" khi hỏi nhiều mã (T5) theo ``config.latest_policy_multi``:

    - ``"common"`` (mặc định): kỳ gần nhất mà **mọi** mã (có dữ liệu) đã công bố; mã nào đã có
      kỳ mới hơn được gắn cảnh báo NEWER_PERIOD_AVAILABLE.
    - ``"per_ticker"``: mỗi mã lấy kỳ gần nhất của riêng nó; nếu các kỳ khác nhau → MIXED_PERIODS.
    """
    t = _check_metric(metric, transform)
    config = config or DEFAULT_RULES
    metric_id = f"{metric}_{t.name}" if t.name else metric
    tickers = _dedupe(tickers)
    warnings: list[MetricWarning] = []
    is_latest = isinstance(period, str) and period == LATEST
    policy = config.latest_policy_multi if is_latest else "explicit"

    per_ticker_period: dict[str, PeriodLike] = {tk: period for tk in tickers}
    if is_latest and policy == "common":
        latest = {tk: store.latest_period(tk, as_of) for tk in tickers if store.has_ticker(tk)}
        available = [p for p in latest.values() if p is not None]
        if available:
            common = min(available)
            for tk, p in latest.items():
                if p is not None:
                    per_ticker_period[tk] = common
                    if p > common:
                        warnings.append(MetricWarning(
                            code=WarnCode.NEWER_PERIOD_AVAILABLE,
                            message=f"{tk}: đã có BCTC {p.label()} nhưng bảng so sánh dùng kỳ chung "
                                    f"gần nhất {common.label()} của các mã.",
                            ticker=tk, period=p.label(), severity="info",
                        ))

    rows = tuple(
        get_metric(store, metric, tk, per_ticker_period[tk], transform=transform, as_of=as_of, config=config)
        for tk in tickers
    )

    if is_latest and policy == "per_ticker":
        periods = {r.period for r in rows if r.period}
        if len(periods) > 1:
            listing = ", ".join(f"{r.ticker}: {r.period}" for r in rows if r.period)
            warnings.append(MetricWarning(
                code=WarnCode.MIXED_PERIODS,
                message=f"Các mã đang ở kỳ khác nhau ({listing}) — không nên so sánh trực tiếp.",
            ))

    return MultiResult(
        metric=metric_id,
        status=_aggregate_status(rows, warnings),
        rows=rows,
        period_policy=policy,
        warnings=tuple(warnings),
    )


def _aggregate_status(rows: Sequence[MetricResult], warnings: list[MetricWarning]) -> Status:
    """OK khi có ít nhất một dòng OK (dòng lỗi được liệt kê qua PARTIAL_COVERAGE);
    câu cần làm rõ luôn được ưu tiên; không dòng nào OK → trạng thái theo thứ tự ưu tiên."""
    statuses = {r.status for r in rows}
    if Status.NEEDS_CLARIFICATION in statuses:
        return Status.NEEDS_CLARIFICATION
    not_ok = [r for r in rows if r.status is not Status.OK]
    if Status.OK in statuses:
        if not_ok:
            listing = ", ".join(f"{r.ticker} ({r.status.value})" for r in not_ok)
            warnings.append(MetricWarning(
                code=WarnCode.PARTIAL_COVERAGE,
                message=f"Không có kết quả số cho: {listing}.",
            ))
        return Status.OK
    for status in _NO_ANSWER_PRIORITY:
        if status in statuses:
            return status
    return Status.MISSING_DATA  # danh sách mã rỗng


def _exclusion_warnings(excluded: Sequence[MetricResult], base: Sequence[MetricWarning],
                        action: str) -> tuple[list[MetricWarning], list[MetricResult], list[MetricResult]]:
    """Cảnh báo cho mã bị loại khỏi phép lọc / xếp hạng: 'mềm' (không xác định, không áp dụng)
    và 'cứng' (thiếu dữ liệu)."""
    warnings = [w for w in base if w.code is not WarnCode.PARTIAL_COVERAGE]
    soft = [r for r in excluded if r.status in (Status.NOT_MEANINGFUL, Status.NOT_APPLICABLE)]
    hard = [r for r in excluded if r.status is Status.MISSING_DATA]
    if soft:
        warnings.append(MetricWarning(
            code=WarnCode.EXCLUDED_NOT_MEANINGFUL,
            message=f"Bị loại khỏi {action} vì chỉ số không xác định/không áp dụng: "
                    + ", ".join(f"{r.ticker} ({r.status.value})" for r in soft) + ".",
        ))
    if hard:
        warnings.append(MetricWarning(
            code=WarnCode.PARTIAL_COVERAGE,
            message=f"Không đánh giá được trong {action} do thiếu dữ liệu: "
                    + ", ".join(r.ticker for r in hard) + ".",
        ))
    return warnings, soft, hard


# ---------------------------------------------------------------------------
# Xếp hạng (R12)
# ---------------------------------------------------------------------------
def rank(
    store: FactStore,
    metric: str,
    tickers: Sequence[str],
    period: PeriodLike = LATEST,
    *,
    transform: str | None = None,
    order: str = "desc",
    top_n: int | None = None,
    as_of: date | str | None = None,
    config: RuleConfig | None = None,
) -> MultiResult:
    """Xếp hạng các mã theo chỉ số, trên **cùng một kỳ** (T5).

    - Chỉ dòng OK được xếp hạng; mã không xác định / không áp dụng bị loại và nêu rõ.
    - Có mã thiếu dữ liệu → vẫn xếp hạng phần còn lại nhưng gắn PARTIAL_COVERAGE (kết quả
      "cao nhất" có thể đổi nếu mã thiếu có dữ liệu).
    - Bằng nhau → giữ thứ tự theo mã (ổn định, tái lập được).
    """
    if order not in ("desc", "asc"):
        raise ValueError("order phải là 'desc' hoặc 'asc'")
    if top_n is not None and top_n < 1:
        raise ValueError("top_n phải ≥ 1")
    multi = get_metric_multi(store, metric, tickers, period, transform=transform, as_of=as_of, config=config)
    ok = sorted((r for r in multi.rows if r.status is Status.OK), key=lambda r: r.ticker)
    ok.sort(key=lambda r: r.value, reverse=(order == "desc"))  # type: ignore[arg-type,return-value]
    if top_n is not None:
        ok = ok[:top_n]
    ranked = tuple(replace(r, details={**r.details, "rank": i}) for i, r in enumerate(ok, start=1))
    excluded = tuple(r for r in multi.rows if r.status is not Status.OK)
    warnings, _, _ = _exclusion_warnings(excluded, multi.warnings, "xếp hạng")

    if any(r.status is Status.NEEDS_CLARIFICATION for r in excluded):
        status = Status.NEEDS_CLARIFICATION
    elif ranked:
        status = Status.OK
    else:
        status = next((s for s in _NO_ANSWER_PRIORITY if s in {r.status for r in excluded}), Status.MISSING_DATA)
    return MultiResult(
        metric=multi.metric, status=status, rows=ranked, period_policy=multi.period_policy,
        warnings=tuple(warnings), excluded=excluded,
    )


# ---------------------------------------------------------------------------
# Lọc theo ngưỡng — quy tắc "0 dòng" (R8)
# ---------------------------------------------------------------------------
def screen(
    store: FactStore,
    metric: str,
    tickers: Sequence[str],
    op: str,
    threshold: float,
    period: PeriodLike = LATEST,
    *,
    transform: str | None = None,
    as_of: date | str | None = None,
    config: RuleConfig | None = None,
) -> MultiResult:
    """Lọc các mã có ``chỉ số <op> threshold``.

    - Có dòng thỏa → OK; mã không đánh giá được nằm trong ``excluded`` kèm cảnh báo.
    - Không dòng nào thỏa **và** mọi mã đều đánh giá được (hoặc chỉ bị loại vì chỉ số không
      xác định / không áp dụng — đã nêu rõ) → EMPTY_VALID (0 dòng hợp lệ).
    - Không dòng nào thỏa nhưng có mã **thiếu dữ liệu** → MISSING_DATA: không được khẳng định
      "không có mã nào".
    - Có mã cần làm rõ chỉ tiêu → NEEDS_CLARIFICATION.
    """
    if op not in SCREEN_OPS:
        raise ValueError(f"phép so sánh không hỗ trợ: {op!r}; chỉ nhận {sorted(SCREEN_OPS)}")
    multi = get_metric_multi(
        store, metric, tickers, period, transform=transform, as_of=as_of, config=config
    )
    matched = tuple(r for r in multi.rows if r.status is Status.OK and compare(r.value, op, threshold))  # type: ignore[arg-type]
    excluded = tuple(r for r in multi.rows if r.status is not Status.OK)
    warnings, _, hard = _exclusion_warnings(excluded, multi.warnings, "phép lọc")

    if any(r.status is Status.NEEDS_CLARIFICATION for r in excluded):
        status = Status.NEEDS_CLARIFICATION
    elif matched:
        status = Status.OK
    elif hard or not multi.rows:
        status = Status.MISSING_DATA
    else:
        status = Status.EMPTY_VALID

    return MultiResult(
        metric=multi.metric,
        status=status,
        rows=matched,
        period_policy=multi.period_policy,
        warnings=tuple(warnings),
        excluded=excluded,
    )
