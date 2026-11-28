"""Hệ thống B0 đầu–cuối: câu hỏi → trạng thái hành động, câu hiểu lại, câu trả lời có kỳ cạnh số."""

import json

import pytest

from fin_assistant.b0 import B0System
from fin_assistant.b0.system import DISCLAIMER
from fin_assistant.semantic import Status

from .conftest import QDATE


def test_answer_number_with_period_and_trace(b0):
    a = b0.answer("Doanh thu thuần quý 3/2024 của AAA tăng bao nhiêu so với cùng kỳ?", QDATE)
    assert a.status is Status.OK
    assert a.result.value == pytest.approx(0.25)
    assert "Q3/2024" in a.text and "25,00%" in a.text
    assert a.text.endswith(DISCLAIMER)
    assert "Kỳ: 2024Q3 (tính tới ngày hỏi 2025-02-15)" in a.interpretation
    assert a.result.inputs  # truy vết source_ref


def test_answer_shows_assumptions(b0):
    a = b0.answer("Lợi nhuận của AAA", QDATE)
    assert a.status is Status.OK
    assert "Giả định:" in a.text and "cổ đông công ty mẹ" in a.text
    assert "kỳ gần nhất đã công bố" in a.interpretation


def test_bank_revenue_asks_for_clarification(b0):
    a = b0.answer("Doanh thu thuần quý 3/2024 của Ngân hàng Nam Hà là bao nhiêu?", QDATE)
    assert a.status is Status.NEEDS_CLARIFICATION
    assert a.candidates == ("bank_nii", "bank_toi", "bank_interest_income")
    assert a.result.value is None


def test_bank_revenue_clarification_in_multi(b0):
    a = b0.answer("So sánh doanh thu quý 3/2024 của AAA và NHA", QDATE)
    assert a.status is Status.NEEDS_CLARIFICATION
    assert "bank_nii" in a.candidates


def test_parser_level_clarification(b0, b0_clarify):
    assert b0.answer("Biên lợi nhuận của AAA quý 3/2024", QDATE).status is Status.NEEDS_CLARIFICATION
    a = b0_clarify.answer("Lợi nhuận của AAA quý 3/2024", QDATE)
    assert a.status is Status.NEEDS_CLARIFICATION
    assert a.result is None and a.query is None
    assert "loại lợi nhuận" in a.text


def test_negative_equity_roe_not_answered(b0):
    a = b0.answer("ROE của DDD quý 3/2024", QDATE)
    assert a.status is Status.NOT_MEANINGFUL
    assert "không trả số" in a.text


def test_screen_empty_valid_vs_missing(b0):
    ok = b0.answer("Trong AAA và NHA, công ty nào có ROE trên 50% quý 3/2024?", QDATE)
    assert ok.status is Status.EMPTY_VALID
    assert "Không có mã nào" in ok.text
    missing = b0.answer("Trong AAA và EEE, công ty nào có ROE trên 50% quý 3/2024?", QDATE)
    assert missing.status is Status.MISSING_DATA


def test_rank_answer(b0):
    a = b0.answer("Top 2 công ty có ROE cao nhất quý 3/2024", QDATE)
    assert a.status is Status.OK
    assert a.result.tickers == ["NHA", "AAA"]
    assert "top 2" in a.interpretation
    assert a.text.splitlines()[0].startswith("1. ")


def test_screen_interpretation(b0):
    a = b0.answer("Công ty nào có ROE trên 15% quý 3/2024?", QDATE)
    assert "lọc lớn hơn 15,00%" in a.interpretation
    a = b0.answer("Công ty nào có tăng trưởng biên lợi nhuận gộp quý 3/2024 trên 1 điểm phần trăm?", QDATE)
    assert a.query.transform == "yoy_pp"
    assert "điểm %" in a.interpretation


def test_universe_interpretation(b0):
    a = b0.answer("ROE các ngân hàng quý 3/2024", QDATE)
    assert "nhóm ngân hàng" in a.interpretation


def test_unsupported_abstains(b0):
    a = b0.answer("EPS của AAA năm 2024", QDATE)
    assert a.status is Status.NOT_APPLICABLE
    assert a.text.startswith("B0 không trả lời câu này")
    assert a.status.is_answer is False


def test_out_of_scope_ticker(b0):
    a = b0.answer("ROE của XYZ quý 3/2024", QDATE)
    assert a.status is Status.NOT_APPLICABLE


def test_not_yet_published(b0):
    a = b0.answer("Doanh thu thuần quý 4/2024 của AAA", "2024-12-20")
    assert a.status is Status.MISSING_DATA
    assert "chưa được công bố" in a.text


def test_question_date_governs_latest(b0):
    early = b0.answer("Doanh thu thuần gần nhất của AAA", "2024-11-15")
    late = b0.answer("Doanh thu thuần gần nhất của AAA", "2025-02-15")
    assert early.result.period == "Q3/2024" and late.result.period == "Q4/2024"


def test_to_dict_is_json_serialisable(b0):
    for question in ("ROE của AAA quý 3/2024", "Biên lợi nhuận của AAA", "Top 2 ROE quý 3/2024"):
        payload = json.loads(json.dumps(b0.answer(question, QDATE).to_dict(), ensure_ascii=False))
        assert payload["method"] == "B0" and payload["status"]


def test_answer_without_question_date(store):
    a = B0System(store).answer("Doanh thu thuần quý 3/2024 của AAA")
    assert a.status is Status.OK and a.question_date is None
    assert "tính tới ngày hỏi" not in a.interpretation
