"""Kiểm thử Output Contract v0.1 và khả năng tương thích với TV2/TV5."""

from __future__ import annotations

from fin_assistant.pipelines.contract import (
    AnswerType,
    InputRef,
    InterpretedQuery,
    MetricRow,
    PipelineOutput,
    Status,
    WarnCode,
    WarningItem,
    validate_output_contract,
)


def test_valid_single_ok_with_traceability() -> None:
    out = PipelineOutput(
        question_id="p_01",
        question_date="2025-02-15",
        pipeline="pilot",
        status=Status.OK,
        answer_type=AnswerType.SINGLE,
        metric="net_revenue_yoy",
        ticker="VNM",
        period="2024Q4",
        value=0.0425,
        unit="ratio",
        formula="(REV(2024Q4) - REV(2023Q4)) / REV(2023Q4)",
        interpreted_query=InterpretedQuery(
            ticker="VNM", tickers=("VNM",), metric="net_revenue", period="2024Q4", transform="yoy"
        ),
        inputs=(
            InputRef(
                item_code="IS.NET_REVENUE",
                ticker="VNM",
                period="2024Q4",
                value=15_400_000_000_000.0,
                unit="VND",
                source_ref="VNM_2024Q4_B02.pdf#p2:L10",
                report_version=1,
                as_of_date="2025-01-30",
            ),
        ),
        message="Tăng trưởng doanh thu thuần YoY Q4/2024 của VNM là 4,25%.",
    )
    assert validate_output_contract(out) == []


def test_valid_table_empty_valid_zero_rows() -> None:
    out = PipelineOutput(
        question_id="p_02",
        pipeline="pilot",
        status=Status.EMPTY_VALID,
        answer_type=AnswerType.TABLE,
        metric="roe_ttm",
        period_policy="common",
        rows=(),
        message="Không có mã nào đạt ROE TTM > 50% trong nhóm theo dõi.",
    )
    assert validate_output_contract(out) == []


def test_valid_bank_net_revenue_needs_clarification() -> None:
    out = PipelineOutput(
        question_id="p_03",
        pipeline="pilot",
        status=Status.NEEDS_CLARIFICATION,
        answer_type=AnswerType.ACTION,
        metric="net_revenue",
        ticker="VCB",
        period="2024Q4",
        warnings=(
            WarningItem(
                code=WarnCode.BANK_NO_NET_REVENUE,
                message="VCB là ngân hàng, BCTC không có chỉ tiêu 'doanh thu thuần'.",
                ticker="VCB",
                period="2024Q4",
                item_code="IS.NET_REVENUE",
            ),
        ),
        candidates=("Thu nhập lãi thuần (NII)", "Tổng thu nhập hoạt động (TOI)"),
        message="Vui lòng chọn chỉ tiêu thay thế phù hợp cho ngân hàng VCB.",
    )
    assert validate_output_contract(out) == []


def test_rejects_generic_warning_without_specific_target() -> None:
    out = PipelineOutput(
        question_id="p_04",
        pipeline="pilot",
        status=Status.NOT_MEANINGFUL,
        answer_type=AnswerType.ACTION,
        metric="roe_ttm",
        ticker="HAG",
        period="2024Q3",
        warnings=(
            WarningItem(
                code=WarnCode.NEGATIVE_EQUITY,
                message="Cảnh báo chung: số liệu có vấn đề.",
            ),
        ),
    )
    errs = validate_output_contract(out)
    assert any("too generic" in e for e in errs)


def test_rejects_value_present_when_not_meaningful() -> None:
    bad_payload = {
        "contract_version": "0.1",
        "question_id": "p_05",
        "pipeline": "pilot",
        "status": "not_meaningful",
        "answer_type": "action",
        "metric": "roe_ttm",
        "ticker": "HAG",
        "period": "2024Q3",
        "value": 0.33,
        "warnings": [
            {
                "code": "negative_equity",
                "message": "Vốn chủ âm tại 2024Q3",
                "ticker": "HAG",
                "period": "2024Q3",
                "item_code": "BS.EQUITY_PARENT",
                "severity": "warning",
            }
        ],
    }
    errs = validate_output_contract(bad_payload)
    assert any("value must be None" in e for e in errs)


def test_converts_from_tv2_metric_and_multi_dicts() -> None:
    metric_dict = {
        "metric": "net_revenue",
        "ticker": "FPT",
        "period": "2024Q4",
        "status": "ok",
        "value": 17_000_000_000_000.0,
        "unit": "VND",
        "formula": "IS.NET_REVENUE(2024Q4)",
        "inputs": [
            {
                "item_code": "IS.NET_REVENUE",
                "ticker": "FPT",
                "period": "2024Q4",
                "value": 17_000_000_000_000.0,
                "unit": "VND",
                "source_ref": "FPT_2024Q4.pdf#p3:L5",
                "report_version": 1,
                "as_of_date": "2025-01-25",
                "is_restated": False,
                "derived_from": None,
            }
        ],
        "warnings": [],
        "candidates": [],
        "details": {},
    }
    converted = PipelineOutput.from_metric_dict(metric_dict, question_id="q_tv2_1", pipeline="B")
    assert validate_output_contract(converted) == []

    multi_dict = {
        "metric": "roe_ttm",
        "status": "ok",
        "period_policy": "common",
        "rows": [
            {
                "metric": "roe_ttm",
                "ticker": "FPT",
                "period": "2024Q4",
                "status": "ok",
                "value": 0.28,
                "unit": "ratio",
                "formula": "TTM_NI / AVG_EQ",
                "inputs": [],
                "warnings": [],
                "candidates": [],
                "details": {},
            },
            {
                "metric": "roe_ttm",
                "ticker": "VCB",
                "period": "2024Q4",
                "status": "ok",
                "value": 0.21,
                "unit": "ratio",
                "formula": "TTM_NI / AVG_EQ",
                "inputs": [],
                "warnings": [],
                "candidates": [],
                "details": {},
            },
        ],
        "excluded": [],
        "warnings": [],
    }
    converted_multi = PipelineOutput.from_multi_dict(
        multi_dict, question_id="q_tv2_2", pipeline="B"
    )
    assert validate_output_contract(converted_multi) == []
    assert len(converted_multi.rows) == 2
    assert isinstance(converted_multi.rows[0], MetricRow)
