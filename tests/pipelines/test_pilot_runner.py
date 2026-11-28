"""Kiểm thử chạy luồng sinh câu trả lời nháp trên tập ví dụ tự tạo (TV3 GĐ1)."""

from __future__ import annotations

import json
from pathlib import Path

from fin_assistant.pipelines.config import LLMConfig, load_llm_config
from fin_assistant.pipelines.contract import Status
from fin_assistant.pipelines.llm_client import MockLLMClient
from fin_assistant.pipelines.logging import RunLogger
from fin_assistant.pipelines.runner import PilotPipelineRunner
from fin_assistant.pipelines.sandbox import SandboxConfig, SandboxExecutor


def _pilot_mock_responder(_system: str, user_prompt: str, _cfg: LLMConfig) -> str:
    if "q_rev_yoy" in user_prompt:
        return json.dumps(
            {
                "status": "ok",
                "answer_type": "single",
                "metric": "net_revenue_yoy",
                "ticker": "VNM",
                "period": "2024Q4",
                "unit": "ratio",
                "formula": "(REV(2024Q4) - REV(2023Q4)) / REV(2023Q4)",
                "python_code": (
                    "import pandas as pd\n"
                    "df = pd.DataFrame(rows_data)\n"
                    "r24 = df.loc[df['period']=='2024Q4', 'value'].iloc[0]\n"
                    "r23 = df.loc[df['period']=='2023Q4', 'value'].iloc[0]\n"
                    "result = {'value': round((r24 - r23) / r23, 4)}\n"
                ),
                "message": "Tăng trưởng doanh thu thuần YoY Q4/2024 của VNM là 10%.",
            },
            ensure_ascii=False,
        )
    if "q_bank_rev" in user_prompt:
        return json.dumps(
            {
                "status": "needs_clarification",
                "answer_type": "action",
                "metric": "net_revenue",
                "ticker": "VCB",
                "period": "2024Q4",
                "warnings": [
                    {
                        "code": "bank_no_net_revenue",
                        "message": "VCB là ngân hàng, không có 'doanh thu thuần'.",
                        "ticker": "VCB",
                        "period": "2024Q4",
                        "item_code": "IS.NET_REVENUE",
                        "severity": "warning",
                    }
                ],
                "candidates": ["Thu nhập lãi thuần", "Tổng thu nhập hoạt động"],
                "message": "Vui lòng chọn chỉ tiêu thay thế cho ngân hàng VCB.",
            },
            ensure_ascii=False,
        )
    if "q_roe_neg_eq" in user_prompt:
        return json.dumps(
            {
                "status": "not_meaningful",
                "answer_type": "action",
                "metric": "roe_ttm",
                "ticker": "HAG",
                "period": "2024Q3",
                "warnings": [
                    {
                        "code": "negative_equity",
                        "message": "VCSH âm tại 2024Q3, ROE TTM không xác định.",
                        "ticker": "HAG",
                        "period": "2024Q3",
                        "item_code": "BS.EQUITY_PARENT",
                        "severity": "warning",
                    }
                ],
                "message": "Không tính ROE khi vốn chủ sở hữu âm.",
            },
            ensure_ascii=False,
        )
    if "q_empty_screen" in user_prompt:
        return json.dumps(
            {
                "status": "empty_valid",
                "answer_type": "table",
                "metric": "roe_ttm",
                "period_policy": "common",
                "rows": [],
                "message": "Không có mã nào thỏa ROE TTM > 50%.",
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "status": "missing_data",
            "answer_type": "action",
            "metric": "roe_ttm",
            "ticker": "FPT",
            "period": "2026Q1",
            "warnings": [
                {
                    "code": "not_yet_published",
                    "message": "Kỳ 2026Q1 chưa công bố tại ngày hỏi.",
                    "ticker": "FPT",
                    "period": "2026Q1",
                    "item_code": "IS.NI_PARENT",
                    "severity": "warning",
                }
            ],
            "message": "Chưa có dữ liệu kỳ 2026Q1.",
        },
        ensure_ascii=False,
    )


def test_pilot_runner_batch_stability_and_sandbox(tmp_path: Path) -> None:
    cfg = load_llm_config(Path("configs/llm.pilot.json"))
    log_path = tmp_path / "pilot_runs.jsonl"
    runner = PilotPipelineRunner(
        config=cfg,
        client=MockLLMClient(responder=_pilot_mock_responder),
        sandbox=SandboxExecutor(SandboxConfig(timeout_sec=10.0)),
        logger=RunLogger(log_path),
    )

    sample_questions = [
        {
            "question_id": "q_rev_yoy",
            "question": "Tăng trưởng doanh thu thuần YoY quý 4/2024 của VNM là bao nhiêu?",
            "question_date": "2025-02-15",
            "sandbox_context": {
                "rows_data": [
                    {"period": "2023Q4", "value": 1000.0},
                    {"period": "2024Q4", "value": 1100.0},
                ]
            },
        },
        {
            "question_id": "q_bank_rev",
            "question": "Doanh thu thuần của VCB quý 4/2024 là bao nhiêu?",
            "question_date": "2025-02-15",
        },
        {
            "question_id": "q_roe_neg_eq",
            "question": "ROE TTM quý 3/2024 của HAG là bao nhiêu?",
            "question_date": "2025-02-15",
        },
        {
            "question_id": "q_empty_screen",
            "question": "Lọc các mã có ROE TTM > 50%.",
            "question_date": "2025-02-15",
        },
        {
            "question_id": "q_missing",
            "question": "ROE TTM quý 1/2026 của FPT là bao nhiêu?",
            "question_date": "2025-02-15",
        },
    ]

    summary = runner.run_batch(sample_questions, repeats=3)
    assert summary["total_runs"] == 15
    assert summary["valid_runs"] == 15
    assert summary["format_stability_rate"] == 1.0
    assert summary["consistent_across_repeats"] is True

    first_out = summary["results"][0].output
    assert first_out is not None
    assert first_out.status is Status.OK
    assert first_out.value == 0.1
    assert first_out.execution_meta is not None
    assert first_out.execution_meta.sandbox_used is True
    assert first_out.execution_meta.sandbox_ok is True

    log_summary = runner.logger.summarize()  # type: ignore[union-attr]
    assert log_summary["total_runs"] == 15
    assert log_summary["contract_valid_rate"] == 1.0
