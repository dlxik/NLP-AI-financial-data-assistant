"""Kiểm thử cấu hình LLM và RunLogger chuẩn hóa JSONL."""

from __future__ import annotations

from pathlib import Path

import pytest

from fin_assistant.pipelines.config import LLMConfig, load_llm_config
from fin_assistant.pipelines.logging import RunLogger, RunLogRecord


def test_load_pilot_config_from_repo() -> None:
    cfg = load_llm_config(Path("configs/llm.pilot.json"))
    assert cfg.temperature == 0.0
    assert cfg.seed == 42
    assert cfg.log_format == "jsonl"
    assert cfg.provider == "mock"


def test_config_rejects_embedded_secret() -> None:
    with pytest.raises(ValueError, match="secret|api_key"):
        LLMConfig.from_dict({"model": "gpt-test", "api_key": "sk-secret-123"})


def test_config_rejects_invalid_temperature() -> None:
    with pytest.raises(ValueError, match="temperature"):
        LLMConfig.from_dict({"model": "gpt-test", "temperature": 2.5})


def test_run_logger_writes_and_summarizes_jsonl(tmp_path: Path) -> None:
    log_file = tmp_path / "runs" / "pilot.jsonl"
    logger = RunLogger(log_file)
    logger.write(
        RunLogRecord(
            run_id="r1",
            question_id="q1",
            pipeline_name="pilot",
            model="m",
            model_version="v1",
            temperature=0.0,
            seed=42,
            prompt_version="pilot-v0.1",
            num_llm_calls=1,
            latency_ms=120.0,
            prompt_tokens=100,
            completion_tokens=40,
            total_tokens=140,
            parse_status="ok",
            contract_valid=True,
            output_status="ok",
        )
    )
    logger.write(
        RunLogRecord(
            run_id="r2",
            question_id="q2",
            pipeline_name="pilot",
            model="m",
            model_version="v1",
            temperature=0.0,
            seed=42,
            prompt_version="pilot-v0.1",
            num_llm_calls=1,
            latency_ms=80.0,
            prompt_tokens=80,
            completion_tokens=20,
            total_tokens=100,
            parse_status="parse_error",
            contract_valid=False,
            error_type="json_parse_error",
        )
    )

    rows = logger.read_all()
    assert len(rows) == 2
    summary = logger.summarize()
    assert summary["total_runs"] == 2
    assert summary["parse_ok_rate"] == 0.5
    assert summary["contract_valid_rate"] == 0.5
    assert summary["avg_latency_ms"] == 100.0
    assert summary["total_tokens"] == 240
    assert summary["total_llm_calls"] == 2
