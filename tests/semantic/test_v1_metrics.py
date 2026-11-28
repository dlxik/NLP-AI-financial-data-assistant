"""Semantic Layer v1.0 — 14 chỉ số chính thức và phép biến đổi lớp 3 (YTD, TTM, YoY, QoQ, điểm %)."""

import pytest

from fin_assistant.semantic import (
    METRICS,
    OFFICIAL_METRICS,
    RuleConfig,
    Status,
    TransformError,
    WarnCode,
    describe,
    format_value,
    get_metric,
    metric_name,
    parse_transform,
)
from fin_assistant.semantic.catalog import Transform, check_transform


# ================================================================ danh mục
def test_official_catalog_has_14_metrics_in_two_layers():
    assert len(OFFICIAL_METRICS) == 14
    layers = [METRICS[m].layer for m in OFFICIAL_METRICS]
    assert layers.count("base") == 9 and layers.count("derived") == 5
    assert "bank_interest_income" not in OFFICIAL_METRICS  # trường hỗ trợ cho câu hỏi làm rõ


@pytest.mark.parametrize(
    "spec, expected",
    [
        (None, Transform()),
        ("q", Transform()),
        ("yoy", Transform("q", "yoy")),
        ("ytd", Transform("ytd")),
        ("ttm_yoy", Transform("ttm", "yoy")),
        ("ytd_yoy", Transform("ytd", "yoy")),
        ("yoy_pp", Transform("q", "yoy", True)),
        ("TTM_QOQ_PP", Transform("ttm", "qoq", True)),
    ],
)
def test_parse_transform(spec, expected):
    assert parse_transform(spec) == expected


@pytest.mark.parametrize("spec", ["mom", "yoy_qoq", "pp", "ytd_ttm", "yoy_pp_x"])
def test_parse_transform_rejects(spec):
    with pytest.raises(TransformError):
        parse_transform(spec)


@pytest.mark.parametrize(
    "metric, spec, match",
    [
        ("equity_parent", "ytd", "cửa sổ"),        # stock không có lũy kế
        ("roe_ttm", "ttm", "cửa sổ"),              # ROE đã là TTM
        ("gross_margin", "yoy", "_pp"),            # tỷ lệ → phải dùng điểm %
        ("net_revenue", "yoy_pp", "tiền tệ"),      # tiền tệ → không dùng điểm %
        ("net_revenue", "ytd_qoq", "lũy kế"),      # lũy kế chỉ so cùng kỳ
        ("liabilities_to_equity", "yoy", "không hỗ trợ"),
    ],
)
def test_check_transform_type_rules(metric, spec, match):
    with pytest.raises(TransformError, match=match):
        check_transform(METRICS[metric], parse_transform(spec))


def test_transform_name_roundtrip():
    for spec in ("yoy", "ytd", "ttm_yoy", "yoy_pp", "ytd_yoy_pp"):
        assert parse_transform(spec).name == spec
    assert parse_transform(None).name is None


# ================================================================ lớp 1 mới
@pytest.mark.parametrize(
    "metric, ticker, expected_bn",
    [
        ("gross_profit", "AAA", 450),
        ("npat", "AAA", 160),
        ("npat", "NHA", 2350),
        ("total_assets", "AAA", 11200),
        ("total_assets", "NHA", 600000),
        ("total_liabilities", "AAA", 5400),
        ("equity_parent", "AAA", 5600),
    ],
)
def test_base_metrics(store, metric, ticker, expected_bn):
    r = get_metric(store, metric, ticker, "2024Q3")
    assert r.status is Status.OK
    assert r.value == pytest.approx(expected_bn * 1e9)
    assert r.unit == "VND"


@pytest.mark.parametrize("metric", ["gross_profit", "total_liabilities", "gross_margin", "net_margin",
                                    "liabilities_to_equity"])
def test_non_financial_only_metrics_refuse_banks(store, metric):
    r = get_metric(store, metric, "NHA", "2024Q3")
    assert r.status is Status.NOT_APPLICABLE
    assert WarnCode.METRIC_NOT_APPLICABLE in r.warning_codes


# ================================================================ cửa sổ
class TestWindows:
    def test_ytd_prefers_reported_cumulative_column(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ytd")
        assert r.value == pytest.approx(3810e9)
        assert [i.period for i in r.inputs] == ["YTD Q3/2024"]
        assert WarnCode.DERIVED_VALUE not in r.warning_codes

    def test_ytd_sums_quarters_when_not_reported(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q2", transform="ytd")
        assert r.value == pytest.approx((1100 + 1210) * 1e9)
        assert len(r.inputs) == 2
        info = next(w for w in r.warnings if w.code is WarnCode.DERIVED_VALUE)
        assert info.severity == "info" and "Q1/2024..Q2/2024" in info.message

    def test_ytd_of_q1_is_the_quarter(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q1", transform="ytd")
        assert r.value == pytest.approx(1100e9)
        assert WarnCode.DERIVED_VALUE not in r.warning_codes

    def test_ytd_missing_quarter_is_named(self, store):
        r = get_metric(store, "npat_parent", "CCC", "2024Q2", transform="ytd")
        assert r.status is Status.MISSING_DATA
        assert any(w.code is WarnCode.MISSING_INPUT and w.period == "Q1/2024" for w in r.warnings)

    def test_ttm_sum(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ttm")
        assert r.value == pytest.approx((1300 + 1100 + 1210 + 1500) * 1e9)
        assert r.details["window"] == "ttm"

    def test_full_year_equals_ytd_q4(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q4", transform="ytd")
        assert r.value == pytest.approx((1100 + 1210 + 1500 + 1430) * 1e9)

    def test_describe_uses_window_label(self, store):
        assert "lũy kế 9 tháng 2024" in describe(get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ytd"))
        assert "4 quý đến Q3/2024" in describe(get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ttm"))


# ================================================================ phép so sánh
class TestChanges:
    def test_qoq(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="qoq")
        assert r.value == pytest.approx((1500 - 1210) / 1210)
        assert r.details["base_period"] == "Q2/2024"

    def test_ytd_yoy_uses_reported_cumulative_columns(self, store):
        """Cặp đối lập 'Q3 vs lũy kế 9 tháng': hai kết quả phải khác nhau."""
        q3 = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="yoy")
        ytd = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ytd_yoy")
        assert q3.value == pytest.approx(0.25)
        assert ytd.value == pytest.approx(3810 / 3300 - 1)
        assert q3.value != pytest.approx(ytd.value)

    def test_ttm_yoy(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q4", transform="ttm_yoy")
        assert r.value == pytest.approx((1100 + 1210 + 1500 + 1430) / (1000 + 1100 + 1200 + 1300) - 1)

    def test_ratio_change_is_percentage_points(self, store):
        """Cặp đối lập '% YoY vs điểm %'."""
        r = get_metric(store, "net_margin", "AAA", "2024Q3", transform="yoy_pp")
        assert r.unit == "pp"
        assert r.value == pytest.approx(160 / 1500 - 130 / 1200)
        assert format_value(r.value, r.unit).endswith("điểm %")

    def test_roe_yoy_pp_needs_both_ends(self, store):
        r = get_metric(store, "roe_ttm", "AAA", "2024Q4", transform="yoy_pp")
        assert r.status is Status.MISSING_DATA  # ROE Q4/2023 cần VCSH Q4/2022 — không có
        assert any(w.item_code == "BS.EQUITY_PARENT" and w.period == "Q4/2022" for w in r.warnings)

    def test_qoq_pp_on_roe(self, store):
        r = get_metric(store, "roe_ttm", "NHA", "2024Q3", transform="qoq_pp")
        assert r.status is Status.MISSING_DATA  # ROE Q2/2024 cần VCSH Q2/2023 — thiếu
        assert any(w.period == "Q2/2023" for w in r.warnings)

    def test_change_propagates_not_meaningful(self, store):
        r = get_metric(store, "roe_ttm", "BBB", "2024Q4", transform="yoy_pp")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.NEGATIVE_EQUITY in r.warning_codes

    def test_stock_yoy(self, store):
        r = get_metric(store, "total_assets", "AAA", "2024Q3", transform="yoy")
        assert r.value == pytest.approx(11200 / 10400 - 1)

    def test_metric_name_for_transforms(self):
        assert metric_name("net_revenue_ytd_yoy") == "Tăng trưởng doanh thu thuần so với cùng kỳ"
        assert metric_name("gross_margin_qoq_pp") == "Thay đổi biên lợi nhuận gộp so với quý trước"
        assert metric_name("net_revenue_qoq") == "Tăng trưởng doanh thu thuần so với quý trước"
        assert metric_name("roe_ttm") == "ROE 4 quý gần nhất (TTM)"
        assert metric_name("unknown_metric") == "unknown_metric"


# ================================================================ lớp 2
class TestDerived:
    @pytest.mark.parametrize("transform, num, den", [
        (None, 450, 1500),
        ("ytd", 330 + 363 + 450, 3810),   # tử số cộng quý, mẫu số dùng cột lũy kế công bố
        ("ttm", 390 + 330 + 363 + 450, 1300 + 1100 + 1210 + 1500),
    ])
    def test_gross_margin_windows(self, store, transform, num, den):
        r = get_metric(store, "gross_margin", "AAA", "2024Q3", transform=transform)
        assert r.status is Status.OK
        assert r.value == pytest.approx(num / den)
        assert r.unit == "ratio"

    def test_net_margin_uses_total_npat(self, store):
        r = get_metric(store, "net_margin", "AAA", "2024Q3")
        assert r.value == pytest.approx(160 / 1500)
        assert {i.item_code for i in r.inputs} == {"IS.NPAT", "IS.NET_REVENUE"}

    def test_margin_zero_revenue_not_meaningful(self):
        import pandas as pd

        from fin_assistant.semantic import FactStore

        from .conftest import companies_df, fact

        rows = [fact("AAA", "2024Q1", "IS.NET_REVENUE", 0), fact("AAA", "2024Q1", "IS.GROSS_PROFIT", 5)]
        s = FactStore(pd.DataFrame(rows), companies_df())
        r = get_metric(s, "gross_margin", "AAA", "2024Q1")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.NON_POSITIVE_BASE in r.warning_codes

    def test_margin_missing_component(self, store):
        r = get_metric(store, "gross_margin", "CCC", "2024Q3")
        assert r.status is Status.MISSING_DATA
        assert any(w.item_code == "IS.GROSS_PROFIT" for w in r.warnings)

    def test_roa_two_point(self, store):
        r = get_metric(store, "roa_ttm", "AAA", "2024Q3")
        assert r.value == pytest.approx((140 + 130 + 140 + 160) / ((10400 + 11200) / 2))
        assert r.details["avg_method"] == "two_point"

    def test_roa_five_point_bank(self, store):
        r = get_metric(store, "roa_ttm", "NHA", "2024Q3", config=RuleConfig(equity_avg_method="five_point"))
        avg = (500000 + 520000 + 540000 + 570000 + 600000) / 5
        assert r.value == pytest.approx((2050 + 2150 + 2250 + 2350) / avg)

    def test_roa_missing_assets_with_fallback(self, store):
        r = get_metric(store, "roa_ttm", "NHA", "2024Q2")
        assert r.status is Status.MISSING_DATA
        assert any(w.item_code == "BS.TOTAL_ASSETS" and w.period == "Q2/2023" for w in r.warnings)
        # đủ 4 quý LNST + có tổng tài sản cuối kỳ → fallback (R6) áp dụng cả cho ROA
        r2 = get_metric(store, "roa_ttm", "NHA", "2024Q2", config=RuleConfig(allow_ending_equity_fallback=True))
        assert r2.status is Status.OK
        assert r2.value == pytest.approx((1950 + 2050 + 2150 + 2250) / 570000)
        assert WarnCode.FALLBACK_ENDING_EQUITY in r2.warning_codes

    def test_roa_non_positive_assets(self):
        import pandas as pd

        from fin_assistant.semantic import FactStore

        from .conftest import companies_df, series

        rows = series("AAA", "IS.NPAT", [1] * 8) + series("AAA", "BS.TOTAL_ASSETS", [0] * 8)
        r = get_metric(FactStore(pd.DataFrame(rows), companies_df()), "roa_ttm", "AAA", "2024Q4")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.NON_POSITIVE_BASE in r.warning_codes

    def test_liabilities_to_equity(self, store):
        r = get_metric(store, "liabilities_to_equity", "AAA", "2024Q3")
        assert r.value == pytest.approx(5400 / 5800)
        assert r.unit == "times"
        assert format_value(r.value, r.unit) == "0,93 lần"
        assert "không phải nợ vay" in r.formula

    def test_liabilities_to_negative_equity_not_meaningful(self, store):
        r = get_metric(store, "liabilities_to_equity", "DDD", "2024Q3")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.NEGATIVE_EQUITY in r.warning_codes

    def test_liabilities_to_equity_missing(self, store):
        r = get_metric(store, "liabilities_to_equity", "CCC", "2024Q3")
        assert r.status is Status.MISSING_DATA

    def test_extreme_margin_warns(self):
        import pandas as pd

        from fin_assistant.semantic import FactStore

        from .conftest import companies_df, fact

        rows = [fact("AAA", "2024Q1", "IS.NET_REVENUE", 2), fact("AAA", "2024Q1", "IS.NPAT", 50)]
        r = get_metric(FactStore(pd.DataFrame(rows), companies_df()), "net_margin", "AAA", "2024Q1")
        assert r.status is Status.OK
        assert WarnCode.EXTREME_VALUE in r.warning_codes

    def test_near_zero_revenue_margin(self):
        import pandas as pd

        from fin_assistant.semantic import FactStore

        from .conftest import companies_df, fact

        rows = [fact("AAA", "2024Q1", "IS.NET_REVENUE", 0.2), fact("AAA", "2024Q1", "IS.GROSS_PROFIT", 0.1)]
        r = get_metric(FactStore(pd.DataFrame(rows), companies_df()), "gross_margin", "AAA", "2024Q1")
        assert r.status is Status.NOT_MEANINGFUL
        assert WarnCode.DENOMINATOR_NEAR_ZERO in r.warning_codes

    def test_formula_mentions_window_and_change(self, store):
        r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ytd_yoy")
        assert "lũy kế 9 tháng 2024" in r.formula and "lũy kế 9 tháng 2023" in r.formula
        r = get_metric(store, "roe_ttm", "AAA", "2024Q3", config=RuleConfig(equity_avg_method="five_point"))
        assert "5 điểm" in r.formula
        r = get_metric(store, "gross_margin", "AAA", "2024Q3", transform="yoy_pp")
        assert "điểm %" in r.formula


def test_format_value_units():
    assert format_value(None, "VND") == "—"
    assert format_value(-0.0123, "pp") == "-1,23 điểm %"
    assert format_value(0.0123, "pp") == "+1,23 điểm %"
    assert format_value(1234.5, None) == "1.234,50"
