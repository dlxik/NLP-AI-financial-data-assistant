"""Xếp hạng (R12), nhóm mã, truy vấn có cấu trúc + bộ thực thi (dùng chung B0 / C)."""

import json

import pytest

from fin_assistant.semantic import (
    MetricResult,
    MultiResult,
    Query,
    QueryError,
    RuleConfig,
    Status,
    WarnCode,
    describe_multi,
    execute,
    rank,
    resolve_universe,
)


# ================================================================ xếp hạng
class TestRank:
    def test_desc_top1(self, store):
        r = rank(store, "roe_ttm", ["AAA", "NHA"], "2024Q3", top_n=1)
        assert r.status is Status.OK
        assert r.tickers == ["NHA"]
        assert r.rows[0].details["rank"] == 1

    def test_asc_all(self, store):
        r = rank(store, "roe_ttm", ["NHA", "AAA", "BBB"], "2024Q1", order="asc")
        # BBB Q1/2024 có ROE âm hợp lệ (VCSH dương) → đứng đầu khi xếp tăng dần
        assert r.tickers[0] == "BBB"

    def test_negative_equity_excluded_and_disclosed(self, store):
        """Mã vốn chủ âm không được lọt vào bảng xếp hạng ROE (R4)."""
        r = rank(store, "roe_ttm", ["AAA", "DDD", "NHA"], "2024Q3")
        assert r.tickers == ["NHA", "AAA"]
        assert [x.ticker for x in r.excluded] == ["DDD"]
        assert WarnCode.EXCLUDED_NOT_MEANINGFUL in r.warning_codes

    def test_missing_ticker_gives_partial_coverage(self, store):
        r = rank(store, "roe_ttm", ["AAA", "EEE"], "2024Q3")
        assert r.status is Status.OK
        assert WarnCode.PARTIAL_COVERAGE in r.warning_codes

    def test_ties_are_stable_by_ticker(self):
        import pandas as pd

        from fin_assistant.semantic import FactStore

        from .conftest import companies_df, fact

        rows = [fact(t, "2024Q1", "IS.NET_REVENUE", 100) for t in ("CCC", "AAA", "BBB")]
        s = FactStore(pd.DataFrame(rows), companies_df())
        assert rank(s, "net_revenue", ["CCC", "AAA", "BBB"], "2024Q1").tickers == ["AAA", "BBB", "CCC"]

    def test_rank_uses_common_latest_period(self, store):
        r = rank(store, "roe_ttm", ["AAA", "NHA"], "latest", as_of="2025-02-15")
        assert {x.period for x in r.rows} == {"Q3/2024"}
        assert WarnCode.NEWER_PERIOD_AVAILABLE in r.warning_codes

    def test_rank_on_growth(self, store):
        """Cặp đối lập 'top tuyệt đối vs tốc độ tăng'."""
        level = rank(store, "net_revenue", ["AAA", "CCC"], "2024Q4")
        growth = rank(store, "net_revenue", ["AAA", "CCC"], "2024Q4", transform="yoy")
        assert level.tickers[0] == "AAA"   # 1.430 > 320 tỷ
        assert growth.tickers[0] == "AAA"  # 10,0% > 6,7%
        assert level.rows[0].value != growth.rows[0].value

    def test_clarification_dominates(self, store):
        assert rank(store, "net_revenue", ["AAA", "NHA"], "2024Q3").status is Status.NEEDS_CLARIFICATION

    def test_nothing_rankable(self, store):
        r = rank(store, "roe_ttm", ["DDD"], "2024Q3")
        assert r.status is Status.NOT_MEANINGFUL
        assert rank(store, "roe_ttm", [], "2024Q3").status is Status.MISSING_DATA

    @pytest.mark.parametrize("kwargs", [{"order": "up"}, {"top_n": 0}])
    def test_invalid_args(self, store, kwargs):
        with pytest.raises(ValueError):
            rank(store, "roe_ttm", ["AAA"], "2024Q3", **kwargs)

    def test_describe_multi_shows_rank_and_exclusions(self, store):
        text = describe_multi(rank(store, "roe_ttm", ["AAA", "DDD", "NHA"], "2024Q3"))
        lines = text.splitlines()
        assert lines[0].startswith("1. ") and "NHA" in lines[0]
        assert any(line.startswith("× ") and "DDD" in line for line in lines)

    def test_describe_multi_empty_valid(self, store):
        from fin_assistant.semantic import screen

        text = describe_multi(screen(store, "roe_ttm", ["AAA"], ">", 0.9, "2024Q3"))
        assert text.startswith("Không có mã nào thỏa điều kiện")


def test_resolve_universe(store):
    assert resolve_universe(store, "bank") == ["NHA"]
    assert "NHA" not in resolve_universe(store, "non_financial")
    assert resolve_universe(store, "VN30") == store.tickers()
    with pytest.raises(ValueError):
        resolve_universe(store, "insurance")


# ================================================================ Query
class TestQuery:
    def test_lookup_single_returns_metric_result(self, store):
        q = Query(op="lookup", metric="net_revenue", tickers=("AAA",), period="2024Q3", transform="yoy")
        r = execute(store, q)
        assert isinstance(r, MetricResult) and r.value == pytest.approx(0.25)

    def test_lookup_universe_returns_multi(self, store):
        q = Query(op="lookup", metric="roe_ttm", universe="bank", period="2024Q3")
        r = execute(store, q)
        assert isinstance(r, MultiResult) and r.tickers == ["NHA"]

    def test_rank_and_screen(self, store):
        top = execute(store, Query(op="rank", metric="roe_ttm", tickers=("AAA", "NHA"), period="2024Q3", top_n=1))
        assert top.tickers == ["NHA"]
        flt = execute(store, Query(op="screen", metric="roe_ttm", tickers=("AAA", "NHA"), period="2024Q3",
                                   cmp=">", threshold=0.5))
        assert flt.status is Status.EMPTY_VALID

    def test_config_is_forwarded(self, store):
        q = Query(op="lookup", metric="roe_ttm", tickers=("EEE",), period="2024Q3")
        assert execute(store, q).status is Status.MISSING_DATA
        assert execute(store, q, RuleConfig(allow_ending_equity_fallback=True)).status is Status.OK

    def test_json_roundtrip(self):
        q = Query(op="screen", metric="gross_margin", universe="non_financial", period="2024Q3",
                  transform="yoy_pp", cmp=">=", threshold=0.01, as_of="2024-11-15", assumptions=("x",))
        again = Query.from_json(q.to_json())
        assert again == q and again.assumptions == ("x",)

    def test_from_dict_normalises_tickers(self):
        q = Query.from_dict({"op": "lookup", "metric": "npat", "tickers": ["aaa"], "period": "2024Q3"})
        assert q.tickers == ("AAA",)

    @pytest.mark.parametrize(
        "payload, match",
        [
            ({"op": "lookup"}, "phải có"),
            ({"op": "delete", "metric": "npat", "tickers": ["AAA"]}, "op"),
            ({"op": "lookup", "metric": "ebitda", "tickers": ["AAA"]}, "danh mục"),
            ({"op": "lookup", "metric": "roe_ttm", "tickers": ["AAA"], "transform": "yoy"}, "_pp"),
            ({"op": "lookup", "metric": "npat", "tickers": ["AAA"], "period": "2024Q9"}, "kỳ"),
            ({"op": "lookup", "metric": "npat"}, "tickers"),
            ({"op": "lookup", "metric": "npat", "tickers": ["AAA"], "universe": "bank"}, "tickers"),
            ({"op": "lookup", "metric": "npat", "universe": "banks"}, "universe"),
            ({"op": "rank", "metric": "npat", "universe": "all", "order": "up"}, "order"),
            ({"op": "rank", "metric": "npat", "universe": "all", "top_n": 0}, "top_n"),
            ({"op": "screen", "metric": "npat", "universe": "all", "cmp": "==", "threshold": 1}, "screen"),
            ({"op": "screen", "metric": "npat", "universe": "all", "cmp": ">", "threshold": "abc"}, "số"),
            ({"op": "lookup", "metric": "npat", "tickers": ["AAA"], "sql": "DROP TABLE"}, "không hợp lệ"),
        ],
    )
    def test_invalid_queries(self, payload, match):
        with pytest.raises(QueryError, match=match):
            Query.from_dict(payload)

    @pytest.mark.parametrize("text", ["{not json", "[1, 2]"])
    def test_invalid_json(self, text):
        with pytest.raises(QueryError):
            Query.from_json(text)

    def test_json_schema_lists_catalog(self):
        schema = Query.json_schema()
        assert set(schema["properties"]["metric"]["enum"]) >= {"roe_ttm", "net_revenue"}
        assert schema["additionalProperties"] is False
        json.dumps(schema)

    def test_execute_validates(self, store):
        with pytest.raises(QueryError):
            execute(store, Query(op="lookup", metric="npat"))
