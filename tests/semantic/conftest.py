"""Dữ liệu giả lập cho unit test semantic layer.

Toàn bộ mã cổ phiếu là **giả** (AAA, BBB, ...) để không nhầm với số liệu thật hay Gold của TV4.
Đơn vị nhập liệu: tỷ đồng (nhân ``B`` = 1e9 khi dựng fact). Ngày công bố mặc định = cuối quý + 30 ngày.

| Mã  | Nhóm | Mục đích kiểm thử |
|-----|------|-------------------|
| AAA | phi tài chính | ca chuẩn: doanh thu, YoY, ROE TTM (VCSH mẹ = 400 − 429), kỳ gần nhất |
| BBB | phi tài chính | VCSH cổ đông mẹ chuyển âm ở cuối kỳ |
| DDD | phi tài chính | VCSH âm cả 2 đầu + lỗ → tỷ số dương nhưng phải "không xác định" |
| CCC | phi tài chính | kỳ gốc = 0 / gần 0 / rất nhỏ; thiếu 1 quý LNST |
| EEE | phi tài chính | điều chỉnh hồi tố, Q4 suy ra từ FY − 9T, thiếu VCSH đầu kỳ |
| NHA | ngân hàng | ROE TTM ngân hàng, NII/TOI, ca "doanh thu thuần" ngân hàng |
| NEW | phi tài chính | có trong danh mục nhưng chưa công bố BCTC nào |
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from fin_assistant.semantic import ITEMS, FactStore, Period

B = 1e9  # 1 tỷ đồng
LAG_DAYS = 30

COMPANIES = [
    ("AAA", "non_financial"),
    ("BBB", "non_financial"),
    ("CCC", "non_financial"),
    ("DDD", "non_financial"),
    ("EEE", "non_financial"),
    ("NHA", "bank"),
    ("NEW", "non_financial"),
]

QUARTERS_23_24 = [Period(2023, q) for q in range(1, 5)] + [Period(2024, q) for q in range(1, 5)]


def fact(
    ticker: str,
    period: str | Period,
    item: str,
    value_bn: float,
    *,
    as_of: str | None = None,
    version: int = 1,
    period_type: str = "Q",
    scope: str = "consolidated",
    restated: bool = False,
    derived_from: str | None = None,
    unit: str | None = None,
    item_type: str | None = None,
) -> dict:
    p = Period.parse(period)
    return {
        "ticker": ticker,
        "fiscal_year": p.year,
        "fiscal_quarter": p.quarter,
        "period_type": period_type,
        "item_code": item,
        "item_type": item_type or ITEMS[item].item_type,
        "value": value_bn * B,
        "unit": unit or ITEMS[item].unit,
        "scope": scope,
        "as_of_date": as_of or (p.end_date() + timedelta(days=LAG_DAYS)).isoformat(),
        "report_version": version,
        "source_ref": f"{ticker}/{p}/{item}/v{version}",
        "is_restated": restated,
        "derived_from": derived_from,
    }


def series(ticker: str, item: str, values_bn: list[float], periods=QUARTERS_23_24) -> list[dict]:
    return [fact(ticker, p, item, v) for p, v in zip(periods, values_bn) if v is not None]


def build_rows() -> list[dict]:
    rows: list[dict] = []
    # --- AAA: ca chuẩn -------------------------------------------------------
    rows += series("AAA", "IS.NET_REVENUE", [1000, 1100, 1200, 1300, 1100, 1210, 1500, 1430])
    rows += series("AAA", "IS.NPAT_PARENT", [100, 110, 120, 130, 120, 130, 150, 140])
    parent_eq = [5000, 5100, 5200, 5300, 5000, 5500, 5600, 5700]
    rows += series("AAA", "BS.EQUITY_TOTAL", [v + 200 for v in parent_eq])
    rows += series("AAA", "BS.NCI", [200] * 8)

    # --- BBB: VCSH mẹ chuyển âm ở cuối kỳ -----------------------------------
    rows += series("BBB", "IS.NPAT_PARENT", [-50] * 8)
    rows += series("BBB", "BS.EQUITY_PARENT", [400, 350, 300, 250, 150, 50, -100, -150])

    # --- DDD: VCSH âm cả hai đầu, lỗ → tỷ số dương giả --------------------------
    rows += series("DDD", "IS.NPAT_PARENT", [-50] * 8)
    rows += series("DDD", "BS.EQUITY_PARENT", [-400, -450, -500, -550, -600, -650, -700, -750])

    # --- CCC: mẫu số kỳ gốc khó; thiếu LNST Q1/2024 ---------------------------
    #            23Q1  23Q2  23Q3  23Q4  24Q1  24Q2  24Q3  24Q4
    rows += series("CCC", "IS.NET_REVENUE", [0, 20, 0.5, 300, 100, 500, 400, 320])
    rows += series("CCC", "IS.NPAT_PARENT", [10, 10, 10, 10, None, 10, 10, 10])
    rows += series("CCC", "BS.EQUITY_PARENT", [1000] * 8)

    # --- EEE: hồi tố, Q4 suy ra, thiếu VCSH đầu kỳ ---------------------------
    rows.append(fact("EEE", "2023Q3", "IS.NET_REVENUE", 800, as_of="2023-10-30", version=1))
    rows.append(fact("EEE", "2023Q3", "IS.NET_REVENUE", 900, as_of="2024-10-30", version=2, restated=True))
    rows.append(fact("EEE", "2023Q4", "IS.NET_REVENUE", 950, derived_from="FY2023 − 9T2023 (YTD→Q)"))
    rows.append(fact("EEE", "2024Q3", "IS.NET_REVENUE", 990, as_of="2024-10-30"))
    rows += series("EEE", "IS.NPAT_PARENT", [None, None, None, 50, 60, 70, 80, None])
    rows.append(fact("EEE", "2024Q3", "BS.EQUITY_PARENT", 2000, as_of="2024-10-30"))

    # --- NHA: ngân hàng -------------------------------------------------------
    bank_q = [Period(2023, 3), Period(2023, 4), Period(2024, 1), Period(2024, 2), Period(2024, 3)]
    rows += series("NHA", "IS.BANK_NII", [4000, 4200, 4500, 4800, 5000], bank_q)
    rows += series("NHA", "IS.BANK_TOI", [5200, 5400, 5800, 6200, 6500], bank_q)
    rows += series("NHA", "IS.BANK_INTEREST_INCOME", [7500, 7800, 8200, 8600, 9000], bank_q)
    rows += series("NHA", "IS.NPAT_PARENT", [1900, 2000, 2100, 2200, 2300], bank_q)
    rows += series("NHA", "BS.EQUITY_PARENT", [50000, 52000, 54000, 57000, 60000], bank_q)
    return rows


def companies_df() -> pd.DataFrame:
    return pd.DataFrame([{"ticker": t, "group": g} for t, g in COMPANIES])


@pytest.fixture(scope="session")
def facts_df() -> pd.DataFrame:
    return pd.DataFrame(build_rows())


@pytest.fixture(scope="session")
def store(facts_df: pd.DataFrame) -> FactStore:
    return FactStore(facts_df, companies_df())
