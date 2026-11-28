"""Truy vấn có cấu trúc + bộ thực thi giới hạn phép toán.

``Query`` là "ngôn ngữ truy vấn" dùng chung:
- **B0** (bộ phân tích quy tắc) sinh ``Query`` từ câu tiếng Việt;
- **C** (GĐ3) để LLM sinh ``Query`` dạng JSON theo :meth:`Query.json_schema`.

Bộ thực thi chỉ gọi các hàm của semantic layer (``get_metric``, ``get_metric_multi``, ``rank``,
``screen``) — không có biểu thức tùy ý, không có code. Câu hỏi nào không biểu đạt được bằng
``Query`` phải được ghi nhận riêng (Đề cương mục 6.2), không ép vào truy vấn gần đúng.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from .api import UNIVERSES, UnknownMetricError, get_metric, get_metric_multi, rank, resolve_universe, screen
from .catalog import METRICS, TransformError, check_transform, parse_transform
from .periods import LATEST, Period
from .result import MetricResult, MultiResult
from .rules import DEFAULT_RULES, SCREEN_OPS, RuleConfig
from .store import FactStore

OPS = ("lookup", "rank", "screen")


class QueryError(ValueError):
    """Truy vấn không hợp lệ / không thực thi được."""


@dataclass(frozen=True)
class Query:
    op: str
    metric: str
    tickers: tuple[str, ...] = ()
    universe: str | None = None
    period: str = LATEST
    transform: str | None = None
    order: str = "desc"
    top_n: int | None = None
    cmp: str | None = None
    threshold: float | None = None
    as_of: str | None = None
    assumptions: tuple[str, ...] = field(default=(), compare=False)

    # --- tuần tự hóa ----------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tickers"] = list(self.tickers)
        d["assumptions"] = list(self.assumptions)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Query":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise QueryError(f"trường không hợp lệ trong truy vấn: {sorted(unknown)}")
        if "op" not in data or "metric" not in data:
            raise QueryError("truy vấn phải có 'op' và 'metric'")
        data = dict(data)
        data["tickers"] = tuple(str(t).upper() for t in data.get("tickers") or ())
        data["assumptions"] = tuple(data.get("assumptions") or ())
        q = cls(**data)
        q.validate()
        return q

    @classmethod
    def from_json(cls, text: str) -> "Query":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise QueryError(f"JSON không hợp lệ: {exc}") from None
        if not isinstance(data, dict):
            raise QueryError("truy vấn JSON phải là object")
        return cls.from_dict(data)

    # --- kiểm tra -------------------------------------------------------------
    def validate(self) -> None:
        if self.op not in OPS:
            raise QueryError(f"op không hợp lệ: {self.op!r}; chỉ nhận {OPS}")
        if self.metric not in METRICS:
            raise QueryError(f"chỉ số không có trong danh mục: {self.metric!r}")
        try:
            check_transform(METRICS[self.metric], parse_transform(self.transform))
        except TransformError as exc:
            raise QueryError(str(exc)) from None
        if self.period != LATEST:
            try:
                Period.parse(self.period)
            except ValueError as exc:
                raise QueryError(str(exc)) from None
        if bool(self.tickers) == bool(self.universe):
            raise QueryError("cần đúng một trong hai: 'tickers' hoặc 'universe'")
        if self.universe is not None and self.universe not in UNIVERSES:
            raise QueryError(f"universe không hợp lệ: {self.universe!r}; chỉ nhận {UNIVERSES}")
        if self.op == "rank":
            if self.order not in ("desc", "asc"):
                raise QueryError("order phải là 'desc' hoặc 'asc'")
            if self.top_n is not None and (not isinstance(self.top_n, int) or self.top_n < 1):
                raise QueryError("top_n phải là số nguyên ≥ 1")
        if self.op == "screen":
            if self.cmp not in SCREEN_OPS or self.threshold is None:
                raise QueryError(f"screen cần 'cmp' thuộc {sorted(SCREEN_OPS)} và 'threshold'")
            try:
                float(self.threshold)
            except (TypeError, ValueError):
                raise QueryError("threshold phải là số") from None

    @staticmethod
    def json_schema() -> dict[str, Any]:
        """JSON Schema cho phương pháp C (LLM sinh truy vấn)."""
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["op", "metric"],
            "properties": {
                "op": {"enum": list(OPS)},
                "metric": {"enum": sorted(METRICS)},
                "tickers": {"type": "array", "items": {"type": "string"}},
                "universe": {"enum": list(UNIVERSES)},
                "period": {"type": "string", "description": "'latest' hoặc 'YYYYQn'"},
                "transform": {"type": ["string", "null"],
                              "description": "[ytd|ttm][_][yoy|qoq][_pp], vd 'yoy', 'ytd', 'ttm_yoy', 'yoy_pp'"},
                "order": {"enum": ["desc", "asc"]},
                "top_n": {"type": ["integer", "null"], "minimum": 1},
                "cmp": {"enum": sorted(SCREEN_OPS)},
                "threshold": {"type": ["number", "null"],
                              "description": "tỷ lệ dạng phân số (0.15 = 15%); tiền tệ bằng đồng"},
                "as_of": {"type": ["string", "null"], "description": "question_date YYYY-MM-DD"},
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
        }


def execute(store: FactStore, query: Query, config: RuleConfig | None = None) -> MetricResult | MultiResult:
    """Thực thi truy vấn. Lỗi truy vấn → :class:`QueryError` (người gọi ghi nhận là 'không biểu đạt được')."""
    query.validate()
    config = config or DEFAULT_RULES
    tickers = list(query.tickers) if query.tickers else resolve_universe(store, query.universe or "all")
    kwargs = dict(transform=query.transform, as_of=query.as_of, config=config)
    try:
        if query.op == "lookup":
            if len(tickers) == 1 and not query.universe:
                return get_metric(store, query.metric, tickers[0], query.period, **kwargs)
            return get_metric_multi(store, query.metric, tickers, query.period, **kwargs)
        if query.op == "rank":
            return rank(store, query.metric, tickers, query.period, order=query.order,
                        top_n=query.top_n, **kwargs)
        assert query.cmp is not None and query.threshold is not None
        return screen(store, query.metric, tickers, query.cmp, float(query.threshold), query.period, **kwargs)
    except (UnknownMetricError, TransformError) as exc:  # pragma: no cover - đã chặn ở validate()
        raise QueryError(str(exc)) from None
