"""Bộ chấm v1: câu đơn, bảng nhiều mã và hành động."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .models import ANSWERED_STATUSES, CaseScore, GoldCase, GoldRow, ScoreSummary
from .warnings import has_required_warning, specific_warnings


def _number_equal(actual: Any, expected: float | None, *, abs_tol: float, rel_tol: float) -> bool:
    if expected is None or isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return actual is None and expected is None
    if not math.isfinite(float(actual)):
        return False
    return math.isclose(float(actual), expected, abs_tol=abs_tol, rel_tol=rel_tol)


def _field_equal(actual: Any, expected: Any) -> bool:
    return expected is None or actual == expected


def _row_key(row: Mapping[str, Any] | GoldRow, fields: tuple[str, ...]) -> tuple[Any, ...]:
    if isinstance(row, GoldRow):
        return tuple(getattr(row, field) for field in fields)
    return tuple(row.get(field) for field in fields)


def _score_row(
    gold: GoldRow,
    prediction: Mapping[str, Any],
    case: GoldCase,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    status = prediction.get("status")
    if status != gold.status:
        errors.append(f"row {gold.ticker}/{gold.period}: status {status!r} != {gold.status!r}")
        return False, errors
    if gold.metric is not None and prediction.get("metric") != gold.metric:
        errors.append(f"row {gold.ticker}/{gold.period}: metric mismatch")
    if gold.unit is not None and prediction.get("unit") != gold.unit:
        errors.append(f"row {gold.ticker}/{gold.period}: unit mismatch")
    if gold.status == "ok" and not _number_equal(
        prediction.get("value"), gold.value, abs_tol=case.abs_tol, rel_tol=case.rel_tol
    ):
        errors.append(f"row {gold.ticker}/{gold.period}: value mismatch")
    if gold.required_warning_codes and not has_required_warning(
        prediction,
        gold.required_warning_codes,
        ticker=gold.ticker,
        period=gold.period,
    ):
        errors.append(f"row {gold.ticker}/{gold.period}: missing specific required warning")
    return not errors, errors


def _score_table(gold: GoldCase, prediction: Mapping[str, Any]) -> tuple[bool, int, int, list[str]]:
    errors: list[str] = []
    raw_rows = prediction.get("rows", [])
    if not isinstance(raw_rows, list) or any(not isinstance(row, Mapping) for row in raw_rows):
        return False, len(gold.rows), 0, ["rows must be a list of objects"]

    gold_keys = [_row_key(row, gold.row_key_fields) for row in gold.rows]
    pred_keys = [_row_key(row, gold.row_key_fields) for row in raw_rows]
    duplicate_keys = [key for key, count in Counter(pred_keys).items() if count > 1]
    if duplicate_keys:
        errors.append(f"duplicate row keys: {duplicate_keys!r}")

    pred_by_key = {key: row for key, row in zip(pred_keys, raw_rows)}
    row_correct = 0
    for gold_row, key in zip(gold.rows, gold_keys):
        predicted_row = pred_by_key.get(key)
        if predicted_row is None:
            errors.append(f"missing row: {key!r}")
            continue
        correct, row_errors = _score_row(gold_row, predicted_row, gold)
        row_correct += int(correct)
        errors.extend(row_errors)

    extra = set(pred_keys) - set(gold_keys)
    if extra:
        errors.append(f"extra rows: {sorted(extra, key=repr)!r}")
    exact = not errors and len(raw_rows) == len(gold.rows)
    return exact, len(gold.rows), row_correct, errors


def score_case(gold: GoldCase, prediction: Mapping[str, Any] | None) -> CaseScore:
    """Chấm một câu; prediction hỏng/thiếu vẫn được tính vào N."""

    if prediction is None:
        return CaseScore(
            question_id=gold.question_id,
            expected_status=gold.status,
            predicted_status=None,
            answered=False,
            wrong_answer=False,
            behavior_correct=False,
            silent_wrong=False,
            unnecessary_clarification=False,
            specific_warning_present=False,
            row_total=len(gold.rows),
            errors=("missing prediction",),
        )

    errors: list[str] = []
    predicted_status_raw = prediction.get("status")
    predicted_status = str(predicted_status_raw) if predicted_status_raw is not None else None
    answered = predicted_status in ANSWERED_STATUSES
    unnecessary_clarification = (
        predicted_status == "needs_clarification" and gold.status != "needs_clarification"
    )
    warnings = specific_warnings(prediction)
    specific_warning_present = bool(warnings)
    required_warning_present = has_required_warning(
        prediction,
        gold.required_warning_codes,
        ticker=gold.ticker,
        period=gold.period,
    )

    if prediction.get("question_id") not in (None, gold.question_id):
        errors.append("question_id mismatch")
    if predicted_status != gold.status:
        errors.append(f"status {predicted_status!r} != {gold.status!r}")
    if prediction.get("answer_type") != gold.answer_type:
        errors.append("answer_type mismatch")
    if prediction.get("metric") != gold.metric:
        errors.append("metric mismatch")

    row_total = 0
    row_correct = 0
    if predicted_status == gold.status:
        if gold.status == "ok" and gold.answer_type == "single":
            if not _field_equal(prediction.get("ticker"), gold.ticker):
                errors.append("ticker mismatch")
            if not _field_equal(prediction.get("period"), gold.period):
                errors.append("period mismatch")
            if not _field_equal(prediction.get("unit"), gold.unit):
                errors.append("unit mismatch")
            if not _number_equal(
                prediction.get("value"), gold.value, abs_tol=gold.abs_tol, rel_tol=gold.rel_tol
            ):
                errors.append("value outside tolerance")
        elif gold.status == "ok" and gold.answer_type == "table":
            _, row_total, row_correct, table_errors = _score_table(gold, prediction)
            errors.extend(table_errors)
        elif gold.status == "empty_valid":
            if prediction.get("rows", []) != []:
                errors.append("empty_valid must have zero rows")

    if gold.required_warning_codes and not required_warning_present:
        errors.append("missing specific required warning")

    if gold.required_candidates:
        candidates = {str(value) for value in prediction.get("candidates", []) or []}
        if not gold.required_candidates.issubset(candidates):
            errors.append("required clarification candidates are missing")

    behavior_correct = not errors
    wrong_answer = answered and not behavior_correct
    # Với Gold số thông thường, một con số sai luôn là lỗi âm thầm. Với Gold yêu cầu
    # cảnh báo, chỉ cảnh báo đúng code và có định vị mới làm lỗi không còn "âm thầm".
    silent_wrong = wrong_answer and not required_warning_present

    return CaseScore(
        question_id=gold.question_id,
        expected_status=gold.status,
        predicted_status=predicted_status,
        answered=answered,
        wrong_answer=wrong_answer,
        behavior_correct=behavior_correct,
        silent_wrong=silent_wrong,
        unnecessary_clarification=unnecessary_clarification,
        specific_warning_present=specific_warning_present,
        row_total=row_total or len(gold.rows),
        row_correct=row_correct,
        errors=tuple(errors),
    )


def score_batch(
    gold_cases: Sequence[GoldCase],
    predictions: Sequence[Mapping[str, Any]],
) -> ScoreSummary:
    """Ghép theo question_id, phát hiện ID trùng và không bỏ câu bị thiếu."""

    prediction_by_id: dict[str, Mapping[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for prediction in predictions:
        question_id = str(prediction.get("question_id", ""))
        if question_id in prediction_by_id:
            duplicate_ids.add(question_id)
        prediction_by_id[question_id] = prediction

    cases: list[CaseScore] = []
    gold_ids = {gold.question_id for gold in gold_cases}
    for gold in gold_cases:
        if gold.question_id in duplicate_ids:
            cases.append(
                CaseScore(
                    question_id=gold.question_id,
                    expected_status=gold.status,
                    predicted_status=None,
                    answered=False,
                    wrong_answer=False,
                    behavior_correct=False,
                    silent_wrong=False,
                    unnecessary_clarification=False,
                    specific_warning_present=False,
                    row_total=len(gold.rows),
                    errors=("duplicate prediction question_id",),
                )
            )
        else:
            cases.append(score_case(gold, prediction_by_id.get(gold.question_id)))

    extras = tuple(sorted(set(prediction_by_id) - gold_ids - {""}))
    return ScoreSummary(cases=tuple(cases), extra_prediction_ids=extras)
