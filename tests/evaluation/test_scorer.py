from __future__ import annotations

import math

from fin_assistant.evaluation import GoldCase, score_batch, score_case


def gold_single(**overrides):
    data = {
        "question_id": "q1",
        "status": "ok",
        "answer_type": "single",
        "metric": "net_revenue_yoy",
        "ticker": "FPT",
        "period": "2025Q3",
        "value": 0.125,
        "unit": "ratio",
        "abs_tol": 1e-9,
        "rel_tol": 1e-6,
    }
    data.update(overrides)
    return GoldCase.from_dict(data)


def pred_single(**overrides):
    data = {
        "question_id": "q1",
        "status": "ok",
        "answer_type": "single",
        "metric": "net_revenue_yoy",
        "ticker": "FPT",
        "period": "2025Q3",
        "value": 0.125,
        "unit": "ratio",
        "warnings": [],
    }
    data.update(overrides)
    return data


def test_correct_single_answer_with_tolerance():
    result = score_case(gold_single(), pred_single(value=0.12500001))

    assert result.answered
    assert result.behavior_correct
    assert not result.wrong_answer
    assert not result.silent_wrong


def test_wrong_number_is_wrong_and_silent():
    result = score_case(gold_single(), pred_single(value=0.5))

    assert result.answered
    assert result.wrong_answer
    assert result.silent_wrong
    assert "value outside tolerance" in result.errors


def test_period_swap_is_detected_even_when_value_matches():
    result = score_case(gold_single(), pred_single(period="2024Q3"))

    assert result.wrong_answer
    assert "period mismatch" in result.errors


def test_generic_warning_does_not_satisfy_required_warning():
    gold = gold_single(
        status="not_meaningful",
        answer_type="action",
        value=None,
        required_warning_codes=["negative_equity"],
    )
    prediction = pred_single(
        status="not_meaningful",
        answer_type="action",
        value=None,
        warnings=[
            {
                "code": "negative_equity",
                "message": "Có vấn đề với dữ liệu.",
                "ticker": None,
                "period": None,
                "item_code": None,
            }
        ],
    )

    result = score_case(gold, prediction)

    assert not result.behavior_correct
    assert not result.specific_warning_present
    assert "missing specific required warning" in result.errors


def test_specific_warning_satisfies_action_gold():
    gold = gold_single(
        status="not_meaningful",
        answer_type="action",
        value=None,
        required_warning_codes=["negative_equity"],
    )
    prediction = pred_single(
        status="not_meaningful",
        answer_type="action",
        value=None,
        warnings=[
            {
                "code": "negative_equity",
                "message": "VCSH của FPT tại 2025Q3 <= 0.",
                "ticker": "FPT",
                "period": "2025Q3",
                "item_code": "BS.EQUITY_PARENT",
            }
        ],
    )

    result = score_case(gold, prediction)

    assert result.behavior_correct
    assert not result.answered  # Hành động đúng không làm tăng A theo định nghĩa kế hoạch.


def test_unnecessary_clarification_is_counted():
    prediction = pred_single(
        status="needs_clarification",
        answer_type="action",
        value=None,
        candidates=["YoY", "QoQ"],
    )
    result = score_case(gold_single(), prediction)

    assert result.unnecessary_clarification
    assert not result.answered
    assert not result.behavior_correct


def test_clarification_requires_expected_candidates():
    gold = gold_single(
        status="needs_clarification",
        answer_type="action",
        value=None,
        required_candidates=["bank_nii", "bank_toi"],
    )
    incomplete = pred_single(
        status="needs_clarification",
        answer_type="action",
        value=None,
        candidates=["bank_nii"],
    )

    assert not score_case(gold, incomplete).behavior_correct
    complete = dict(incomplete, candidates=["bank_nii", "bank_toi"])
    assert score_case(gold, complete).behavior_correct


def test_empty_valid_is_an_answer_distinct_from_missing_data():
    gold = GoldCase.from_dict(
        {
            "question_id": "screen0",
            "status": "empty_valid",
            "answer_type": "table",
            "metric": "roe_ttm",
            "rows": [],
        }
    )
    result = score_case(
        gold,
        {
            "question_id": "screen0",
            "status": "empty_valid",
            "answer_type": "table",
            "metric": "roe_ttm",
            "rows": [],
            "warnings": [],
        },
    )

    assert result.answered
    assert result.behavior_correct


def test_table_scores_rows_and_requires_whole_question_exact_match():
    gold = GoldCase.from_dict(
        {
            "question_id": "rank1",
            "status": "ok",
            "answer_type": "table",
            "metric": "net_revenue",
            "rows": [
                {"ticker": "FPT", "period": "2025Q3", "value": 10.0, "unit": "VND"},
                {"ticker": "HPG", "period": "2025Q3", "value": 20.0, "unit": "VND"},
            ],
        }
    )
    prediction = {
        "question_id": "rank1",
        "status": "ok",
        "answer_type": "table",
        "metric": "net_revenue",
        "rows": [
            {
                "ticker": "FPT",
                "period": "2025Q3",
                "status": "ok",
                "metric": "net_revenue",
                "value": 20.0,
                "unit": "VND",
            },
            {
                "ticker": "HPG",
                "period": "2025Q3",
                "status": "ok",
                "metric": "net_revenue",
                "value": 10.0,
                "unit": "VND",
            },
        ],
        "warnings": [],
    }

    result = score_case(gold, prediction)

    assert result.row_total == 2
    assert result.row_correct == 0
    assert result.wrong_answer


def test_batch_keeps_missing_cases_and_four_required_metrics():
    gold = [gold_single(), gold_single(question_id="q2")]
    report = score_batch(gold, [pred_single()])
    summary = report.to_dict()

    assert summary["N"] == 2
    assert summary["A"] == 1
    assert summary["W"] == 0
    assert summary["answer_rate_A_over_N"] == 0.5
    assert summary["wrong_among_answered_W_over_A"] == 0.0
    assert summary["overall_correct_A_minus_W_over_N"] == 0.5
    assert summary["silent_wrong_count"] == 0


def test_zero_answer_batch_does_not_divide_by_zero():
    report = score_batch([gold_single()], []).to_dict()

    assert report["wrong_among_answered_W_over_A"] is None
    assert report["answer_rate_A_over_N"] == 0.0


def test_duplicate_predictions_are_rejected():
    report = score_batch([gold_single()], [pred_single(), pred_single()])

    assert not report.cases[0].behavior_correct
    assert "duplicate prediction question_id" in report.cases[0].errors
