"""Unit tests for TV1 Week 1 deliverables: VN30 classification, schema, and YTD->Q."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]

from fin_assistant.etl.pdf_manifest import generate_pilot_pdf_manifest
from fin_assistant.etl.pilot_etl import (
    derive_single_quarter_from_ytd,
    export_snapshot,
    get_pilot_tickers,
    load_vn30_reference,
)
from fin_assistant.etl.schema import (
    FACT_FINANCIALS_COLUMNS,
    FactFinancialRecord,
    records_to_dataframe,
    validate_fact_dataframe,
)


def test_vn30_constituents_count_and_classification() -> None:
    vn30 = load_vn30_reference(ROOT / "data/reference/vn30_constituents_2026-11-27.csv")
    assert len(vn30) == 30
    assert vn30["ticker"].nunique() == 30

    kept = vn30[vn30["keep_status"] == "KEEP"]
    excluded = vn30[vn30["keep_status"] == "EXCLUDE"]
    assert len(kept) == 26
    assert len(excluded) == 4
    assert set(excluded["ticker"]) == {"BVH", "SSI", "TCX", "VPL"}
    assert (excluded["exclusion_reason"].fillna("").str.len() > 10).all()

    non_fin = kept[kept["entity_group"] == "non_financial"]
    banks = kept[kept["entity_group"] == "bank"]
    assert len(non_fin) == 15
    assert len(banks) == 11

    pilots = get_pilot_tickers(vn30)
    assert pilots == ["FPT", "HPG", "MWG", "TCB", "VCB"]
    pilot_rows = vn30[vn30["ticker"].isin(pilots)]
    assert (pilot_rows["entity_group"] == "non_financial").sum() == 3
    assert (pilot_rows["entity_group"] == "bank").sum() == 2
    assert pilot_rows.loc[pilot_rows["entity_group"] == "non_financial", "sector"].nunique() == 3


def test_schema_validation_blocks_bank_net_revenue_and_bad_item_type() -> None:
    bad_bank = FactFinancialRecord(
        ticker="VCB",
        entity_group="bank",
        statement_type="IS",
        item_code="net_revenue",
        item_name_vi="Doanh thu thuần",
        item_type="flow",
        fiscal_year=2025,
        fiscal_quarter=3,
        period_type="Q",
        period_start="2025-07-01",
        period_end="2025-09-30",
        value=100.0,
        unit="VND",
        consolidation_scope="consolidated",
        as_of_date="2025-10-30",
        report_version="original",
        is_restated=False,
        source_report_id="VCB_2025Q3",
        source_ref="mock",
    )
    df_bad_bank = records_to_dataframe([bad_bank])
    errs = validate_fact_dataframe(df_bad_bank)
    assert any("net_revenue" in e for e in errs)

    bad_bs = FactFinancialRecord(
        ticker="FPT",
        entity_group="non_financial",
        statement_type="BS",
        item_code="equity_total",
        item_name_vi="Vốn chủ sở hữu",
        item_type="flow",  # Invalid: BS must be stock
        fiscal_year=2025,
        fiscal_quarter=3,
        period_type="Q",
        period_start="2025-07-01",
        period_end="2025-09-30",
        value=1000.0,
        unit="VND",
        consolidation_scope="consolidated",
        as_of_date="2025-10-30",
        report_version="original",
        is_restated=False,
        source_report_id="FPT_2025Q3",
        source_ref="mock",
    )
    errs_bs = validate_fact_dataframe(records_to_dataframe([bad_bs]))
    assert any("stock" in e for e in errs_bs)


def test_ytd_to_quarter_derivation_flow_only_and_lineage() -> None:
    records = [
        # Flow items (IS) for FPT 2025: YTD Q1, YTD Q2 (reviewed), YTD Q3, FY (audited)
        FactFinancialRecord(
            ticker="FPT",
            entity_group="non_financial",
            statement_type="IS",
            item_code="net_revenue",
            item_name_vi="Doanh thu thuần",
            item_type="flow",
            fiscal_year=2025,
            fiscal_quarter=1,
            period_type="YTD",
            period_start="2025-01-01",
            period_end="2025-03-31",
            value=16_000_000_000_000.0,
            unit="VND",
            consolidation_scope="consolidated",
            as_of_date="2025-04-25",
            report_version="original",
            is_restated=False,
            source_report_id="FPT_2025Q1_CONSOL",
            source_ref="page=4;code=10",
        ),
        FactFinancialRecord(
            ticker="FPT",
            entity_group="non_financial",
            statement_type="IS",
            item_code="net_revenue",
            item_name_vi="Doanh thu thuần",
            item_type="flow",
            fiscal_year=2025,
            fiscal_quarter=2,
            period_type="YTD",
            period_start="2025-01-01",
            period_end="2025-06-30",
            value=33_500_000_000_000.0,
            unit="VND",
            consolidation_scope="consolidated",
            as_of_date="2025-08-15",
            report_version="reviewed",
            is_restated=False,
            source_report_id="FPT_2025Q2_CONSOL_REV",
            source_ref="page=4;code=10",
        ),
        FactFinancialRecord(
            ticker="FPT",
            entity_group="non_financial",
            statement_type="IS",
            item_code="net_revenue",
            item_name_vi="Doanh thu thuần",
            item_type="flow",
            fiscal_year=2025,
            fiscal_quarter=3,
            period_type="YTD",
            period_start="2025-01-01",
            period_end="2025-09-30",
            value=51_000_000_000_000.0,
            unit="VND",
            consolidation_scope="consolidated",
            as_of_date="2025-10-28",
            report_version="original",
            is_restated=False,
            source_report_id="FPT_2025Q3_CONSOL",
            source_ref="page=4;code=10",
        ),
        FactFinancialRecord(
            ticker="FPT",
            entity_group="non_financial",
            statement_type="IS",
            item_code="net_revenue",
            item_name_vi="Doanh thu thuần",
            item_type="flow",
            fiscal_year=2025,
            fiscal_quarter=0,
            period_type="FY",
            period_start="2025-01-01",
            period_end="2025-12-31",
            value=70_000_000_000_000.0,
            unit="VND",
            consolidation_scope="consolidated",
            as_of_date="2026-03-25",
            report_version="audited",
            is_restated=False,
            source_report_id="FPT_2025FY_CONSOL_AUD",
            source_ref="page=6;code=10",
        ),
        # Stock item (BS) must NEVER be subtracted by YTD->Q derivation
        FactFinancialRecord(
            ticker="FPT",
            entity_group="non_financial",
            statement_type="BS",
            item_code="equity_total",
            item_name_vi="Vốn chủ sở hữu",
            item_type="stock",
            fiscal_year=2025,
            fiscal_quarter=2,
            period_type="Q",
            period_start="2025-04-01",
            period_end="2025-06-30",
            value=36_000_000_000_000.0,
            unit="VND",
            consolidation_scope="consolidated",
            as_of_date="2025-08-15",
            report_version="reviewed",
            is_restated=False,
            source_report_id="FPT_2025Q2_CONSOL_REV",
            source_ref="page=3;code=400",
        ),
    ]

    df_in = records_to_dataframe(records)
    assert list(df_in.columns) == list(FACT_FINANCIALS_COLUMNS)

    df_out = derive_single_quarter_from_ytd(df_in)
    assert validate_fact_dataframe(df_out) == []

    q_rows = df_out[(df_out["item_code"] == "net_revenue") & (df_out["period_type"] == "Q")]
    by_q = dict(zip(q_rows["fiscal_quarter"], q_rows["value"]))
    assert by_q == {
        1: 16_000_000_000_000.0,
        2: 17_500_000_000_000.0,
        3: 17_500_000_000_000.0,
        4: 19_000_000_000_000.0,
    }

    q4_lineage = json.loads(q_rows.loc[q_rows["fiscal_quarter"] == 4, "derived_from"].iloc[0])
    assert q4_lineage["formula"] == "FY - YTD_9M"
    assert len(q4_lineage["inputs"]) == 2

    # Export snapshot with manifest
    with tempfile.TemporaryDirectory() as tmp:
        exported = export_snapshot(df_out, tmp, snapshot_tag="pilot_test")
        manifest = json.loads(Path(exported["manifest"]).read_text(encoding="utf-8"))
        assert manifest["row_count"] == len(df_out)
        assert manifest["tickers"] == ["FPT"]


def test_pilot_pdf_manifest_covers_5y_quarters() -> None:
    manifest = generate_pilot_pdf_manifest(["FPT", "HPG", "MWG", "TCB", "VCB"])
    # 2021..2025 (5*4=20) + 2026 Q1..Q3 (3) = 23 quarters per ticker -> 115 rows
    assert len(manifest) == 115
    assert set(manifest["ticker"]) == {"FPT", "HPG", "MWG", "TCB", "VCB"}
