"""Xử lý kỳ báo cáo (mục 4.4 — quy tắc thời gian).

Quy ước:
- Kỳ cơ sở là **quý tài chính** ``Period(year, quarter)``; năm tài chính trùng năm dương lịch
  (giả định cho nhóm VN30 — TV1 kiểm tra đồng bộ niên độ khi nạp dữ liệu).
- Số liệu dòng tiền/kết quả (``flow``) của một quý là số **quý đơn lẻ**; số liệu cân đối
  (``stock``) của một quý là **số dư cuối quý**.
- "Cùng kỳ năm trước" = dịch lùi 4 quý; cửa sổ TTM = 4 quý liên tiếp kết thúc tại kỳ hỏi.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Union

LATEST = "latest"
"""Giá trị đặc biệt cho tham số ``period``: "kỳ gần nhất" (xem :mod:`fin_assistant.semantic.api`)."""

_PATTERNS = (
    re.compile(r"^(?P<year>\d{4})\s*[-_/ ]?\s*Q(?P<q>[1-4])$", re.IGNORECASE),  # 2024Q3, 2024-Q3
    re.compile(r"^Q(?P<q>[1-4])\s*[-_/ ]\s*(?P<year>\d{4})$", re.IGNORECASE),  # Q3/2024, Q3-2024
)


@dataclass(frozen=True, order=True)
class Period:
    """Một quý tài chính. So sánh/sắp xếp theo (năm, quý)."""

    year: int
    quarter: int

    def __post_init__(self) -> None:
        if not isinstance(self.year, int) or not isinstance(self.quarter, int):
            raise TypeError("year và quarter phải là số nguyên")
        if not 1 <= self.quarter <= 4:
            raise ValueError(f"quý phải trong 1..4, nhận {self.quarter}")
        if not 1900 <= self.year <= 2200:
            raise ValueError(f"năm không hợp lệ: {self.year}")

    # --- số học trên kỳ -------------------------------------------------------
    @property
    def index(self) -> int:
        """Chỉ số tuyến tính của quý (dùng để cộng/trừ kỳ)."""
        return self.year * 4 + (self.quarter - 1)

    @classmethod
    def from_index(cls, idx: int) -> "Period":
        return cls(idx // 4, idx % 4 + 1)

    def shift(self, n: int) -> "Period":
        """Dịch ``n`` quý (âm = lùi về quá khứ)."""
        return Period.from_index(self.index + n)

    def same_quarter_last_year(self) -> "Period":
        """Cùng kỳ năm trước (YoY) — lùi 4 quý."""
        return self.shift(-4)

    def ttm_window(self) -> tuple["Period", ...]:
        """4 quý liên tiếp kết thúc tại kỳ này, theo thứ tự thời gian."""
        return tuple(self.shift(k) for k in range(-3, 1))

    def end_date(self) -> date:
        """Ngày kết thúc quý (năm tài chính = năm dương lịch)."""
        month = self.quarter * 3
        return date(self.year, month, calendar.monthrange(self.year, month)[1])

    # --- hiển thị -------------------------------------------------------------
    def label(self) -> str:
        """Nhãn tiếng Việt, luôn hiển thị cạnh con số: ``Q3/2024``."""
        return f"Q{self.quarter}/{self.year}"

    def __str__(self) -> str:
        return f"{self.year}Q{self.quarter}"

    # --- phân tích chuỗi ------------------------------------------------------
    @classmethod
    def parse(cls, value: Union["Period", str, tuple[int, int]]) -> "Period":
        """Nhận ``Period``, ``(năm, quý)``, ``"2024Q3"``, ``"2024-Q3"``, ``"Q3/2024"``."""
        if isinstance(value, Period):
            return value
        if isinstance(value, tuple) and len(value) == 2:
            return cls(int(value[0]), int(value[1]))
        if isinstance(value, str):
            text = value.strip()
            for pattern in _PATTERNS:
                match = pattern.match(text)
                if match:
                    return cls(int(match.group("year")), int(match.group("q")))
        raise ValueError(f"không đọc được kỳ báo cáo: {value!r}")


PeriodLike = Union[Period, str, tuple]


def to_date(value: Union[date, str, None]) -> date | None:
    """Chuẩn hóa ngày hỏi / ngày công bố về ``datetime.date`` (``None`` giữ nguyên)."""
    if value is None or isinstance(value, date) and not hasattr(value, "hour"):
        return value  # type: ignore[return-value]
    if hasattr(value, "date"):  # datetime / pandas.Timestamp
        return value.date()  # type: ignore[union-attr]
    if isinstance(value, str):
        return date.fromisoformat(value.strip()[:10])
    raise TypeError(f"không đọc được ngày: {value!r}")
