"""Script chạy thử luồng TV3 Giai đoạn 1 trên tập ví dụ tự tạo để đo độ ổn định định dạng.

Mặc định dùng MockLLMClient (chạy offline không cần API key). Khi nhóm đã chốt provider/key,
có thể truyền ``--live`` và cấu hình ``LLM_API_KEY`` trong môi trường.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fin_assistant.pipelines.config import LLMConfig, load_llm_config
from fin_assistant.pipelines.llm_client import MockLLMClient, OpenAICompatibleClient
from fin_assistant.pipelines.logging import RunLogger
from fin_assistant.pipelines.runner import PilotPipelineRunner
from fin_assistant.pipelines.sandbox import SandboxConfig, SandboxExecutor


SAMPLE_QUESTIONS = [
    {
        "question_id": "tv3_ex_01",
        "question": "Tính tăng trưởng doanh thu thuần YoY quý 4/2024 của mã phi tài chính VNM.",
        "question_date": "2025-02-15",
        "sandbox_context": {
            "rows_data": [
                {"period": "2023Q4", "value": 15000.0},
                {"period": "2024Q4", "value": 15750.0},
            ]
        },
    },
    {
        "question_id": "tv3_ex_02",
        "question": "Doanh thu thuần quý 4/2024 của ngân hàng VCB là bao nhiêu?",
        "question_date": "2025-02-15",
    },
    {
        "question_id": "tv3_ex_03",
        "question": "ROE TTM quý 3/2024 khi vốn chủ sở hữu bình quân âm.",
        "question_date": "2025-02-15",
    },
    {
        "question_id": "tv3_ex_04",
        "question": "Liệt kê các mã có ROE TTM > 60%.",
        "question_date": "2025-02-15",
    },
    {
        "question_id": "tv3_ex_05",
        "question": "Doanh thu quý 2/2026 của FPT (kỳ chưa công bố).",
        "question_date": "2025-02-15",
    },
]


def _default_mock_responder(_system: str, user_prompt: str, _cfg: LLMConfig) -> str:
    if "tv3_ex_01" in user_prompt:
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
                "message": "Tăng trưởng doanh thu thuần YoY Q4/2024 của VNM là 5%.",
            },
            ensure_ascii=False,
        )
    if "tv3_ex_02" in user_prompt:
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
                        "message": "VCB thuộc nhóm ngân hàng, không dùng 'doanh thu thuần'.",
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
    if "tv3_ex_03" in user_prompt:
        return json.dumps(
            {
                "status": "not_meaningful",
                "answer_type": "action",
                "metric": "roe_ttm",
                "ticker": "SAMPLE_NEG",
                "period": "2024Q3",
                "warnings": [
                    {
                        "code": "negative_equity",
                        "message": "VCSH âm tại 2024Q3 nên ROE TTM không xác định.",
                        "ticker": "SAMPLE_NEG",
                        "period": "2024Q3",
                        "item_code": "BS.EQUITY_PARENT",
                        "severity": "warning",
                    }
                ],
                "message": "Không tính ROE khi vốn chủ sở hữu âm.",
            },
            ensure_ascii=False,
        )
    if "tv3_ex_04" in user_prompt:
        return json.dumps(
            {
                "status": "empty_valid",
                "answer_type": "table",
                "metric": "roe_ttm",
                "period_policy": "common",
                "rows": [],
                "message": "Không có mã nào thỏa điều kiện ROE TTM > 60%.",
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "status": "missing_data",
            "answer_type": "action",
            "metric": "net_revenue",
            "ticker": "FPT",
            "period": "2026Q2",
            "warnings": [
                {
                    "code": "not_yet_published",
                    "message": "BCTC 2026Q2 chưa công bố tại ngày hỏi 2025-02-15.",
                    "ticker": "FPT",
                    "period": "2026Q2",
                    "item_code": "IS.NET_REVENUE",
                    "severity": "warning",
                }
            ],
            "message": "Chưa có dữ liệu kỳ 2026Q2.",
        },
        ensure_ascii=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy kiểm tra luồng nháp TV3 GĐ1.")
    parser.add_argument("--config", default="configs/llm.pilot.json")
    parser.add_argument("--log", default="runs/tv3_pilot_check.jsonl")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    cfg = load_llm_config(Path(args.config))
    client = (
        OpenAICompatibleClient()
        if args.live
        else MockLLMClient(responder=_default_mock_responder)
    )
    logger = RunLogger(Path(args.log))
    sandbox = SandboxExecutor(SandboxConfig(timeout_sec=10.0))
    runner = PilotPipelineRunner(cfg, client, sandbox=sandbox, logger=logger)

    summary = runner.run_batch(SAMPLE_QUESTIONS, repeats=args.repeats)
    report = {
        "total_runs": summary["total_runs"],
        "valid_runs": summary["valid_runs"],
        "format_stability_rate": summary["format_stability_rate"],
        "consistent_across_repeats": summary["consistent_across_repeats"],
        "log_summary": logger.summarize(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
