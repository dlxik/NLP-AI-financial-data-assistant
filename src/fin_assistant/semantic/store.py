"""Truy xuất ``fact_financials`` theo ngày hỏi (``as_of``) và phiên bản báo cáo.

Đầu vào là bảng long format do TV1 bàn giao (hợp đồng dữ liệu: xem
``docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md``, mục 2). Lớp này chỉ **đọc**:
- chọn đúng phạm vi báo cáo (hợp nhất/riêng) của từng mã;
- chỉ thấy các dòng đã công bố tới ngày hỏi (``as_of_date <= as_of``) — quy tắc T1;
- khi một ô có nhiều phiên bản, lấy phiên bản công bố muộn nhất tới ngày hỏi — quy tắc T2.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

from .catalog import CONSOLIDATED, GROUPS, ITEMS, SCOPES, STOCK
from .periods import Period, to_date

FACT_COLUMNS = (
    "ticker",
    "fiscal_year",
    "fiscal_quarter",
    "period_type",
    "item_code",
    "item_type",
    "value",
    "unit",
    "scope",
    "as_of_date",
    "report_version",
    "source_ref",
)
OPTIONAL_FACT_COLUMNS = ("is_restated", "derived_from")
COMPANY_COLUMNS = ("ticker", "group")
PERIOD_TYPES = frozenset({"Q", "YTD"})
KEY_COLUMNS = ("ticker", "fiscal_year", "fiscal_quarter", "period_type", "item_code", "scope", "report_version")


class DataContractError(ValueError):
    """Dữ liệu bàn giao vi phạm hợp đồng dữ liệu (lỗi phía ETL, cần TV1 sửa)."""


@dataclass(frozen=True)
class Fact:
    ticker: str
    period: Period
    period_type: str
    item_code: str
    item_type: str
    value: float
    unit: str
    scope: str
    as_of_date: date
    report_version: int
    source_ref: str
    is_restated: bool
    derived_from: str | None


def validate_facts(facts: pd.DataFrame, companies: pd.DataFrame) -> list[str]:
    """Kiểm tra hợp đồng dữ liệu; trả danh sách lỗi (rỗng = hợp lệ)."""
    problems: list[str] = []
    missing = [c for c in FACT_COLUMNS if c not in facts.columns]
    if missing:
        return [f"fact_financials thiếu cột: {missing}"]
    missing = [c for c in COMPANY_COLUMNS if c not in companies.columns]
    if missing:
        return [f"bảng công ty thiếu cột: {missing}"]

    nulls = [c for c in FACT_COLUMNS if facts[c].isna().any()]
    if nulls:
        problems.append(f"cột bắt buộc có giá trị rỗng: {nulls} (bỏ dòng thay vì để value rỗng)")

    bad_groups = set(companies["group"]) - GROUPS
    if bad_groups:
        problems.append(f"nhóm doanh nghiệp không hợp lệ: {sorted(bad_groups)}")
    if "scope" in companies.columns:
        bad_scopes = set(companies["scope"].dropna()) - SCOPES
        if bad_scopes:
            problems.append(f"phạm vi báo cáo không hợp lệ trong bảng công ty: {sorted(bad_scopes)}")
    if companies["ticker"].duplicated().any():
        problems.append("bảng công ty có mã trùng")

    unknown = set(facts["ticker"]) - set(companies["ticker"])
    if unknown:
        problems.append(f"mã không có trong bảng công ty: {sorted(unknown)}")
    if not facts["fiscal_quarter"].isin([1, 2, 3, 4]).all():
        problems.append("fiscal_quarter phải thuộc 1..4")
    bad_pt = set(facts["period_type"]) - PERIOD_TYPES
    if bad_pt:
        problems.append(f"period_type không hợp lệ: {sorted(bad_pt)}")
    bad_scope = set(facts["scope"]) - SCOPES
    if bad_scope:
        problems.append(f"scope không hợp lệ: {sorted(bad_scope)}")

    for code, item in ITEMS.items():
        rows = facts[facts["item_code"] == code]
        if rows.empty:
            continue
        if (rows["item_type"] != item.item_type).any():
            problems.append(f"{code}: item_type phải là {item.item_type!r}")
        if (rows["unit"] != item.unit).any():
            problems.append(f"{code}: đơn vị phải là {item.unit!r} (TV1 quy đổi trước khi bàn giao)")
        if item.item_type == STOCK and (rows["period_type"] != "Q").any():
            problems.append(f"{code}: chỉ tiêu cân đối (stock) chỉ có period_type 'Q' (số dư cuối quý)")

    dup = facts.duplicated(subset=list(KEY_COLUMNS), keep=False)
    if dup.any():
        sample = facts.loc[dup, list(KEY_COLUMNS)].head(3).to_dict("records")
        problems.append(f"trùng khóa (ticker, kỳ, item, scope, version), ví dụ: {sample}")
    return problems


class FactStore:
    """Kho số liệu chỉ đọc, đánh chỉ mục sẵn để tra cứu O(1)."""

    def __init__(self, facts: pd.DataFrame, companies: pd.DataFrame) -> None:
        problems = validate_facts(facts, companies)
        if problems:
            raise DataContractError("; ".join(problems))

        self._groups: dict[str, str] = {}
        self._scopes: dict[str, str] = {}
        for rec in companies.to_dict("records"):
            ticker = str(rec["ticker"]).upper()
            self._groups[ticker] = rec["group"]
            scope = rec.get("scope")
            self._scopes[ticker] = scope if isinstance(scope, str) and scope else CONSOLIDATED

        self._index: dict[tuple, list[Fact]] = defaultdict(list)
        # (ticker, scope, period) -> ngày công bố sớm nhất của bất kỳ dòng quý nào
        self._first_published: dict[tuple[str, str, Period], date] = {}

        for rec in facts.to_dict("records"):
            fact = Fact(
                ticker=str(rec["ticker"]).upper(),
                period=Period(int(rec["fiscal_year"]), int(rec["fiscal_quarter"])),
                period_type=rec["period_type"],
                item_code=rec["item_code"],
                item_type=rec["item_type"],
                value=float(rec["value"]),
                unit=rec["unit"],
                scope=rec["scope"],
                as_of_date=to_date(rec["as_of_date"]),  # type: ignore[arg-type]
                report_version=int(rec["report_version"]),
                source_ref=str(rec["source_ref"]),
                is_restated=_as_bool(rec.get("is_restated")),
                derived_from=_none_if_blank(rec.get("derived_from")),
            )
            key = (fact.ticker, fact.item_code, fact.period, fact.period_type, fact.scope)
            self._index[key].append(fact)
            if fact.period_type == "Q":
                pkey = (fact.ticker, fact.scope, fact.period)
                prev = self._first_published.get(pkey)
                if prev is None or fact.as_of_date < prev:
                    self._first_published[pkey] = fact.as_of_date

        for versions in self._index.values():
            versions.sort(key=lambda f: (f.as_of_date, f.report_version))

    # --- thông tin công ty ----------------------------------------------------
    def has_ticker(self, ticker: str) -> bool:
        return ticker.upper() in self._groups

    def group_of(self, ticker: str) -> str | None:
        return self._groups.get(ticker.upper())

    def scope_of(self, ticker: str) -> str:
        return self._scopes.get(ticker.upper(), CONSOLIDATED)

    # --- tra cứu ô số ---------------------------------------------------------
    def lookup(
        self,
        ticker: str,
        item_code: str,
        period: Period,
        *,
        as_of: date | str | None = None,
        period_type: str = "Q",
    ) -> Fact | None:
        """Phiên bản mới nhất của một ô số đã công bố tới ngày ``as_of`` (T1, T2)."""
        ticker = ticker.upper()
        key = (ticker, item_code, period, period_type, self.scope_of(ticker))
        versions = self._index.get(key)
        if not versions:
            return None
        cutoff = to_date(as_of)
        if cutoff is None:
            return versions[-1]
        visible = [f for f in versions if f.as_of_date <= cutoff]
        return visible[-1] if visible else None

    def is_published_later(self, ticker: str, period: Period, as_of: date | str | None) -> bool:
        """Kỳ đã có dữ liệu trong kho nhưng công bố **sau** ngày hỏi (phân biệt với khoảng trống dữ liệu)."""
        cutoff = to_date(as_of)
        if cutoff is None:
            return False
        first = self._first_published.get((ticker.upper(), self.scope_of(ticker), period))
        return first is not None and first > cutoff

    def published_periods(self, ticker: str, as_of: date | str | None = None) -> list[Period]:
        """Các quý mà mã đã công bố BCTC (có ít nhất một dòng) tới ngày hỏi, tăng dần."""
        ticker = ticker.upper()
        scope = self.scope_of(ticker)
        cutoff = to_date(as_of)
        periods = [
            p
            for (t, s, p), first in self._first_published.items()
            if t == ticker and s == scope and (cutoff is None or first <= cutoff)
        ]
        return sorted(periods)

    def latest_period(self, ticker: str, as_of: date | str | None = None) -> Period | None:
        """T4 — kỳ gần nhất của **một mã**: quý mới nhất đã công bố tới ngày hỏi."""
        periods = self.published_periods(ticker, as_of)
        return periods[-1] if periods else None

    def tickers(self, group: str | None = None) -> list[str]:
        return sorted(t for t, g in self._groups.items() if group is None or g == group)


def _as_bool(value: object) -> bool:
    """NaN/None (ô trống trong CSV) → False; tránh bẫy ``bool(float('nan')) is True``."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "x"}
    return bool(value)


def _none_if_blank(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def make_companies(rows: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """Tiện ích: tạo bảng công ty từ danh sách (ticker, group)."""
    return pd.DataFrame([{"ticker": t, "group": g} for t, g in rows])
