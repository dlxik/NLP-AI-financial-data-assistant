"""Đặc tả và bộ kiểm tra Output Contract (JSON) cho các pipeline LLM (TV3).

Đồng bộ hoàn toàn ``Status``, ``WarnCode`` và cấu trúc ``InputRef`` / ``MetricResult`` /
``MultiResult`` để tương thích trực tiếp với Semantic Layer (TV2) và Bộ chấm v1 (TV5).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


CONTRACT_VERSION = "0.1"


class Status(str, Enum):
    """Trạng thái kết quả ↔ hành động kỳ vọng của hệ thống."""

    OK = "ok"
    MISSING_DATA = "missing_data"
    NOT_MEANINGFUL = "not_meaningful"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_APPLICABLE = "not_applicable"
    EMPTY_VALID = "empty_valid"

    @property
    def is_answer(self) -> bool:
        """True khi hệ thống được tính là đã trả lời (tử số A trong A/N)."""
        return self in (Status.OK, Status.EMPTY_VALID)


class AnswerType(str, Enum):
    """Kiểu đầu ra của câu trả lời."""

    SINGLE = "single"
    TABLE = "table"
    ACTION = "action"


class WarnCode(str, Enum):
    """16 mã cảnh báo chuẩn hóa dùng chung giữa TV2, TV3 và TV5."""

    MISSING_INPUT = "missing_input"
    NOT_YET_PUBLISHED = "not_yet_published"
    OUT_OF_SCOPE_TICKER = "out_of_scope_ticker"
    NEGATIVE_EQUITY = "negative_equity"
    NON_POSITIVE_BASE = "non_positive_base"
    DENOMINATOR_NEAR_ZERO = "denominator_near_zero"
    EXTREME_VALUE = "extreme_value"
    FALLBACK_ENDING_EQUITY = "fallback_ending_equity"
    BANK_NO_NET_REVENUE = "bank_no_net_revenue"
    METRIC_NOT_APPLICABLE = "metric_not_applicable"
    RESTATED_VALUE = "restated_value"
    DERIVED_VALUE = "derived_value"
    NEWER_PERIOD_AVAILABLE = "newer_period_available"
    MIXED_PERIODS = "mixed_periods"
    PARTIAL_COVERAGE = "partial_coverage"
    EXCLUDED_NOT_MEANINGFUL = "excluded_not_meaningful"


# Cảnh báo cấp bảng không gắn với duy nhất 1 ô số/mã đơn lẻ.
TABLE_LEVEL_WARN_CODES: frozenset[WarnCode] = frozenset(
    {
        WarnCode.MIXED_PERIODS,
        WarnCode.PARTIAL_COVERAGE,
        WarnCode.EXCLUDED_NOT_MEANINGFUL,
    }
)

_NO_VALUE_STATUSES: frozenset[Status] = frozenset(
    {
        Status.MISSING_DATA,
        Status.NOT_MEANINGFUL,
        Status.NEEDS_CLARIFICATION,
        Status.NOT_APPLICABLE,
        Status.EMPTY_VALID,
    }
)

_REASON_REQUIRED_STATUSES: frozenset[Status] = frozenset(
    {
        Status.MISSING_DATA,
        Status.NOT_MEANINGFUL,
        Status.NOT_APPLICABLE,
    }
)


def _is_finite_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val)


@dataclass(frozen=True)
class WarningItem:
    """Một cảnh báo cụ thể nêu rõ mã/kỳ/đầu vào bị ảnh hưởng."""

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WarningItem:
        return cls(
            code=WarnCode(data["code"]),
            message=str(data["message"]),
            ticker=data.get("ticker"),
            period=data.get("period"),
            item_code=data.get("item_code"),
            severity=str(data.get("severity", "warning")),
        )


@dataclass(frozen=True)
class InputRef:
    """Một ô số đầu vào dùng để tính — phục vụ truy vết về BCTC gốc."""

    item_code: str
    ticker: str
    period: str
    value: float
    unit: str
    source_ref: str
    report_version: int = 1
    as_of_date: str = ""
    is_restated: bool = False
    derived_from: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_code": self.item_code,
            "ticker": self.ticker,
            "period": self.period,
            "value": self.value,
            "unit": self.unit,
            "source_ref": self.source_ref,
            "report_version": self.report_version,
            "as_of_date": self.as_of_date,
            "is_restated": self.is_restated,
            "derived_from": self.derived_from,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InputRef:
        return cls(
            item_code=str(data["item_code"]),
            ticker=str(data["ticker"]),
            period=str(data["period"]),
            value=float(data["value"]),
            unit=str(data["unit"]),
            source_ref=str(data["source_ref"]),
            report_version=int(data.get("report_version", 1)),
            as_of_date=str(data.get("as_of_date", "")),
            is_restated=bool(data.get("is_restated", False)),
            derived_from=data.get("derived_from"),
        )


@dataclass(frozen=True)
class MetricRow:
    """Một dòng trong kết quả bảng nhiều mã hoặc danh sách bị loại (`excluded`)."""

    metric: str
    ticker: str
    period: str | None
    status: Status
    value: float | None = None
    unit: str | None = None
    formula: str = ""
    inputs: tuple[InputRef, ...] = ()
    warnings: tuple[WarningItem, ...] = ()
    candidates: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricRow:
        return cls(
            metric=str(data["metric"]),
            ticker=str(data["ticker"]),
            period=data.get("period"),
            status=Status(data["status"]),
            value=data.get("value"),
            unit=data.get("unit"),
            formula=str(data.get("formula", "")),
            inputs=tuple(InputRef.from_dict(i) for i in data.get("inputs", [])),
            warnings=tuple(WarningItem.from_dict(w) for w in data.get("warnings", [])),
            candidates=tuple(str(c) for c in data.get("candidates", [])),
            details=dict(data.get("details", {})),
        )


@dataclass(frozen=True)
class InterpretedQuery:
    """Diễn giải cấu trúc câu hỏi để hiển thị minh bạch và kiểm lỗi ngữ nghĩa."""

    ticker: str | None = None
    tickers: tuple[str, ...] = ()
    metric: str | None = None
    period: str | None = None
    transform: str | None = None
    scope: str = "consolidated"
    assumptions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "tickers": list(self.tickers),
            "metric": self.metric,
            "period": self.period,
            "transform": self.transform,
            "scope": self.scope,
            "assumptions": list(self.assumptions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterpretedQuery:
        return cls(
            ticker=data.get("ticker"),
            tickers=tuple(str(t) for t in data.get("tickers", [])),
            metric=data.get("metric"),
            period=data.get("period"),
            transform=data.get("transform"),
            scope=str(data.get("scope", "consolidated")),
            assumptions=tuple(str(a) for a in data.get("assumptions", [])),
        )


@dataclass(frozen=True)
class ExecutionMeta:
    """Thông tin thực thi của một lượt chạy LLM/sandbox."""

    model: str
    model_version: str
    seed: int | None
    temperature: float
    num_llm_calls: int = 1
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    sandbox_used: bool = False
    sandbox_ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "model_version": self.model_version,
            "seed": self.seed,
            "temperature": self.temperature,
            "num_llm_calls": self.num_llm_calls,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "sandbox_used": self.sandbox_used,
            "sandbox_ok": self.sandbox_ok,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionMeta:
        return cls(
            model=str(data["model"]),
            model_version=str(data["model_version"]),
            seed=data.get("seed"),
            temperature=float(data["temperature"]),
            num_llm_calls=int(data.get("num_llm_calls", 1)),
            latency_ms=float(data.get("latency_ms", 0.0)),
            prompt_tokens=int(data.get("prompt_tokens", 0)),
            completion_tokens=int(data.get("completion_tokens", 0)),
            total_tokens=int(data.get("total_tokens", 0)),
            sandbox_used=bool(data.get("sandbox_used", False)),
            sandbox_ok=data.get("sandbox_ok"),
        )


@dataclass(frozen=True)
class PipelineOutput:
    """Đầu ra chuẩn hóa chung giữa các pipeline (B0, A, B, C, B1, D) và Bộ chấm."""

    question_id: str
    pipeline: str
    status: Status
    answer_type: AnswerType
    metric: str
    contract_version: str = CONTRACT_VERSION
    question_date: str | None = None
    ticker: str | None = None
    period: str | None = None
    value: float | None = None
    unit: str | None = None
    period_policy: str | None = None
    rows: tuple[MetricRow, ...] = ()
    excluded: tuple[MetricRow, ...] = ()
    formula: str = ""
    interpreted_query: InterpretedQuery | None = None
    inputs: tuple[InputRef, ...] = ()
    warnings: tuple[WarningItem, ...] = ()
    candidates: tuple[str, ...] = ()
    message: str = ""
    execution_meta: ExecutionMeta | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "question_id": self.question_id,
            "question_date": self.question_date,
            "pipeline": self.pipeline,
            "status": self.status.value,
            "answer_type": self.answer_type.value,
            "metric": self.metric,
            "ticker": self.ticker,
            "period": self.period,
            "value": self.value,
            "unit": self.unit,
            "period_policy": self.period_policy,
            "rows": [r.to_dict() for r in self.rows],
            "excluded": [r.to_dict() for r in self.excluded],
            "formula": self.formula,
            "interpreted_query": self.interpreted_query.to_dict() if self.interpreted_query else None,
            "inputs": [i.to_dict() for i in self.inputs],
            "warnings": [w.to_dict() for w in self.warnings],
            "candidates": list(self.candidates),
            "message": self.message,
            "execution_meta": self.execution_meta.to_dict() if self.execution_meta else None,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineOutput:
        iq_raw = data.get("interpreted_query")
        meta_raw = data.get("execution_meta")
        return cls(
            contract_version=str(data.get("contract_version", CONTRACT_VERSION)),
            question_id=str(data["question_id"]),
            question_date=data.get("question_date"),
            pipeline=str(data["pipeline"]),
            status=Status(data["status"]),
            answer_type=AnswerType(data["answer_type"]),
            metric=str(data["metric"]),
            ticker=data.get("ticker"),
            period=data.get("period"),
            value=data.get("value"),
            unit=data.get("unit"),
            period_policy=data.get("period_policy"),
            rows=tuple(MetricRow.from_dict(r) for r in data.get("rows", [])),
            excluded=tuple(MetricRow.from_dict(r) for r in data.get("excluded", [])),
            formula=str(data.get("formula", "")),
            interpreted_query=InterpretedQuery.from_dict(iq_raw) if isinstance(iq_raw, dict) else None,
            inputs=tuple(InputRef.from_dict(i) for i in data.get("inputs", [])),
            warnings=tuple(WarningItem.from_dict(w) for w in data.get("warnings", [])),
            candidates=tuple(str(c) for c in data.get("candidates", [])),
            message=str(data.get("message", "")),
            execution_meta=ExecutionMeta.from_dict(meta_raw) if isinstance(meta_raw, dict) else None,
            details=dict(data.get("details", {})),
        )

    @classmethod
    def from_metric_dict(
        cls,
        metric_dict: dict[str, Any],
        *,
        question_id: str,
        pipeline: str,
        question_date: str | None = None,
        interpreted_query: InterpretedQuery | None = None,
        execution_meta: ExecutionMeta | None = None,
        message: str = "",
    ) -> PipelineOutput:
        """Chuyển trực tiếp ``MetricResult.to_dict()`` (TV2) sang ``PipelineOutput``."""
        status = Status(metric_dict["status"])
        answer_type = AnswerType.SINGLE if status is Status.OK else AnswerType.ACTION
        return cls(
            question_id=question_id,
            question_date=question_date,
            pipeline=pipeline,
            status=status,
            answer_type=answer_type,
            metric=str(metric_dict["metric"]),
            ticker=metric_dict.get("ticker"),
            period=metric_dict.get("period"),
            value=metric_dict.get("value"),
            unit=metric_dict.get("unit"),
            formula=str(metric_dict.get("formula", "")),
            interpreted_query=interpreted_query,
            inputs=tuple(InputRef.from_dict(i) for i in metric_dict.get("inputs", [])),
            warnings=tuple(WarningItem.from_dict(w) for w in metric_dict.get("warnings", [])),
            candidates=tuple(str(c) for c in metric_dict.get("candidates", [])),
            message=message,
            execution_meta=execution_meta,
            details=dict(metric_dict.get("details", {})),
        )

    @classmethod
    def from_multi_dict(
        cls,
        multi_dict: dict[str, Any],
        *,
        question_id: str,
        pipeline: str,
        question_date: str | None = None,
        interpreted_query: InterpretedQuery | None = None,
        execution_meta: ExecutionMeta | None = None,
        message: str = "",
    ) -> PipelineOutput:
        """Chuyển trực tiếp ``MultiResult.to_dict()`` (TV2) sang ``PipelineOutput``."""
        status = Status(multi_dict["status"])
        return cls(
            question_id=question_id,
            question_date=question_date,
            pipeline=pipeline,
            status=status,
            answer_type=AnswerType.TABLE,
            metric=str(multi_dict["metric"]),
            period_policy=multi_dict.get("period_policy"),
            rows=tuple(MetricRow.from_dict(r) for r in multi_dict.get("rows", [])),
            excluded=tuple(MetricRow.from_dict(r) for r in multi_dict.get("excluded", [])),
            interpreted_query=interpreted_query,
            warnings=tuple(WarningItem.from_dict(w) for w in multi_dict.get("warnings", [])),
            message=message,
            execution_meta=execution_meta,
        )


def _validate_warnings(warnings_raw: Any, prefix: str, errors: list[str]) -> list[WarningItem]:
    parsed: list[WarningItem] = []
    if not isinstance(warnings_raw, list):
        errors.append(f"{prefix}.warnings must be a list")
        return parsed
    for idx, item in enumerate(warnings_raw):
        loc = f"{prefix}.warnings[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{loc} must be an object")
            continue
        try:
            warn = WarningItem.from_dict(item)
        except (KeyError, ValueError) as exc:
            errors.append(f"{loc} invalid warning: {exc}")
            continue
        if not warn.message.strip():
            errors.append(f"{loc}.message must not be empty")
        # Bộ chấm của TV5 loại bỏ cảnh báo chung chung không nêu mã/kỳ/đầu vào.
        if (
            warn.severity == "warning"
            and warn.code not in TABLE_LEVEL_WARN_CODES
            and not any([warn.ticker, warn.period, warn.item_code])
        ):
            errors.append(
                f"{loc} ({warn.code.value}) is too generic: must specify ticker, period, or item_code"
            )
        parsed.append(warn)
    return parsed


def _validate_inputs(inputs_raw: Any, prefix: str, errors: list[str]) -> None:
    if not isinstance(inputs_raw, list):
        errors.append(f"{prefix}.inputs must be a list")
        return
    for idx, item in enumerate(inputs_raw):
        loc = f"{prefix}.inputs[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{loc} must be an object")
            continue
        for req in ("item_code", "ticker", "period", "value", "unit", "source_ref"):
            if req not in item or item[req] is None or item[req] == "":
                errors.append(f"{loc}.{req} is required for source traceability")
        if "value" in item and not _is_finite_number(item["value"]):
            errors.append(f"{loc}.value must be a finite number")


def _validate_rows(rows_raw: Any, prefix: str, errors: list[str]) -> list[MetricRow]:
    parsed: list[MetricRow] = []
    if not isinstance(rows_raw, list):
        errors.append(f"{prefix}.rows must be a list")
        return parsed
    for idx, item in enumerate(rows_raw):
        loc = f"{prefix}[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{loc} must be an object")
            continue
        try:
            row = MetricRow.from_dict(item)
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"{loc} invalid row: {exc}")
            continue
        if not row.ticker.strip():
            errors.append(f"{loc}.ticker must not be empty")
        if row.status is Status.OK:
            if not _is_finite_number(row.value):
                errors.append(f"{loc}.value must be a finite number when row status is 'ok'")
            if not row.period:
                errors.append(f"{loc}.period is required when row status is 'ok'")
        elif row.value is not None:
            errors.append(f"{loc}.value must be None when row status is '{row.status.value}'")
        _validate_warnings(item.get("warnings", []), loc, errors)
        _validate_inputs(item.get("inputs", []), loc, errors)
        parsed.append(row)
    return parsed


def validate_output_contract(payload: dict[str, Any] | PipelineOutput) -> list[str]:
    """Kiểm tra tính hợp lệ của một đầu ra theo Output Contract v0.1.

    Trả về danh sách thông báo lỗi (rỗng nếu hợp lệ hoàn toàn).
    """
    data = payload.to_dict() if isinstance(payload, PipelineOutput) else payload
    if not isinstance(data, dict):
        return ["payload must be a JSON object or PipelineOutput"]

    errors: list[str] = []
    for req in ("contract_version", "question_id", "pipeline", "status", "answer_type", "metric"):
        val = data.get(req)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{req} must be a non-empty string")

    status: Status | None = None
    answer_type: AnswerType | None = None
    if "status" in data:
        try:
            status = Status(data["status"])
        except ValueError:
            errors.append(f"invalid status: {data.get('status')!r}")
    if "answer_type" in data:
        try:
            answer_type = AnswerType(data["answer_type"])
        except ValueError:
            errors.append(f"invalid answer_type: {data.get('answer_type')!r}")

    warnings = _validate_warnings(data.get("warnings", []), "root", errors)
    _validate_inputs(data.get("inputs", []), "root", errors)
    rows = _validate_rows(data.get("rows", []), "root.rows", errors)
    _validate_rows(data.get("excluded", []), "root.excluded", errors)

    value = data.get("value")
    candidates = data.get("candidates", [])
    message = str(data.get("message", "") or "")

    if status is None or answer_type is None:
        return errors

    if status in _NO_VALUE_STATUSES and value is not None:
        errors.append(f"value must be None when status is '{status.value}'")

    if status is Status.OK:
        if answer_type is AnswerType.SINGLE:
            if not _is_finite_number(value):
                errors.append("value must be a finite number for single 'ok' answer")
            if not isinstance(data.get("ticker"), str) or not data["ticker"].strip():
                errors.append("ticker is required for single 'ok' answer")
            if not isinstance(data.get("period"), str) or not data["period"].strip():
                errors.append("period is required for single 'ok' answer")
        elif answer_type is AnswerType.TABLE:
            if not rows:
                errors.append("rows must be non-empty for table 'ok' answer")
            elif not any(r.status is Status.OK for r in rows):
                errors.append("table 'ok' answer must contain at least one 'ok' row")
        else:
            errors.append("answer_type 'action' cannot have status 'ok'")

    elif status is Status.EMPTY_VALID:
        if answer_type is not AnswerType.TABLE:
            errors.append("status 'empty_valid' requires answer_type 'table'")
        if rows:
            errors.append("status 'empty_valid' requires empty rows")

    elif status is Status.NEEDS_CLARIFICATION:
        if not isinstance(candidates, list) or not [c for c in candidates if isinstance(c, str) and c.strip()]:
            errors.append("status 'needs_clarification' requires non-empty candidates list")

    elif status in _REASON_REQUIRED_STATUSES:
        has_row_reason = any(r.warnings for r in rows)
        if not warnings and not has_row_reason and not message.strip():
            errors.append(
                f"status '{status.value}' requires specific warnings or explanatory message"
            )

    return errors
