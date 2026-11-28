"""Kiểu dữ liệu Gold và kết quả chấm của TV5.

Module không phụ thuộc pipeline/semantic layer để người giữ Test có thể chấm độc lập.
Đầu vào dự đoán chỉ cần là mapping tuân theo Output Contract v0.1 của TV3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


ANSWERED_STATUSES = frozenset({"ok", "empty_valid"})
VALID_STATUSES = frozenset(
    {
        "ok",
        "empty_valid",
        "missing_data",
        "not_meaningful",
        "needs_clarification",
        "not_applicable",
    }
)
VALID_ANSWER_TYPES = frozenset({"single", "table", "action"})


def _as_codes(raw: Any) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError("warning codes must be a list")
    return frozenset(str(value) for value in raw)


@dataclass(frozen=True)
class GoldRow:
    """Đáp án chuẩn cho một dòng của bảng nhiều mã."""

    ticker: str
    period: str | None
    status: str = "ok"
    value: float | None = None
    unit: str | None = None
    metric: str | None = None
    required_warning_codes: frozenset[str] = frozenset()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GoldRow":
        status = str(data.get("status", "ok"))
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid Gold row status: {status}")
        value = data.get("value")
        return cls(
            ticker=str(data["ticker"]),
            period=data.get("period"),
            status=status,
            value=float(value) if value is not None else None,
            unit=data.get("unit"),
            metric=data.get("metric"),
            required_warning_codes=_as_codes(data.get("required_warning_codes")),
        )


@dataclass(frozen=True)
class GoldCase:
    """Một câu Gold, gồm cả kết quả số và hành động kỳ vọng."""

    question_id: str
    status: str
    answer_type: str
    metric: str
    ticker: str | None = None
    period: str | None = None
    value: float | None = None
    unit: str | None = None
    rows: tuple[GoldRow, ...] = ()
    required_warning_codes: frozenset[str] = frozenset()
    required_candidates: frozenset[str] = frozenset()
    abs_tol: float = 1e-6
    rel_tol: float = 1e-6
    row_key_fields: tuple[str, ...] = ("ticker", "period")
    family: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid Gold status: {self.status}")
        if self.answer_type not in VALID_ANSWER_TYPES:
            raise ValueError(f"invalid Gold answer_type: {self.answer_type}")
        if self.abs_tol < 0 or self.rel_tol < 0:
            raise ValueError("tolerances must be non-negative")
        if self.answer_type == "table" and self.status == "ok" and not self.rows:
            raise ValueError("table Gold with status 'ok' must have rows")
        if self.status == "empty_valid" and self.rows:
            raise ValueError("empty_valid Gold must not have rows")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GoldCase":
        value = data.get("value")
        return cls(
            question_id=str(data["question_id"]),
            status=str(data["status"]),
            answer_type=str(data["answer_type"]),
            metric=str(data["metric"]),
            ticker=data.get("ticker"),
            period=data.get("period"),
            value=float(value) if value is not None else None,
            unit=data.get("unit"),
            rows=tuple(GoldRow.from_dict(row) for row in data.get("rows", [])),
            required_warning_codes=_as_codes(data.get("required_warning_codes")),
            required_candidates=_as_codes(data.get("required_candidates")),
            abs_tol=float(data.get("abs_tol", 1e-6)),
            rel_tol=float(data.get("rel_tol", 1e-6)),
            row_key_fields=tuple(data.get("row_key_fields", ("ticker", "period"))),
            family=data.get("family"),
        )


@dataclass(frozen=True)
class CaseScore:
    """Kết quả chấm một câu."""

    question_id: str
    expected_status: str
    predicted_status: str | None
    answered: bool
    wrong_answer: bool
    behavior_correct: bool
    silent_wrong: bool
    unnecessary_clarification: bool
    specific_warning_present: bool
    row_total: int = 0
    row_correct: int = 0
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "expected_status": self.expected_status,
            "predicted_status": self.predicted_status,
            "answered": self.answered,
            "wrong_answer": self.wrong_answer,
            "behavior_correct": self.behavior_correct,
            "silent_wrong": self.silent_wrong,
            "unnecessary_clarification": self.unnecessary_clarification,
            "specific_warning_present": self.specific_warning_present,
            "row_total": self.row_total,
            "row_correct": self.row_correct,
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class ScoreSummary:
    """Bảng tổng hợp, giữ nguyên bốn đại lượng bắt buộc trong kế hoạch."""

    cases: tuple[CaseScore, ...]
    extra_prediction_ids: tuple[str, ...] = ()

    @property
    def n(self) -> int:
        return len(self.cases)

    @property
    def a(self) -> int:
        return sum(case.answered for case in self.cases)

    @property
    def w(self) -> int:
        return sum(case.wrong_answer for case in self.cases)

    @property
    def correct_answer_count(self) -> int:
        return self.a - self.w

    @property
    def behavior_correct_count(self) -> int:
        return sum(case.behavior_correct for case in self.cases)

    @property
    def silent_wrong_count(self) -> int:
        return sum(case.silent_wrong for case in self.cases)

    @property
    def unnecessary_clarification_count(self) -> int:
        return sum(case.unnecessary_clarification for case in self.cases)

    @property
    def row_total(self) -> int:
        return sum(case.row_total for case in self.cases)

    @property
    def row_correct(self) -> int:
        return sum(case.row_correct for case in self.cases)

    @staticmethod
    def _ratio(num: int, den: int) -> float | None:
        return num / den if den else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "N": self.n,
            "A": self.a,
            "W": self.w,
            "correct_answers": self.correct_answer_count,
            "answer_rate_A_over_N": self._ratio(self.a, self.n),
            "wrong_among_answered_W_over_A": self._ratio(self.w, self.a),
            "overall_correct_A_minus_W_over_N": self._ratio(self.correct_answer_count, self.n),
            "silent_wrong_count": self.silent_wrong_count,
            "silent_wrong_rate_over_N": self._ratio(self.silent_wrong_count, self.n),
            "behavior_correct_count": self.behavior_correct_count,
            "behavior_accuracy": self._ratio(self.behavior_correct_count, self.n),
            "unnecessary_clarification_count": self.unnecessary_clarification_count,
            "row_total": self.row_total,
            "row_correct": self.row_correct,
            "row_accuracy": self._ratio(self.row_correct, self.row_total),
            "extra_prediction_ids": list(self.extra_prediction_ids),
            "cases": [case.to_dict() for case in self.cases],
        }
