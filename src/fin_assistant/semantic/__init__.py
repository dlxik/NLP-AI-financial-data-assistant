"""Semantic layer (TV2) — thư viện chỉ số tài chính có quy tắc số liệu khó & thời gian.

Ví dụ::

    from fin_assistant.semantic import FactStore, get_metric

    store = FactStore(facts_df, companies_df)
    r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="yoy", as_of="2024-11-15")
    r.status, r.value, r.warnings

Đặc tả: ``docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md``.
"""

from .api import UnknownMetricError, get_metric, get_metric_multi, screen
from .catalog import BANK, ITEMS, METRICS, NON_FINANCIAL
from .fmt import describe, format_value
from .periods import LATEST, Period
from .result import InputRef, MetricResult, MetricWarning, MultiResult, Status, WarnCode
from .rules import DEFAULT_RULES, RuleConfig
from .store import DataContractError, FactStore, validate_facts

__all__ = [
    "BANK",
    "DEFAULT_RULES",
    "DataContractError",
    "FactStore",
    "ITEMS",
    "InputRef",
    "LATEST",
    "METRICS",
    "MetricResult",
    "MetricWarning",
    "MultiResult",
    "NON_FINANCIAL",
    "Period",
    "RuleConfig",
    "Status",
    "UnknownMetricError",
    "WarnCode",
    "describe",
    "format_value",
    "get_metric",
    "get_metric_multi",
    "screen",
    "validate_facts",
]
