"""Giao diện công khai của semantic layer: ``get_metric``, ``get_metric_multi``, ``screen``.

Đây là điểm gọi chung cho B0, phương pháp B (LLM sinh code gọi thư viện) và bộ thực thi C.
Thứ tự kiểm tra trong ``get_metric`` là cố định (xem đặc tả mục 5):

1. Mã chỉ số / phép biến đổi có trong danh mục không (lỗi lập trình → ngoại lệ).
2. Mã cổ phiếu có trong phạm vi dữ liệu không → NOT_APPLICABLE.
3. Ngân hàng + chỉ số cần làm rõ ("doanh thu thuần") → NEEDS_CLARIFICATION.
4. Chỉ số có áp dụng cho nhóm doanh nghiệp không → NOT_APPLICABLE.
5. Xác định kỳ ("latest" → kỳ gần nhất đã công bố tại ngày hỏi).
6. Tính toán + quy tắc số liệu khó.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Sequence

from .catalog import BANK, BANK_CLARIFY_METRICS, METRICS
from .metrics import bank_revenue_clarification, base_value, roe_ttm, yoy
from .periods import LATEST, Period, PeriodLike, to_date
from .result import MetricResult, MetricWarning, MultiResult, Status, WarnCode
from .rules import DEFAULT_RULES, SCREEN_OPS, RuleConfig, compare
from .store import FactStore


class UnknownMetricError(KeyError):
    """Chỉ số / phép biến đổi không có trong danh mục (bộ phân tích phải kiểm tra trước)."""


def _check_metric(metric: str, transform: str | None) -> None:
    if metric not in METRICS:
        raise UnknownMetricError(f"chỉ số không có trong danh mục: {metric!r}; có: {sorted(METRICS)}")
    if transform is not None and transform not in METRICS[metric].transforms:
        raise UnknownMetricError(
            f"phép biến đổi {transform!r} không áp dụng cho {metric!r}; "
            f"hỗ trợ: {sorted(METRICS[metric].transforms) or 'không có'}"
        )


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
        transform: ``None`` hoặc ``"yoy"``.
        as_of: ngày hỏi (``question_date``); chỉ dùng số liệu đã công bố tới ngày này.
            ``None`` = dùng toàn bộ snapshot.
        config: bộ ngưỡng quy tắc; mặc định :data:`rules.DEFAULT_RULES`.
    """
    _check_metric(metric, transform)
    config = config or DEFAULT_RULES
    mdef = METRICS[metric]
    metric_id = f"{metric}_{transform}" if transform else metric
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

    if metric == "roe_ttm":
        result = roe_ttm(store, ticker, resolved, as_of, config)
    elif transform == "yoy":
        result = yoy(store, mdef, ticker, resolved, as_of, config)
    else:
        result = base_value(store, mdef, ticker, resolved, as_of)

    if explicit is None:
        result.details["period_resolved_from"] = LATEST
    return result


# ---------------------------------------------------------------------------
# Nhiều mã
# ---------------------------------------------------------------------------
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
    _check_metric(metric, transform)
    config = config or DEFAULT_RULES
    metric_id = f"{metric}_{transform}" if transform else metric
    tickers = _dedupe(tickers)
    warnings: list[MetricWarning] = []
    is_latest = isinstance(period, str) and period == LATEST
    policy = config.latest_policy_multi if is_latest else "explicit"

    per_ticker_period: dict[str, PeriodLike] = {t: period for t in tickers}
    if is_latest and policy == "common":
        latest = {t: store.latest_period(t, as_of) for t in tickers if store.has_ticker(t)}
        available = [p for p in latest.values() if p is not None]
        if available:
            common = min(available)
            for t, p in latest.items():
                if p is not None:
                    per_ticker_period[t] = common
                    if p > common:
                        warnings.append(MetricWarning(
                            code=WarnCode.NEWER_PERIOD_AVAILABLE,
                            message=f"{t}: đã có BCTC {p.label()} nhưng bảng so sánh dùng kỳ chung "
                                    f"gần nhất {common.label()} của các mã.",
                            ticker=t, period=p.label(), severity="info",
                        ))

    rows = tuple(
        get_metric(store, metric, t, per_ticker_period[t], transform=transform, as_of=as_of, config=config)
        for t in tickers
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


# ---------------------------------------------------------------------------
# Lọc theo ngưỡng — quy tắc "0 dòng"
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

    Quy tắc 0 dòng (R8):

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
    warnings = [w for w in multi.warnings if w.code is not WarnCode.PARTIAL_COVERAGE]
    matched = tuple(r for r in multi.rows if r.status is Status.OK and compare(r.value, op, threshold))  # type: ignore[arg-type]
    excluded = tuple(r for r in multi.rows if r.status is not Status.OK)

    soft = [r for r in excluded if r.status in (Status.NOT_MEANINGFUL, Status.NOT_APPLICABLE)]
    hard = [r for r in excluded if r.status is Status.MISSING_DATA]
    if soft:
        warnings.append(MetricWarning(
            code=WarnCode.EXCLUDED_NOT_MEANINGFUL,
            message="Bị loại khỏi phép lọc vì chỉ số không xác định/không áp dụng: "
                    + ", ".join(f"{r.ticker} ({r.status.value})" for r in soft) + ".",
        ))
    if hard:
        warnings.append(MetricWarning(
            code=WarnCode.PARTIAL_COVERAGE,
            message="Không đánh giá được do thiếu dữ liệu: " + ", ".join(r.ticker for r in hard) + ".",
        ))

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
