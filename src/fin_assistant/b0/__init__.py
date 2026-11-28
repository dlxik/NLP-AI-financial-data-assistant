"""Phương pháp B0 (không LLM, TV2): bộ phân tích quy tắc/template nhận nguyên câu tiếng Việt
(tách thực thể, kỳ, chỉ số, phép toán) và gọi thẳng thư viện chỉ số.

Ví dụ::

    from fin_assistant.b0 import B0System

    b0 = B0System(store)
    ans = b0.answer("Doanh thu quý 3/2024 của VNM tăng bao nhiêu so với cùng kỳ?", "2024-11-15")
    ans.status, ans.interpretation, ans.text

Đặc tả: ``docs/specs/b0-dac-ta.md``.
"""

from .normalize import normalize, parse_number
from .parser import B0Parser, ParseResult
from .system import B0Answer, B0System, interpret

__all__ = ["B0Answer", "B0Parser", "B0System", "ParseResult", "interpret", "normalize", "parse_number"]
