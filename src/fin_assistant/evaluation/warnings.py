"""Lọc cảnh báo cụ thể; cảnh báo chung chung không được công nhận."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


TABLE_LEVEL_CODES = frozenset(
    {"mixed_periods", "partial_coverage", "excluded_not_meaningful"}
)


def warning_is_specific(warning: Mapping[str, Any]) -> bool:
    """Cảnh báo phải có code/message và định vị mã, kỳ hoặc đầu vào.

    Ba cảnh báo tổng hợp cấp bảng được miễn trường định vị theo Output Contract v0.1.
    """

    code = str(warning.get("code", "")).strip()
    message = str(warning.get("message", "")).strip()
    if not code or not message:
        return False
    if str(warning.get("severity", "warning")) != "warning":
        return False
    if code in TABLE_LEVEL_CODES:
        return True
    return any(
        str(warning.get(field, "") or "").strip()
        for field in ("ticker", "period", "item_code")
    )


def iter_warnings(prediction: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Duyệt cảnh báo ở cấp câu, rows và excluded."""

    for warning in prediction.get("warnings", []) or []:
        if isinstance(warning, Mapping):
            yield warning
    for collection in ("rows", "excluded"):
        for row in prediction.get(collection, []) or []:
            if not isinstance(row, Mapping):
                continue
            for warning in row.get("warnings", []) or []:
                if isinstance(warning, Mapping):
                    yield warning


def specific_warnings(prediction: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return tuple(warning for warning in iter_warnings(prediction) if warning_is_specific(warning))


def has_required_warning(
    prediction: Mapping[str, Any],
    required_codes: frozenset[str],
    *,
    ticker: str | None = None,
    period: str | None = None,
) -> bool:
    """Kiểm tra code cảnh báo và từ chối cảnh báo định vị sai mã/kỳ."""

    if not required_codes:
        return False
    for warning in specific_warnings(prediction):
        if str(warning.get("code")) not in required_codes:
            continue
        warning_ticker = warning.get("ticker")
        warning_period = warning.get("period")
        if ticker and warning_ticker and str(warning_ticker) != ticker:
            continue
        if period and warning_period and str(warning_period) != period:
            continue
        return True
    return False
