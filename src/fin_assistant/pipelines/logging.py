"""Chuẩn hóa ghi log JSONL cho mọi lượt chạy pipeline LLM (TV3)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunLogRecord:
    """Bản ghi log chuẩn của một lượt chạy câu hỏi."""

    run_id: str
    question_id: str
    pipeline_name: str
    model: str
    model_version: str
    temperature: float
    seed: int | None
    prompt_version: str
    num_llm_calls: int
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    parse_status: str
    contract_valid: bool
    sandbox_status: str = "not_used"
    output_status: str | None = None
    error_type: str | None = None
    error_message: str = ""
    question_date: str | None = None
    raw_response: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "question_id": self.question_id,
            "question_date": self.question_date,
            "pipeline_name": self.pipeline_name,
            "model": self.model,
            "model_version": self.model_version,
            "temperature": self.temperature,
            "seed": self.seed,
            "prompt_version": self.prompt_version,
            "num_llm_calls": self.num_llm_calls,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "parse_status": self.parse_status,
            "contract_valid": self.contract_valid,
            "sandbox_status": self.sandbox_status,
            "output_status": self.output_status,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "raw_response": self.raw_response,
        }


class RunLogger:
    """Ghi và đọc log JSONL cho các đợt chạy thử nghiệm."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)

    def write(self, record: RunLogRecord) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.to_dict(), ensure_ascii=False)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def summarize(self) -> dict[str, Any]:
        """Tổng hợp nhanh tỷ lệ ổn định định dạng, độ trễ và token từ log."""
        rows = self.read_all()
        total = len(rows)
        if total == 0:
            return {
                "total_runs": 0,
                "parse_ok_rate": 0.0,
                "contract_valid_rate": 0.0,
                "avg_latency_ms": 0.0,
                "total_tokens": 0,
                "total_llm_calls": 0,
            }
        parse_ok = sum(1 for r in rows if r.get("parse_status") == "ok")
        contract_ok = sum(1 for r in rows if r.get("contract_valid") is True)
        latencies = [float(r.get("latency_ms", 0.0)) for r in rows]
        tokens = sum(int(r.get("total_tokens", 0)) for r in rows)
        calls = sum(int(r.get("num_llm_calls", 0)) for r in rows)
        return {
            "total_runs": total,
            "parse_ok_rate": round(parse_ok / total, 4),
            "contract_valid_rate": round(contract_ok / total, 4),
            "avg_latency_ms": round(sum(latencies) / total, 2),
            "total_tokens": tokens,
            "total_llm_calls": calls,
        }
