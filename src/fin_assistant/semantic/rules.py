"""Quy tắc số liệu khó (mục 4.3) — các hàm thuần, không phụ thuộc dữ liệu.

Mọi ngưỡng gom vào :class:`RuleConfig` để nhóm chốt ở cổng Giai đoạn 1 và đóng băng; không
hàm nào được tự ý dùng ngưỡng ngoài cấu hình. Giá trị mặc định = đề xuất trong
``docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .result import Status, WarnCode

EquityAvgMethod = Literal["two_point", "five_point"]
LatestPolicy = Literal["common", "per_ticker"]


@dataclass(frozen=True)
class RuleConfig:
    """Bộ ngưỡng/quy ước có thể cấu hình (giá trị mặc định = đề xuất chốt)."""

    near_zero_abs_vnd: float = 1e9
    """R2 — mẫu số tiền tệ dương nhưng nhỏ hơn ngưỡng này (1 tỷ đồng) coi như "gần 0"."""
    extreme_ratio: float = 10.0
    """R3 — |kết quả| > ngưỡng (10 = 1.000%) vẫn trả số nhưng gắn cảnh báo EXTREME_VALUE."""
    equity_avg_method: EquityAvgMethod = "two_point"
    """R5 — VCSH bình quân: 2 điểm (đầu kỳ t−4, cuối kỳ t) hoặc 5 điểm (t−4..t)."""
    allow_ending_equity_fallback: bool = False
    """R6 — thiếu VCSH đầu kỳ: mặc định báo thiếu; bật cờ này mới dùng VCSH cuối kỳ (kèm cảnh báo)."""
    latest_policy_multi: LatestPolicy = "common"
    """T5 — "kỳ gần nhất" khi hỏi nhiều mã: kỳ chung gần nhất (mặc định) hoặc từng mã."""

    def __post_init__(self) -> None:
        if self.near_zero_abs_vnd < 0:
            raise ValueError("near_zero_abs_vnd phải ≥ 0")
        if self.extreme_ratio <= 0:
            raise ValueError("extreme_ratio phải > 0")
        if self.equity_avg_method not in ("two_point", "five_point"):
            raise ValueError(f"equity_avg_method không hợp lệ: {self.equity_avg_method}")
        if self.latest_policy_multi not in ("common", "per_ticker"):
            raise ValueError(f"latest_policy_multi không hợp lệ: {self.latest_policy_multi}")


DEFAULT_RULES = RuleConfig()


@dataclass(frozen=True)
class RuleOutcome:
    """Kết quả áp quy tắc cho một phép chia."""

    status: Status
    value: float | None
    code: WarnCode | None = None


def check_denominator(
    denominator: float,
    config: RuleConfig,
    *,
    non_positive_code: WarnCode = WarnCode.NON_POSITIVE_BASE,
) -> WarnCode | None:
    """R1–R2: trả mã cảnh báo nếu mẫu số không dùng được, ``None`` nếu hợp lệ.

    - Mẫu số ≤ 0 → không xác định (``non_positive_code``; với ROE là NEGATIVE_EQUITY).
    - 0 < mẫu số < ``near_zero_abs_vnd`` → không xác định (DENOMINATOR_NEAR_ZERO).
    """
    if denominator <= 0:
        return non_positive_code
    if denominator < config.near_zero_abs_vnd:
        return WarnCode.DENOMINATOR_NEAR_ZERO
    return None


def growth_rate(current: float, base: float, config: RuleConfig) -> RuleOutcome:
    """Tăng trưởng tương đối ``(current − base) / base`` (dạng tỷ lệ: 0.15 = 15%).

    Chỉ xác định khi kỳ gốc dương và không gần 0 (R1–R2); giá trị cực đoan vẫn trả kèm
    cảnh báo (R3).
    """
    code = check_denominator(base, config)
    if code is not None:
        return RuleOutcome(Status.NOT_MEANINGFUL, None, code)
    value = (current - base) / base
    if abs(value) > config.extreme_ratio:
        return RuleOutcome(Status.OK, value, WarnCode.EXTREME_VALUE)
    return RuleOutcome(Status.OK, value)


def safe_ratio(
    numerator: float,
    denominator: float,
    config: RuleConfig,
    *,
    non_positive_code: WarnCode = WarnCode.NON_POSITIVE_BASE,
) -> RuleOutcome:
    """Tỷ số ``numerator / denominator`` theo cùng quy tắc mẫu số (R1–R3)."""
    code = check_denominator(denominator, config, non_positive_code=non_positive_code)
    if code is not None:
        return RuleOutcome(Status.NOT_MEANINGFUL, None, code)
    value = numerator / denominator
    if abs(value) > config.extreme_ratio:
        return RuleOutcome(Status.OK, value, WarnCode.EXTREME_VALUE)
    return RuleOutcome(Status.OK, value)


_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}
SCREEN_OPS = frozenset(_OPS)


def compare(value: float, op: str, threshold: float) -> bool:
    """Phép so sánh giới hạn dùng cho lọc (không nhận biểu thức tùy ý)."""
    try:
        return _OPS[op](value, threshold)
    except KeyError:
        raise ValueError(f"phép so sánh không hỗ trợ: {op!r}; chỉ nhận {sorted(_OPS)}") from None
