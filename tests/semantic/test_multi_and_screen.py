"""Kỳ gần nhất đa mã (T5) và quy tắc 0 dòng (R8)."""

import pytest

from fin_assistant.semantic import RuleConfig, Status, WarnCode, get_metric_multi, screen


class TestLatestMulti:
    def test_common_policy_aligns_all_tickers(self, store):
        # 15/02/2025: AAA đã có Q4/2024, NHA mới có Q3/2024
        m = get_metric_multi(store, "roe_ttm", ["AAA", "NHA"], "latest", as_of="2025-02-15")
        assert m.period_policy == "common"
        assert {r.period for r in m.rows} == {"Q3/2024"}
        assert m.status is Status.OK
        w = next(w for w in m.warnings if w.code is WarnCode.NEWER_PERIOD_AVAILABLE)
        assert w.ticker == "AAA" and w.period == "Q4/2024"

    def test_per_ticker_policy_flags_mixed_periods(self, store):
        cfg = RuleConfig(latest_policy_multi="per_ticker")
        m = get_metric_multi(store, "roe_ttm", ["AAA", "NHA"], "latest", as_of="2025-02-15", config=cfg)
        assert [r.period for r in m.rows] == ["Q4/2024", "Q3/2024"]
        assert WarnCode.MIXED_PERIODS in m.warning_codes

    def test_explicit_period_has_no_period_warning(self, store):
        m = get_metric_multi(store, "roe_ttm", ["AAA", "NHA"], "2024Q3")
        assert m.period_policy == "explicit"
        assert not ({WarnCode.NEWER_PERIOD_AVAILABLE, WarnCode.MIXED_PERIODS} & m.warning_codes)

    def test_ticker_without_data_is_reported_not_dropped(self, store):
        m = get_metric_multi(store, "net_revenue", ["AAA", "NEW"], "latest", as_of="2024-11-15")
        assert m.tickers == ["AAA", "NEW"]
        assert m.rows[1].status is Status.MISSING_DATA
        assert m.status is Status.OK
        assert WarnCode.PARTIAL_COVERAGE in m.warning_codes

    def test_bank_in_revenue_comparison_triggers_clarification(self, store):
        m = get_metric_multi(store, "net_revenue", ["AAA", "NHA"], "2024Q3")
        assert m.status is Status.NEEDS_CLARIFICATION
        assert m.rows[0].status is Status.OK  # phần phi tài chính vẫn tính sẵn

    def test_duplicates_removed_and_case_normalised(self, store):
        m = get_metric_multi(store, "net_revenue", ["aaa", "AAA"], "2024Q3")
        assert m.tickers == ["AAA"]

    def test_all_failed_status_priority(self, store):
        m = get_metric_multi(store, "roe_ttm", ["DDD", "CCC"], "2024Q3")
        assert m.status is Status.MISSING_DATA  # thiếu dữ liệu ưu tiên hơn "không xác định"


class TestScreenZeroRows:
    def test_empty_valid_when_everyone_evaluated(self, store):
        s = screen(store, "roe_ttm", ["AAA", "NHA"], ">", 0.5, "2024Q3")
        assert s.status is Status.EMPTY_VALID
        assert s.rows == () and s.excluded == ()
        assert s.status.is_answer

    def test_matches(self, store):
        s = screen(store, "roe_ttm", ["AAA", "NHA"], ">", 0.12, "2024Q3")
        assert s.status is Status.OK
        assert s.tickers == ["NHA"]

    def test_zero_rows_with_missing_data_is_not_empty_valid(self, store):
        """Cặp đối lập 'rỗng hợp lệ' vs 'thiếu mẫu số'."""
        s = screen(store, "roe_ttm", ["AAA", "EEE"], ">", 0.5, "2024Q3")
        assert s.status is Status.MISSING_DATA
        assert [r.ticker for r in s.excluded] == ["EEE"]
        assert WarnCode.PARTIAL_COVERAGE in s.warning_codes

    def test_not_meaningful_rows_excluded_but_disclosed(self, store):
        s = screen(store, "roe_ttm", ["AAA", "DDD"], ">", 0.5, "2024Q3")
        assert s.status is Status.EMPTY_VALID
        assert [r.ticker for r in s.excluded] == ["DDD"]
        assert WarnCode.EXCLUDED_NOT_MEANINGFUL in s.warning_codes

    def test_negative_equity_never_passes_a_positive_filter(self, store):
        s = screen(store, "roe_ttm", ["DDD"], ">", 0.0, "2024Q3")
        assert s.tickers == []

    def test_clarification_dominates(self, store):
        s = screen(store, "net_revenue", ["AAA", "NHA"], ">", 0, "2024Q3")
        assert s.status is Status.NEEDS_CLARIFICATION

    def test_matches_with_partial_coverage(self, store):
        s = screen(store, "roe_ttm", ["AAA", "NHA", "EEE"], ">", 0.05, "2024Q3")
        assert s.status is Status.OK
        assert s.tickers == ["AAA", "NHA"]
        assert WarnCode.PARTIAL_COVERAGE in s.warning_codes

    def test_rejects_unknown_operator(self, store):
        with pytest.raises(ValueError):
            screen(store, "roe_ttm", ["AAA"], "!=", 0.1, "2024Q3")

    def test_empty_ticker_list(self, store):
        s = screen(store, "roe_ttm", [], ">", 0.1, "2024Q3")
        assert s.status is Status.MISSING_DATA
