"""Schema definition and validation for `fact_financials` (long format)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from typing import Iterable

import pandas as pd

VALID_ENTITY_GROUPS = frozenset({"non_financial", "bank"})
VALID_STATEMENT_TYPES = frozenset({"IS", "BS", "CF"})
VALID_ITEM_TYPES = frozenset({"flow", "stock"})
VALID_PERIOD_TYPES = frozenset({"Q", "YTD", "FY"})
VALID_SCOPES = frozenset({"consolidated", "parent"})
VALID_REPORT_VERSIONS = frozenset({"original", "reviewed", "audited", "restated"})

FACT_FINANCIALS_COLUMNS: tuple[str, ...] = (
    "fact_id",
    "ticker",
    "entity_group",
    "statement_type",
    "item_code",
    "item_name_vi",
    "item_type",
    "fiscal_year",
    "fiscal_quarter",
    "period_type",
    "period_start",
    "period_end",
    "value",
    "unit",
    "consolidation_scope",
    "as_of_date",
    "report_version",
    "is_restated",
    "source_report_id",
    "source_ref",
    "derived_from",
    "ingested_at",
)


@dataclass(frozen=True)
class PilotItemSpec:
    """Metadata specification for a canonical financial statement item."""

    entity_group: str
    item_code: str
    statement_type: str
    item_type: str
    item_name_vi: str
    accounting_code: str


# Note: `bank` deliberately excludes `net_revenue` so downstream queries
# cannot silently alias `net_interest_income` to `net_revenue`.
PILOT_ITEM_CATALOG: dict[tuple[str, str], PilotItemSpec] = {
    (spec.entity_group, spec.item_code): spec
    for spec in (
        PilotItemSpec(
            entity_group="non_financial",
            item_code="net_revenue",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Doanh thu thuần về bán hàng và cung cấp dịch vụ",
            accounting_code="TT200_IS_10",
        ),
        PilotItemSpec(
            entity_group="non_financial",
            item_code="net_income_parent",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Lợi nhuận sau thuế của cổ đông công ty mẹ",
            accounting_code="TT200_IS_61",
        ),
        PilotItemSpec(
            entity_group="non_financial",
            item_code="net_income_total",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Lợi nhuận sau thuế thu nhập doanh nghiệp",
            accounting_code="TT200_IS_60",
        ),
        PilotItemSpec(
            entity_group="non_financial",
            item_code="equity_total",
            statement_type="BS",
            item_type="stock",
            item_name_vi="Vốn chủ sở hữu",
            accounting_code="TT200_BS_400",
        ),
        PilotItemSpec(
            entity_group="non_financial",
            item_code="equity_parent",
            statement_type="BS",
            item_type="stock",
            item_name_vi="Vốn chủ sở hữu thuộc cổ đông công ty mẹ",
            accounting_code="TT200_BS_410_PARENT",
        ),
        PilotItemSpec(
            entity_group="bank",
            item_code="net_interest_income",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Thu nhập lãi thuần",
            accounting_code="TT49_IS_I",
        ),
        PilotItemSpec(
            entity_group="bank",
            item_code="total_operating_income",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Tổng thu nhập hoạt động",
            accounting_code="TT49_IS_TOI",
        ),
        PilotItemSpec(
            entity_group="bank",
            item_code="net_income_parent",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Lợi nhuận sau thuế của cổ đông của Ngân hàng",
            accounting_code="TT49_IS_PAT_PARENT",
        ),
        PilotItemSpec(
            entity_group="bank",
            item_code="net_income_total",
            statement_type="IS",
            item_type="flow",
            item_name_vi="Lợi nhuận sau thuế",
            accounting_code="TT49_IS_PAT",
        ),
        PilotItemSpec(
            entity_group="bank",
            item_code="equity_total",
            statement_type="BS",
            item_type="stock",
            item_name_vi="Vốn chủ sở hữu",
            accounting_code="TT49_BS_EQUITY",
        ),
    )
}


def build_fact_id(
    ticker: str,
    statement_type: str,
    item_code: str,
    fiscal_year: int,
    fiscal_quarter: int,
    period_type: str,
    consolidation_scope: str,
    report_version: str,
) -> str:
    """Create a deterministic 16-char hex ID for a fact row."""
    raw = "|".join(
        [
            ticker.upper(),
            statement_type,
            item_code,
            str(fiscal_year),
            str(fiscal_quarter),
            period_type,
            consolidation_scope,
            report_version,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class FactFinancialRecord:
    """Single normalized observation in `fact_financials`."""

    ticker: str
    entity_group: str
    statement_type: str
    item_code: str
    item_name_vi: str
    item_type: str
    fiscal_year: int
    fiscal_quarter: int
    period_type: str
    period_start: str
    period_end: str
    value: float
    unit: str
    consolidation_scope: str
    as_of_date: str
    report_version: str
    is_restated: bool
    source_report_id: str
    source_ref: str
    derived_from: str = ""
    ingested_at: str = ""
    fact_id: str = ""

    def finalize(self) -> "FactFinancialRecord":
        """Populate `fact_id` and `ingested_at` if omitted and normalize ticker."""
        norm_ticker = self.ticker.upper().strip()
        fid = self.fact_id or build_fact_id(
            ticker=norm_ticker,
            statement_type=self.statement_type,
            item_code=self.item_code,
            fiscal_year=self.fiscal_year,
            fiscal_quarter=self.fiscal_quarter,
            period_type=self.period_type,
            consolidation_scope=self.consolidation_scope,
            report_version=self.report_version,
        )
        ts = self.ingested_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return FactFinancialRecord(
            **{
                **asdict(self),
                "ticker": norm_ticker,
                "fact_id": fid,
                "ingested_at": ts,
            }
        )


def records_to_dataframe(records: Iterable[FactFinancialRecord]) -> pd.DataFrame:
    """Convert finalized `FactFinancialRecord` objects into a schema-ordered DataFrame."""
    rows = [asdict(rec.finalize()) for rec in records]
    if not rows:
        return pd.DataFrame(columns=FACT_FINANCIALS_COLUMNS)
    df = pd.DataFrame(rows)
    return df.loc[:, list(FACT_FINANCIALS_COLUMNS)]


def validate_fact_dataframe(df: pd.DataFrame) -> list[str]:
    """Validate structural, domain, and accounting invariants on `fact_financials`."""
    errors: list[str] = []

    missing_cols = [c for c in FACT_FINANCIALS_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return errors

    if df.empty:
        return errors

    # Required non-null columns (all except `derived_from`)
    for col in FACT_FINANCIALS_COLUMNS:
        if col == "derived_from":
            continue
        if df[col].isna().any():
            errors.append(f"Column '{col}' contains null values.")

    if df["fact_id"].duplicated().any():
        dups = df.loc[df["fact_id"].duplicated(), "fact_id"].tolist()
        errors.append(f"Duplicate fact_id detected: {dups[:5]}")

    domain_checks = (
        ("entity_group", VALID_ENTITY_GROUPS),
        ("statement_type", VALID_STATEMENT_TYPES),
        ("item_type", VALID_ITEM_TYPES),
        ("period_type", VALID_PERIOD_TYPES),
        ("consolidation_scope", VALID_SCOPES),
        ("report_version", VALID_REPORT_VERSIONS),
    )
    for col, allowed in domain_checks:
        bad = set(df[col].dropna().unique()) - allowed
        if bad:
            errors.append(f"Invalid values in '{col}': {sorted(bad)}")

    # Unit standardization rule
    bad_units = set(df["unit"].dropna().unique()) - {"VND"}
    if bad_units:
        errors.append(f"All values must be normalized to VND; found {sorted(bad_units)}")

    # Accounting invariant: Balance Sheet must be stock; IS/CF must be flow
    bs_non_stock = df[(df["statement_type"] == "BS") & (df["item_type"] != "stock")]
    if not bs_non_stock.empty:
        errors.append(f"BS rows must have item_type='stock' ({len(bs_non_stock)} invalid).")

    flow_stmts = df["statement_type"].isin(["IS", "CF"])
    bad_flow = df[flow_stmts & (df["item_type"] != "flow")]
    if not bad_flow.empty:
        errors.append(f"IS/CF rows must have item_type='flow' ({len(bad_flow)} invalid).")

    # Bank guard: `bank` entity_group must never contain `net_revenue`
    bank_rev = df[(df["entity_group"] == "bank") & (df["item_code"] == "net_revenue")]
    if not bank_rev.empty:
        errors.append("Bank rows must not use item_code='net_revenue'.")

    # Period quarter consistency
    fy_bad_q = df[(df["period_type"] == "FY") & (df["fiscal_quarter"] != 0)]
    if not fy_bad_q.empty:
        errors.append("FY rows must set fiscal_quarter=0.")

    q_bad_q = df[df["period_type"].isin(["Q", "YTD"]) & (~df["fiscal_quarter"].isin([1, 2, 3, 4]))]
    if not q_bad_q.empty:
        errors.append("Q/YTD rows must set fiscal_quarter in {1, 2, 3, 4}.")

    return errors
