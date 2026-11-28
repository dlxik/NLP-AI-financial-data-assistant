"""Ca biên còn lại: hợp đồng dữ liệu, hiển thị, kỳ gần nhất khi không mã nào có dữ liệu."""

import pandas as pd
import pytest

from fin_assistant.b0 import B0Parser
from fin_assistant.semantic import (
    DataContractError,
    FactStore,
    Period,
    RuleConfig,
    Status,
    WarnCode,
    describe,
    get_metric,
    get_metric_multi,
    metric_name,
)
from fin_assistant.semantic.periods import to_date
from fin_assistant.semantic.store import _as_bool, make_companies

from .conftest import companies_df, fact


# ---------------------------------------------------------------- hợp đồng dữ liệu
def _facts():
    return pd.DataFrame([fact("AAA", "2024Q1", "IS.NET_REVENUE", 1)])


@pytest.mark.parametrize(
    "mutate_facts, companies, match",
    [
        (None, pd.DataFrame([{"ticker": "AAA"}]), "bảng công ty thiếu cột"),
        (None, pd.DataFrame([{"ticker": "AAA", "group": "non_financial", "scope": "global"}]), "phạm vi"),
        (None, pd.DataFrame([{"ticker": "AAA", "group": "non_financial"}] * 2), "mã trùng"),
        (lambda d: d.assign(fiscal_quarter=5), None, "fiscal_quarter"),
        (lambda d: d.assign(period_type="H1"), None, "period_type"),
        (lambda d: d.assign(scope="global"), None, "scope không hợp lệ"),
    ],
)
def test_contract_violations(mutate_facts, companies, match):
    facts = _facts() if mutate_facts is None else mutate_facts(_facts())
    with pytest.raises(DataContractError, match=match):
        FactStore(facts, companies if companies is not None else companies_df())


@pytest.mark.parametrize("value, expected", [(None, False), (float("nan"), False), ("TRUE", True),
                                             ("x", True), ("0", False), (1, True)])
def test_as_bool(value, expected):
    assert _as_bool(value) is expected


def test_make_companies():
    df = make_companies([("AAA", "non_financial"), ("NHA", "bank")])
    assert list(df.columns) == ["ticker", "group"] and len(df) == 2


def test_aliases_ignore_blank(store):
    aliases = store.aliases()
    assert aliases["alpha corp"] == "AAA" and aliases["nam hà bank"] == "NHA"
    assert "" not in aliases and "nan" not in aliases


# ---------------------------------------------------------------- kỳ
def test_period_year_range_and_bad_inputs():
    with pytest.raises(ValueError):
        Period(1800, 1)
    with pytest.raises(ValueError):
        Period.parse(2024)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_date(20241030)  # type: ignore[arg-type]


def test_multi_latest_when_no_ticker_has_data(store):
    m = get_metric_multi(store, "net_revenue", ["NEW"], "latest")
    assert m.status is Status.MISSING_DATA
    assert m.rows[0].period is None


def test_per_ticker_policy_same_period_no_warning(store):
    cfg = RuleConfig(latest_policy_multi="per_ticker")
    m = get_metric_multi(store, "net_revenue", ["AAA", "CCC"], "latest", as_of="2025-02-15", config=cfg)
    assert WarnCode.MIXED_PERIODS not in m.warning_codes


def test_missing_equity_parent_base_metric(store):
    r = get_metric(store, "equity_parent", "EEE", "2024Q2")
    assert r.status is Status.MISSING_DATA
    assert any(w.code is WarnCode.MISSING_INPUT and w.item_code == "BS.EQUITY_PARENT" for w in r.warnings)


# ---------------------------------------------------------------- hiển thị
def test_describe_without_period(store):
    text = describe(get_metric(store, "net_revenue", "NEW", "latest"))
    assert text.startswith("Doanh thu thuần của NEW: không trả số")


def test_describe_ok_with_warning(store):
    text = describe(get_metric(store, "net_revenue", "CCC", "2024Q2", transform="yoy"))
    assert "⚠" in text and "thận trọng" in text


def test_metric_name_invalid_suffix():
    assert metric_name("net_revenue_abc") == "net_revenue_abc"


# ---------------------------------------------------------------- B0: nhánh hiếm
def test_b0_stock_metric_full_year(store):
    res = B0Parser(store).parse("Tổng tài sản năm 2024 của AAA", "2025-02-15")
    assert res.query.period == "2024Q4" and res.query.transform is None
    assert any("cuối năm 2024" in a for a in res.assumptions)


def test_b0_bare_threshold_for_times_metric(store):
    res = B0Parser(store).parse("Công ty nào có nợ phải trả trên vốn chủ dưới 1 quý 3/2024?", "2025-02-15")
    assert res.query.cmp == "<" and res.query.threshold == pytest.approx(1.0)


def test_b0_ratio_fraction_threshold(store):
    res = B0Parser(store).parse("Công ty nào có ROE trên 0,15 quý 3/2024?", "2025-02-15")
    assert res.query.threshold == pytest.approx(0.15)


def test_b0_repeated_ticker_and_metric(store):
    res = B0Parser(store).parse("ROE của AAA, ROE của AAA quý 3/2024", "2025-02-15")
    assert res.query.tickers == ("AAA",) and res.query.metric == "roe_ttm"
