"""Hợp đồng dữ liệu và tra cứu theo ngày hỏi / phiên bản (T1–T3)."""

import pandas as pd
import pytest

from fin_assistant.semantic import DataContractError, FactStore, Period, validate_facts

from .conftest import companies_df, fact


def _store(rows):
    return FactStore(pd.DataFrame(rows), companies_df())


def test_valid_fixture_has_no_problems(facts_df):
    assert validate_facts(facts_df, companies_df()) == []


def test_missing_column_rejected(facts_df):
    with pytest.raises(DataContractError, match="thiếu cột"):
        FactStore(facts_df.drop(columns=["as_of_date"]), companies_df())


def test_unit_must_be_normalised_to_vnd():
    rows = [fact("AAA", "2024Q1", "IS.NET_REVENUE", 1000, unit="tỷ đồng")]
    with pytest.raises(DataContractError, match="đơn vị"):
        _store(rows)


def test_item_type_must_match_catalog():
    rows = [fact("AAA", "2024Q1", "BS.EQUITY_PARENT", 1000, item_type="flow")]
    with pytest.raises(DataContractError, match="item_type"):
        _store(rows)


def test_stock_item_cannot_be_ytd():
    rows = [fact("AAA", "2024Q2", "BS.EQUITY_PARENT", 1000, period_type="YTD")]
    with pytest.raises(DataContractError, match="stock"):
        _store(rows)


def test_duplicate_key_rejected():
    row = fact("AAA", "2024Q1", "IS.NET_REVENUE", 1000)
    with pytest.raises(DataContractError, match="trùng khóa"):
        _store([row, dict(row, value=2.0)])


def test_unknown_ticker_rejected():
    with pytest.raises(DataContractError, match="không có trong bảng công ty"):
        _store([fact("XYZ", "2024Q1", "IS.NET_REVENUE", 1)])


def test_null_value_rejected():
    with pytest.raises(DataContractError, match="rỗng"):
        _store([dict(fact("AAA", "2024Q1", "IS.NET_REVENUE", 1), value=None)])


def test_bad_group_rejected():
    companies = pd.DataFrame([{"ticker": "AAA", "group": "insurance"}])
    with pytest.raises(DataContractError, match="nhóm"):
        FactStore(pd.DataFrame([fact("AAA", "2024Q1", "IS.NET_REVENUE", 1)]), companies)


def test_blank_optional_columns_from_csv_are_handled():
    df = pd.DataFrame([fact("AAA", "2024Q1", "IS.NET_REVENUE", 1000)])
    df["is_restated"] = float("nan")  # ô trống khi đọc CSV
    df["derived_from"] = float("nan")
    store = FactStore(df, companies_df())
    f = store.lookup("AAA", "IS.NET_REVENUE", Period(2024, 1))
    assert f is not None and f.is_restated is False and f.derived_from is None


def test_lookup_respects_as_of_and_picks_latest_version(store):
    p = Period(2023, 3)
    assert store.lookup("EEE", "IS.NET_REVENUE", p, as_of="2023-10-29") is None
    v1 = store.lookup("EEE", "IS.NET_REVENUE", p, as_of="2024-01-01")
    v2 = store.lookup("EEE", "IS.NET_REVENUE", p, as_of="2024-10-30")
    latest = store.lookup("EEE", "IS.NET_REVENUE", p)
    assert v1.value == 800e9 and v1.report_version == 1
    assert v2.value == 900e9 and v2.is_restated
    assert latest.value == 900e9


def test_lookup_is_case_insensitive_on_ticker(store):
    assert store.lookup("aaa", "IS.NET_REVENUE", Period(2024, 3)).value == 1500e9


def test_scope_from_company_table():
    rows = [
        fact("AAA", "2024Q1", "IS.NET_REVENUE", 100, scope="separate"),
        fact("AAA", "2024Q1", "IS.NET_REVENUE", 120, scope="consolidated"),
    ]
    companies = pd.DataFrame([{"ticker": "AAA", "group": "non_financial", "scope": "separate"}])
    store = FactStore(pd.DataFrame(rows), companies)
    assert store.lookup("AAA", "IS.NET_REVENUE", Period(2024, 1)).value == 100e9


def test_latest_period_single_ticker(store):
    assert store.latest_period("AAA", as_of="2024-11-15") == Period(2024, 3)
    assert store.latest_period("AAA", as_of="2025-02-15") == Period(2024, 4)
    assert store.latest_period("AAA", as_of="2024-10-29") == Period(2024, 2)  # Q3 công bố 30/10
    assert store.latest_period("AAA", as_of="2020-01-01") is None
    assert store.latest_period("NEW") is None


def test_is_published_later(store):
    assert store.is_published_later("AAA", Period(2024, 3), "2024-10-15")
    assert not store.is_published_later("AAA", Period(2024, 3), "2024-11-15")
    assert not store.is_published_later("AAA", Period(2024, 3), None)
