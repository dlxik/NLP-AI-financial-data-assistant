"""Kiểm thử hàm thuần: kỳ báo cáo (4.4) và quy tắc mẫu số (4.3)."""

from datetime import date, datetime

import pytest

from fin_assistant.semantic import Period, RuleConfig, Status, WarnCode
from fin_assistant.semantic.periods import to_date
from fin_assistant.semantic.rules import check_denominator, compare, growth_rate, safe_ratio

CFG = RuleConfig()


# ---------------------------------------------------------------- Period
@pytest.mark.parametrize(
    "text, expected",
    [
        ("2024Q3", Period(2024, 3)),
        ("2024-Q3", Period(2024, 3)),
        ("2024 q1", Period(2024, 1)),
        ("Q3/2024", Period(2024, 3)),
        ("q4-2023", Period(2023, 4)),
        ((2022, 2), Period(2022, 2)),
    ],
)
def test_parse_period(text, expected):
    assert Period.parse(text) == expected


@pytest.mark.parametrize("bad", ["2024Q5", "Q0/2024", "2024", "quý 3 năm 2024", ""])
def test_parse_period_rejects(bad):
    with pytest.raises(ValueError):
        Period.parse(bad)


def test_period_validation():
    with pytest.raises(ValueError):
        Period(2024, 0)
    with pytest.raises(TypeError):
        Period(2024, "3")  # type: ignore[arg-type]


def test_shift_crosses_year_boundary():
    assert Period(2024, 1).shift(-1) == Period(2023, 4)
    assert Period(2023, 4).shift(1) == Period(2024, 1)
    assert Period(2024, 3).same_quarter_last_year() == Period(2023, 3)


def test_ttm_window_is_four_consecutive_quarters_ending_at_period():
    assert Period(2024, 2).ttm_window() == (
        Period(2023, 3), Period(2023, 4), Period(2024, 1), Period(2024, 2),
    )


def test_end_date_and_label():
    assert Period(2024, 1).end_date() == date(2024, 3, 31)
    assert Period(2023, 2).end_date() == date(2023, 6, 30)
    assert Period(2024, 4).end_date() == date(2024, 12, 31)
    assert Period(2024, 3).label() == "Q3/2024"
    assert str(Period(2024, 3)) == "2024Q3"


def test_ordering():
    assert Period(2023, 4) < Period(2024, 1) < Period(2024, 2)
    assert min(Period(2024, 3), Period(2024, 1)) == Period(2024, 1)


def test_to_date():
    assert to_date("2024-10-30") == date(2024, 10, 30)
    assert to_date(datetime(2024, 10, 30, 15, 0)) == date(2024, 10, 30)
    assert to_date(date(2024, 1, 1)) == date(2024, 1, 1)
    assert to_date(None) is None


# ---------------------------------------------------------------- rules
def test_growth_normal():
    out = growth_rate(1500 * 1e9, 1200 * 1e9, CFG)
    assert out.status is Status.OK
    assert out.value == pytest.approx(0.25)
    assert out.code is None


def test_growth_negative_change_is_valid():
    out = growth_rate(900 * 1e9, 1200 * 1e9, CFG)
    assert out.status is Status.OK and out.value == pytest.approx(-0.25)


@pytest.mark.parametrize("base", [0.0, -100 * 1e9])
def test_growth_non_positive_base_is_not_meaningful(base):
    out = growth_rate(100 * 1e9, base, CFG)
    assert out.status is Status.NOT_MEANINGFUL
    assert out.value is None
    assert out.code is WarnCode.NON_POSITIVE_BASE


def test_growth_near_zero_base_is_not_meaningful():
    out = growth_rate(400 * 1e9, 0.5 * 1e9, CFG)
    assert out.status is Status.NOT_MEANINGFUL
    assert out.code is WarnCode.DENOMINATOR_NEAR_ZERO


def test_growth_threshold_is_configurable():
    loose = RuleConfig(near_zero_abs_vnd=1e8)
    out = growth_rate(400 * 1e9, 0.5 * 1e9, loose)
    assert out.status is Status.OK
    assert out.code is WarnCode.EXTREME_VALUE  # 79.900% > 1.000%


def test_growth_extreme_value_still_answers_with_warning():
    out = growth_rate(500 * 1e9, 20 * 1e9, CFG)
    assert out.status is Status.OK
    assert out.value == pytest.approx(24.0)
    assert out.code is WarnCode.EXTREME_VALUE


def test_growth_at_exact_extreme_threshold_has_no_warning():
    out = growth_rate(11 * 1e9, 1 * 1e9 + 0, RuleConfig(near_zero_abs_vnd=0))
    assert out.value == pytest.approx(10.0)
    assert out.code is None


def test_safe_ratio_custom_non_positive_code():
    out = safe_ratio(100.0, -5 * 1e9, CFG, non_positive_code=WarnCode.NEGATIVE_EQUITY)
    assert out.status is Status.NOT_MEANINGFUL
    assert out.code is WarnCode.NEGATIVE_EQUITY


def test_check_denominator():
    assert check_denominator(5 * 1e9, CFG) is None
    assert check_denominator(1e9, CFG) is None  # đúng bằng ngưỡng → hợp lệ
    assert check_denominator(1e9 - 1, CFG) is WarnCode.DENOMINATOR_NEAR_ZERO
    assert check_denominator(0, CFG) is WarnCode.NON_POSITIVE_BASE


@pytest.mark.parametrize(
    "kwargs",
    [
        {"near_zero_abs_vnd": -1},
        {"extreme_ratio": 0},
        {"equity_avg_method": "three_point"},
        {"latest_policy_multi": "any"},
    ],
)
def test_rule_config_validation(kwargs):
    with pytest.raises(ValueError):
        RuleConfig(**kwargs)


def test_compare_only_whitelisted_ops():
    assert compare(0.2, ">", 0.15)
    assert compare(0.15, ">=", 0.15)
    assert not compare(0.2, "<", 0.15)
    with pytest.raises(ValueError):
        compare(0.2, "==", 0.2)
    with pytest.raises(ValueError):
        compare(0.2, "__import__('os')", 0.2)
