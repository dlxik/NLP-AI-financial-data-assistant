"""Hệ thống B0 hoàn chỉnh: câu hỏi tiếng Việt → phân tích quy tắc → thư viện chỉ số → câu trả lời.

Đầu ra :meth:`B0Answer.to_dict` theo cùng khóa với ``MetricResult.to_dict()`` để TV3 (output
contract) và TV5 (bộ chấm) dùng chung cho mọi phương pháp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..semantic.catalog import METRICS
from ..semantic.fmt import describe, describe_multi, format_value, metric_name
from ..semantic.query import Query, QueryError, execute
from ..semantic.result import MetricResult, MultiResult, Status
from ..semantic.rules import DEFAULT_RULES, RuleConfig
from ..semantic.store import FactStore
from .parser import B0Parser

DISCLAIMER = "Thông tin chỉ nhằm mục đích tham khảo, không phải khuyến nghị đầu tư."

_CMP_VI = {">": "lớn hơn", ">=": "từ", "<": "nhỏ hơn", "<=": "không quá"}


@dataclass(frozen=True)
class B0Answer:
    question: str
    question_date: str | None
    status: Status
    query: Query | None
    result: MetricResult | MultiResult | None
    interpretation: str
    assumptions: tuple[str, ...] = ()
    candidates: tuple[str, ...] = ()
    reason: str | None = None
    text: str = ""
    method: str = field(default="B0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "question": self.question,
            "question_date": self.question_date,
            "status": self.status.value,
            "interpretation": self.interpretation,
            "assumptions": list(self.assumptions),
            "candidates": list(self.candidates),
            "reason": self.reason,
            "query": self.query.to_dict() if self.query else None,
            "result": self.result.to_dict() if self.result else None,
            "text": self.text,
        }


def interpret(query: Query) -> str:
    """Câu hiểu lại của hệ thống (yêu cầu M5): chỉ số, đối tượng, kỳ, phép toán."""
    mid = f"{query.metric}_{query.transform}" if query.transform else query.metric
    who = ", ".join(query.tickers) if query.tickers else {
        "all": "toàn bộ các mã (VN30)", "vn30": "toàn bộ các mã (VN30)",
        "bank": "nhóm ngân hàng", "non_financial": "nhóm doanh nghiệp phi tài chính",
    }[query.universe or "all"]
    when = "kỳ gần nhất đã công bố" if query.period == "latest" else query.period
    if query.as_of:
        when += f" (tính tới ngày hỏi {query.as_of})"
    text = f"Chỉ số: {metric_name(mid)} · Đối tượng: {who} · Kỳ: {when}"
    if query.op == "rank":
        order = "cao nhất" if query.order == "desc" else "thấp nhất"
        text += f" · Phép: xếp hạng {order}" + (f", top {query.top_n}" if query.top_n else "")
    elif query.op == "screen":
        unit = "ratio" if query.transform and ("yoy" in query.transform or "qoq" in query.transform) else None
        unit = unit or METRICS[query.metric].unit
        if query.transform and query.transform.endswith("_pp"):
            unit = "pp"
        text += f" · Phép: lọc {_CMP_VI[query.cmp or '>']} {format_value(query.threshold, unit)}"
    return text


class B0System:
    """Phương pháp B0 (không LLM). ``policy``: ``"default"`` (mặc định công khai + nêu giả định)
    hoặc ``"clarify"`` (hỏi lại 1 lượt khi câu mơ hồ) — phục vụ đánh giá RQ3."""

    def __init__(self, store: FactStore, *, policy: str = "default", config: RuleConfig | None = None) -> None:
        self.store = store
        self.parser = B0Parser(store, policy=policy)
        self.config = config or DEFAULT_RULES

    def answer(self, question: str, question_date: date | str | None = None) -> B0Answer:
        parsed = self.parser.parse(question, question_date)
        qdate = str(question_date) if question_date is not None else None
        assumptions = tuple(parsed.assumptions)

        if parsed.query is None:
            status = parsed.status or Status.NOT_APPLICABLE
            if status is Status.NEEDS_CLARIFICATION:
                text = parsed.reason or "Câu hỏi chưa rõ, vui lòng làm rõ."
            else:
                text = f"B0 không trả lời câu này: {parsed.reason}."
            return B0Answer(question, qdate, status, None, None, interpretation="(không dựng được truy vấn)",
                            assumptions=assumptions, candidates=parsed.candidates, reason=parsed.reason,
                            text=text)

        try:
            result = execute(self.store, parsed.query, self.config)
        except QueryError as exc:  # pragma: no cover - parser đã validate truy vấn
            return B0Answer(question, qdate, Status.NOT_APPLICABLE, parsed.query, None,
                            interpretation=interpret(parsed.query), assumptions=assumptions,
                            reason=str(exc), text=f"B0 không thực thi được truy vấn: {exc}.")

        body = describe(result) if isinstance(result, MetricResult) else describe_multi(result)
        lines = [body]
        if assumptions:
            lines.append("Giả định: " + "; ".join(assumptions) + ".")
        lines.append(DISCLAIMER)
        candidates = result.candidates if isinstance(result, MetricResult) else tuple(
            dict.fromkeys(c for r in (*result.rows, *result.excluded) for c in r.candidates))
        return B0Answer(
            question, qdate, result.status, parsed.query, result,
            interpretation=interpret(parsed.query), assumptions=assumptions,
            candidates=candidates, text="\n".join(lines),
        )
