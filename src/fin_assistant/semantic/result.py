"""Kiểu kết quả chuẩn của thư viện chỉ số.

Mỗi lời gọi trả về một :class:`MetricResult` mang **trạng thái hành động** (khớp với nhãn
hành động kỳ vọng mà TV5 chấm), giá trị, công thức, danh sách ô số đầu vào (truy vết
``source_ref``) và cảnh báo **cụ thể** (nêu đúng mã / kỳ / đầu vào bị ảnh hưởng).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    """Trạng thái kết quả ↔ hành động kỳ vọng của hệ thống."""

    OK = "ok"
    """Trả số (có thể kèm cảnh báo)."""
    MISSING_DATA = "missing_data"
    """Báo thiếu dữ liệu — không trả số."""
    NOT_MEANINGFUL = "not_meaningful"
    """Chỉ số không xác định (vốn chủ âm, mẫu số ≤ 0 / gần 0) — cảnh báo, không trả số."""
    NEEDS_CLARIFICATION = "needs_clarification"
    """Câu hỏi mơ hồ về nghĩa chỉ tiêu — hỏi làm rõ, không tự chọn thay người dùng."""
    NOT_APPLICABLE = "not_applicable"
    """Chỉ số không áp dụng cho nhóm doanh nghiệp / mã ngoài phạm vi — từ chối có lý do."""
    EMPTY_VALID = "empty_valid"
    """Phép lọc chạy trên dữ liệu đầy đủ và không có dòng nào thỏa — 0 dòng hợp lệ."""

    @property
    def is_answer(self) -> bool:
        """True khi hệ thống được coi là đã "trả lời" (tính vào A trong A/N)."""
        return self in (Status.OK, Status.EMPTY_VALID)


class WarnCode(str, Enum):
    """Mã cảnh báo chuẩn hóa (dùng cho bộ chấm và giao diện demo)."""

    # thiếu dữ liệu / thời gian
    MISSING_INPUT = "missing_input"
    NOT_YET_PUBLISHED = "not_yet_published"
    OUT_OF_SCOPE_TICKER = "out_of_scope_ticker"
    # quy tắc số liệu khó (4.3)
    NEGATIVE_EQUITY = "negative_equity"
    NON_POSITIVE_BASE = "non_positive_base"
    DENOMINATOR_NEAR_ZERO = "denominator_near_zero"
    EXTREME_VALUE = "extreme_value"
    FALLBACK_ENDING_EQUITY = "fallback_ending_equity"
    # ngữ nghĩa chỉ tiêu
    BANK_NO_NET_REVENUE = "bank_no_net_revenue"
    METRIC_NOT_APPLICABLE = "metric_not_applicable"
    # truy vết / phiên bản
    RESTATED_VALUE = "restated_value"
    DERIVED_VALUE = "derived_value"
    # nhiều mã / lọc (4.4, 0 dòng)
    NEWER_PERIOD_AVAILABLE = "newer_period_available"
    MIXED_PERIODS = "mixed_periods"
    PARTIAL_COVERAGE = "partial_coverage"
    EXCLUDED_NOT_MEANINGFUL = "excluded_not_meaningful"


@dataclass(frozen=True)
class MetricWarning:
    """Một cảnh báo cụ thể. ``severity='info'`` chỉ để minh bạch, không đổi trạng thái."""

    code: WarnCode
    message: str
    ticker: str | None = None
    period: str | None = None
    item_code: str | None = None
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "ticker": self.ticker,
            "period": self.period,
            "item_code": self.item_code,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class InputRef:
    """Một ô số đầu vào đã dùng để tính — phục vụ truy vết về BCTC gốc."""

    item_code: str
    ticker: str
    period: str
    value: float
    unit: str
    source_ref: str
    report_version: int
    as_of_date: str
    is_restated: bool = False
    derived_from: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class MetricResult:
    """Kết quả của một chỉ số cho một mã tại một kỳ."""

    metric: str
    ticker: str
    period: str | None
    status: Status
    value: float | None = None
    unit: str | None = None
    formula: str = ""
    inputs: tuple[InputRef, ...] = ()
    warnings: tuple[MetricWarning, ...] = ()
    candidates: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def warning_codes(self) -> set[WarnCode]:
        return {w.code for w in self.warnings}

    def to_dict(self) -> dict[str, Any]:
        """Dạng JSON cho Output Contract (TV3) và bộ chấm (TV5)."""
        return {
            "metric": self.metric,
            "ticker": self.ticker,
            "period": self.period,
            "status": self.status.value,
            "value": self.value,
            "unit": self.unit,
            "formula": self.formula,
            "inputs": [i.to_dict() for i in self.inputs],
            "warnings": [w.to_dict() for w in self.warnings],
            "candidates": list(self.candidates),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class MultiResult:
    """Kết quả nhiều mã (bảng) hoặc kết quả lọc."""

    metric: str
    status: Status
    rows: tuple[MetricResult, ...]
    period_policy: str
    warnings: tuple[MetricWarning, ...] = ()
    excluded: tuple[MetricResult, ...] = ()

    @property
    def tickers(self) -> list[str]:
        return [r.ticker for r in self.rows]

    @property
    def warning_codes(self) -> set[WarnCode]:
        return {w.code for w in self.warnings}

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "status": self.status.value,
            "period_policy": self.period_policy,
            "rows": [r.to_dict() for r in self.rows],
            "excluded": [r.to_dict() for r in self.excluded],
            "warnings": [w.to_dict() for w in self.warnings],
        }
