"""Bộ hàm pilot — 3 đại lượng của Giai đoạn 1.

(1) Doanh thu thuần quý & YoY (phi tài chính); (2) ROE TTM (cả 2 nhóm);
(3) "doanh thu thuần" của ngân hàng → hỏi làm rõ.
"""

import json

import pytest

from fin_assistant.semantic import (
    RuleConfig,
    Status,
    UnknownMetricError,
    WarnCode,
    describe,
    get_metric,
)


# =============================================================== (1) doanh thu
class TestNetRevenue:
    def test_quarter_value_with_trace(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q3")
        assert r.status is Status.OK
        assert r.value == 1500e9
        assert r.unit == "VND"
        assert r.period == "Q3/2024"
        assert [i.source_ref for i in r.inputs] == ["AAA/2024Q3/IS.NET_REVENUE/v1"]

    def test_yoy_standard(self, store):
        r = get_metric(store, "net_revenue", "AAA", "Q3/2024", transform="yoy")
        assert r.metric == "net_revenue_yoy"
        assert r.status is Status.OK
        assert r.value == pytest.approx((1500 - 1200) / 1200)
        assert r.unit == "ratio"
        assert r.details["base_period"] == "Q3/2023"
        assert r.details["abs_change"] == pytest.approx(300e9)
        assert len(r.inputs) == 2

    def test_yoy_negative_growth(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q4", transform="yoy")
        assert r.status is Status.OK
        assert r.value == pytest.approx((1430 - 1300) / 1300)

    def test_yoy_zero_base_not_meaningful(self, store):
        r = get_metric(store, "net_revenue", "CCC", "2024Q1", transform="yoy")
        assert r.status is Status.NOT_MEANINGFUL
        assert r.value is None
        w = next(w for w in r.warnings if w.code is WarnCode.NON_POSITIVE_BASE)
        assert w.ticker == "CCC" and w.period == "Q1/2023"  # cảnh báo nêu đúng mã + kỳ gốc
        assert r.details["abs_change"] == pytest.approx(100e9)  # vẫn cung cấp chênh lệch tuyệt đối

    def test_yoy_near_zero_base_not_meaningful(self, store):
        r = get_metric(store, "net_revenue", "CCC", "2024Q3", transform="yoy")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.DENOMINATOR_NEAR_ZERO in r.warning_codes

    def test_yoy_extreme_value_answers_with_warning(self, store):
        r = get_metric(store, "net_revenue", "CCC", "2024Q2", transform="yoy")
        assert r.status is Status.OK
        assert r.value == pytest.approx(24.0)
        assert WarnCode.EXTREME_VALUE in r.warning_codes

    def test_yoy_missing_base_period(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2023Q2", transform="yoy")
        assert r.status is Status.MISSING_DATA
        w = next(w for w in r.warnings if w.code is WarnCode.MISSING_INPUT)
        assert w.period == "Q2/2022" and w.item_code == "IS.NET_REVENUE"

    def test_not_yet_published_differs_from_missing(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q3", as_of="2024-10-15")
        assert r.status is Status.MISSING_DATA
        assert WarnCode.NOT_YET_PUBLISHED in r.warning_codes
        assert WarnCode.MISSING_INPUT not in r.warning_codes

    def test_quarter_not_ended_at_question_date(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q4", as_of="2024-12-01")
        assert r.status is Status.MISSING_DATA
        assert WarnCode.NOT_YET_PUBLISHED in r.warning_codes

    def test_restated_base_is_used_and_disclosed(self, store):
        before = get_metric(store, "net_revenue", "EEE", "2023Q3", as_of="2024-01-01")
        after = get_metric(store, "net_revenue", "EEE", "2023Q3", as_of="2024-11-01")
        assert before.value == 800e9 and WarnCode.RESTATED_VALUE not in before.warning_codes
        assert after.value == 900e9 and WarnCode.RESTATED_VALUE in after.warning_codes
        yoy = get_metric(store, "net_revenue", "EEE", "2024Q3", transform="yoy", as_of="2024-11-01")
        assert yoy.value == pytest.approx((990 - 900) / 900)
        assert yoy.status is Status.OK  # cảnh báo hồi tố chỉ là info

    def test_derived_q4_is_disclosed(self, store):
        r = get_metric(store, "net_revenue", "EEE", "2023Q4")
        assert r.status is Status.OK
        info = next(w for w in r.warnings if w.code is WarnCode.DERIVED_VALUE)
        assert info.severity == "info" and "YTD→Q" in info.message
        assert r.inputs[0].derived_from is not None


# =============================================================== (2) ROE TTM
class TestRoeTtm:
    def test_non_financial_two_point(self, store):
        r = get_metric(store, "roe_ttm", "AAA", "2024Q3")
        assert r.status is Status.OK
        # Σ LNST mẹ Q4/23..Q3/24 = 130+120+130+150 = 530 ; VCSH mẹ (5200 + 5600)/2 = 5400
        assert r.value == pytest.approx(530 / 5400)
        assert r.unit == "ratio"
        assert r.details["npat_parent_ttm"] == pytest.approx(530e9)
        assert r.details["equity_avg"] == pytest.approx(5400e9)

    def test_equity_parent_derived_from_total_minus_nci(self, store):
        r = get_metric(store, "roe_ttm", "AAA", "2024Q3")
        items = {i.item_code for i in r.inputs}
        assert {"BS.EQUITY_TOTAL", "BS.NCI", "IS.NPAT_PARENT"} <= items
        assert any(w.code is WarnCode.DERIVED_VALUE and w.item_code == "BS.EQUITY_PARENT" for w in r.warnings)

    def test_five_point_average(self, store):
        r = get_metric(store, "roe_ttm", "AAA", "2024Q3", config=RuleConfig(equity_avg_method="five_point"))
        # VCSH mẹ Q3/23..Q3/24 = 5200, 5300, 5000, 5500, 5600 → bình quân 5320
        assert r.value == pytest.approx(530 / 5320)
        assert len(r.details["equity_points"]) == 5

    def test_bank_two_point(self, store):
        r = get_metric(store, "roe_ttm", "NHA", "2024Q3")
        assert r.status is Status.OK
        assert r.value == pytest.approx((2000 + 2100 + 2200 + 2300) / ((50000 + 60000) / 2))

    def test_bank_five_point(self, store):
        cfg = RuleConfig(equity_avg_method="five_point")
        r = get_metric(store, "roe_ttm", "NHA", "2024Q3", config=cfg)
        assert r.value == pytest.approx(8600 / ((50000 + 52000 + 54000 + 57000 + 60000) / 5))

    def test_negative_ending_equity_not_meaningful(self, store):
        r = get_metric(store, "roe_ttm", "BBB", "2024Q3")
        assert r.status is Status.NOT_MEANINGFUL
        assert r.value is None
        w = next(w for w in r.warnings if w.code is WarnCode.NEGATIVE_EQUITY)
        assert w.ticker == "BBB" and w.period == "Q3/2024"

    def test_negative_equity_and_loss_do_not_produce_positive_roe(self, store):
        """Cặp đối lập: lỗ / VCSH âm cho tỷ số dương (−200/−600 ≈ +33%) — phải 'không xác định'."""
        r = get_metric(store, "roe_ttm", "DDD", "2024Q3")
        assert r.status is Status.NOT_MEANINGFUL
        assert r.value is None
        assert WarnCode.NEGATIVE_EQUITY in r.warning_codes

    def test_negative_roe_with_positive_equity_is_valid(self, store):
        r = get_metric(store, "roe_ttm", "BBB", "2024Q1")
        assert r.status is Status.OK
        assert r.value == pytest.approx(-200 / ((400 + 150) / 2))

    def test_missing_quarter_of_npat_is_named(self, store):
        r = get_metric(store, "roe_ttm", "CCC", "2024Q3")
        assert r.status is Status.MISSING_DATA
        missing = [w for w in r.warnings if w.code is WarnCode.MISSING_INPUT]
        assert [(w.item_code, w.period) for w in missing] == [("IS.NPAT_PARENT", "Q1/2024")]

    def test_missing_beginning_equity_default_is_missing(self, store):
        r = get_metric(store, "roe_ttm", "EEE", "2024Q3")
        assert r.status is Status.MISSING_DATA
        w = next(w for w in r.warnings if w.code is WarnCode.MISSING_INPUT)
        assert (w.item_code, w.period) == ("BS.EQUITY_PARENT", "Q3/2023")

    def test_missing_beginning_equity_with_explicit_fallback(self, store):
        cfg = RuleConfig(allow_ending_equity_fallback=True)
        r = get_metric(store, "roe_ttm", "EEE", "2024Q3", config=cfg)
        assert r.status is Status.OK
        assert r.value == pytest.approx((50 + 60 + 70 + 80) / 2000)
        assert WarnCode.FALLBACK_ENDING_EQUITY in r.warning_codes
        assert WarnCode.MISSING_INPUT not in r.warning_codes
        assert r.details["equity_avg_method"] == "ending_only"

    def test_fallback_does_not_hide_missing_npat(self, store):
        cfg = RuleConfig(allow_ending_equity_fallback=True)
        r = get_metric(store, "roe_ttm", "EEE", "2024Q4", config=cfg)
        assert r.status is Status.MISSING_DATA

    def test_missing_beginning_equity_bank(self, store):
        """NHA đủ 4 quý LNST nhưng thiếu VCSH Q2/2023 → mặc định báo thiếu, không tự dùng cuối kỳ."""
        r = get_metric(store, "roe_ttm", "NHA", "2024Q2")
        assert r.status is Status.MISSING_DATA
        assert r.value is None
        w = next(w for w in r.warnings if w.code is WarnCode.MISSING_INPUT)
        assert (w.item_code, w.period) == ("BS.EQUITY_PARENT", "Q2/2023")

    def test_no_annualisation_from_partial_year(self, store):
        """EEE chỉ có 3 quý LNST (Q4/23..Q2/24) → không được nhân 4/3 để ra ROE TTM."""
        cfg = RuleConfig(allow_ending_equity_fallback=True)
        r = get_metric(store, "roe_ttm", "EEE", "2024Q2", config=cfg)
        assert r.status is Status.MISSING_DATA
        assert any(w.code is WarnCode.MISSING_INPUT and w.period == "Q3/2023" for w in r.warnings)

    def test_near_zero_equity(self):
        import pandas as pd

        from fin_assistant.semantic import FactStore

        from .conftest import companies_df, fact, series

        rows = series("AAA", "IS.NPAT_PARENT", [1, 1, 1, 1, 1, 1, 1, 1])
        rows += series("AAA", "BS.EQUITY_PARENT", [0.4] * 8)
        tiny = FactStore(pd.DataFrame(rows), companies_df())
        r = get_metric(tiny, "roe_ttm", "AAA", "2024Q4")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.DENOMINATOR_NEAR_ZERO in r.warning_codes


# =============================================================== (3) ngân hàng
class TestBankNetRevenue:
    @pytest.mark.parametrize("transform", [None, "yoy"])
    @pytest.mark.parametrize("period", ["2024Q3", "latest"])
    def test_asks_for_clarification_and_never_substitutes(self, store, transform, period):
        r = get_metric(store, "net_revenue", "NHA", period, transform=transform)
        assert r.status is Status.NEEDS_CLARIFICATION
        assert r.value is None
        assert r.inputs == ()  # không đọc bất kỳ ô số nào → không thể "lén" thay bằng NII
        assert r.candidates == ("bank_nii", "bank_toi", "bank_interest_income")
        w = next(w for w in r.warnings if w.code is WarnCode.BANK_NO_NET_REVENUE)
        assert w.ticker == "NHA"
        assert "Doanh thu thuần" in w.message

    def test_candidates_are_computable_after_clarification(self, store):
        nii = get_metric(store, "bank_nii", "NHA", "2024Q3")
        toi = get_metric(store, "bank_toi", "NHA", "2024Q3")
        assert nii.status is Status.OK and nii.value == 5000e9
        assert toi.status is Status.OK and toi.value == 6500e9
        assert get_metric(store, "bank_nii", "NHA", "2024Q3", transform="yoy").value == pytest.approx(0.25)

    def test_bank_metric_not_applicable_to_non_financial(self, store):
        r = get_metric(store, "bank_nii", "AAA", "2024Q3")
        assert r.status is Status.NOT_APPLICABLE
        assert WarnCode.METRIC_NOT_APPLICABLE in r.warning_codes


# =============================================================== điều phối chung
class TestDispatch:
    def test_out_of_scope_ticker(self, store):
        r = get_metric(store, "net_revenue", "ZZZ", "2024Q3")
        assert r.status is Status.NOT_APPLICABLE
        assert WarnCode.OUT_OF_SCOPE_TICKER in r.warning_codes

    def test_unknown_metric_and_transform_raise(self, store):
        with pytest.raises(UnknownMetricError):
            get_metric(store, "ebitda", "AAA", "2024Q3")
        with pytest.raises(UnknownMetricError):
            get_metric(store, "roe_ttm", "AAA", "2024Q3", transform="yoy")

    def test_latest_single_ticker_uses_question_date(self, store):
        r = get_metric(store, "net_revenue", "AAA", "latest", as_of="2024-11-15")
        assert r.period == "Q3/2024" and r.value == 1500e9
        assert r.details["period_resolved_from"] == "latest"
        r = get_metric(store, "roe_ttm", "AAA", "latest", as_of="2025-02-15")
        assert r.period == "Q4/2024"
        assert r.value == pytest.approx((120 + 130 + 150 + 140) / ((5300 + 5700) / 2))

    def test_latest_without_any_publication(self, store):
        r = get_metric(store, "net_revenue", "NEW", "latest")
        assert r.status is Status.MISSING_DATA
        assert r.period is None

    def test_result_is_json_serialisable(self, store):
        r = get_metric(store, "roe_ttm", "AAA", "2024Q3")
        payload = json.loads(json.dumps(r.to_dict(), ensure_ascii=False))
        assert payload["status"] == "ok"
        assert payload["inputs"][0]["source_ref"]

    def test_describe_puts_period_next_to_number(self, store):
        text = describe(get_metric(store, "net_revenue", "AAA", "2024Q3"))
        assert text == "Doanh thu thuần Q3/2024 của AAA: 1.500,0 tỷ đồng"
        text = describe(get_metric(store, "net_revenue", "AAA", "2024Q3", transform="yoy"))
        assert "Q3/2024" in text and "25,00%" in text
        text = describe(get_metric(store, "roe_ttm", "DDD", "2024Q3"))
        assert "không trả số" in text and "DDD" in text
