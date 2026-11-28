"""Semantic layer v1.0 (TV2) — thư viện chỉ số tài chính có quy tắc số liệu khó & thời gian.

Ví dụ::

    from fin_assistant.semantic import FactStore, get_metric, rank

    store = FactStore(facts_df, companies_df)
    r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="yoy", as_of="2024-11-15")
    top = rank(store, "roe_ttm", store.tickers(), "latest", top_n=5, as_of="2024-11-15")

Đặc tả: ``docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md``; danh mục: ``docs/specs/danh-muc-chi-so-de-xuat.md``.
"""

from .api import UnknownMetricError, get_metric, get_metric_multi, rank, resolve_universe, screen
from .catalog import BANK, ITEMS, METRICS, NON_FINANCIAL, OFFICIAL_METRICS, TransformError, parse_transform
from .fmt import describe, describe_multi, format_value, metric_name
from .periods import LATEST, Period
from .query import Query, QueryError, execute
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
    "OFFICIAL_METRICS",
    "Period",
    "Query",
    "QueryError",
    "RuleConfig",
    "Status",
    "TransformError",
    "UnknownMetricError",
    "WarnCode",
    "describe",
    "describe_multi",
    "execute",
    "format_value",
    "get_metric",
    "get_metric_multi",
    "metric_name",
    "parse_transform",
    "rank",
    "resolve_universe",
    "screen",
    "validate_facts",
]
