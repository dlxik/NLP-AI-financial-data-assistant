"""Pipeline runner nháp cho Giai đoạn 1 (TV3).

Kết nối LLMClient -> trích xuất JSON -> (tùy chọn) Sandbox v0.1 -> kiểm tra Output Contract
-> ghi log chuẩn hóa JSONL để đo độ ổn định định dạng.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from fin_assistant.pipelines.config import LLMConfig
from fin_assistant.pipelines.contract import (
    CONTRACT_VERSION,
    ExecutionMeta,
    PipelineOutput,
    validate_output_contract,
)
from fin_assistant.pipelines.llm_client import LLMClient
from fin_assistant.pipelines.logging import RunLogger, RunLogRecord
from fin_assistant.pipelines.sandbox import SandboxExecutor


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)

PILOT_SYSTEM_PROMPT = (
    "Bạn là trợ lý phân tích dữ liệu tài chính VN30. "
    "Chỉ trả về duy nhất một JSON object hợp lệ theo Output Contract v0.1, "
    "không bịa số, nêu rõ trạng thái (ok, empty_valid, missing_data, not_meaningful, "
    "needs_clarification, not_applicable) và cảnh báo cụ thể (ticker, period, item_code)."
)


@dataclass(frozen=True)
class PilotRunResult:
    """Kết quả một lượt chạy câu hỏi qua PilotPipelineRunner."""

    output: PipelineOutput | None
    validation_errors: tuple[str, ...]
    log_record: RunLogRecord

    @property
    def is_valid(self) -> bool:
        return self.output is not None and len(self.validation_errors) == 0


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """Trích xuất JSON object từ phản hồi thô của LLM (hỗ trợ code fence)."""
    cleaned = raw_text.strip()
    match = _JSON_FENCE_RE.search(cleaned)
    if match:
        cleaned = match.group(1).strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object")
    return parsed


class PilotPipelineRunner:
    """Runner chuẩn hóa cho giai đoạn thử nghiệm và đo độ ổn định định dạng."""

    def __init__(
        self,
        config: LLMConfig,
        client: LLMClient,
        *,
        pipeline_name: str = "pilot_llm",
        sandbox: SandboxExecutor | None = None,
        logger: RunLogger | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.pipeline_name = pipeline_name
        self.sandbox = sandbox
        self.logger = logger

    def run_question(
        self,
        question_id: str,
        question_text: str,
        *,
        question_date: str | None = None,
        context_hint: str = "",
        sandbox_context: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> PilotRunResult:
        """Chạy 1 câu hỏi qua LLM, kiểm tra Output Contract và ghi log."""
        rid = run_id or uuid.uuid4().hex[:12]
        user_prompt = self._build_user_prompt(question_id, question_text, question_date, context_hint)

        resp = self.client.generate(PILOT_SYSTEM_PROMPT, user_prompt, self.config)
        num_calls = 1
        sandbox_status = "not_used"
        sandbox_used = False
        sandbox_ok: bool | None = None

        try:
            payload = extract_json_object(resp.text)
        except Exception as exc:
            rec = self._make_log(
                rid,
                question_id,
                question_date,
                resp,
                num_calls=num_calls,
                parse_status="parse_error",
                contract_valid=False,
                sandbox_status=sandbox_status,
                error_type="json_parse_error",
                error_message=str(exc),
            )
            self._write_log(rec)
            return PilotRunResult(output=None, validation_errors=(f"JSON parse error: {exc}",), log_record=rec)

        # Bổ sung các trường định danh chuẩn nếu LLM bỏ sót.
        payload.setdefault("contract_version", CONTRACT_VERSION)
        payload.setdefault("question_id", question_id)
        payload.setdefault("question_date", question_date)
        payload.setdefault("pipeline", self.pipeline_name)

        # Tùy chọn thực thi mã Python nếu LLM trả kèm `python_code` và runner có Sandbox.
        python_code = payload.pop("python_code", None)
        if python_code is not None:
            if self.sandbox is None:
                sandbox_status = "unavailable"
            else:
                sandbox_used = True
                sb_res = self.sandbox.execute(str(python_code), context=sandbox_context)
                sandbox_ok = sb_res.ok
                sandbox_status = "ok" if sb_res.ok else (sb_res.error_type or "error")
                if sb_res.ok and isinstance(sb_res.result, dict):
                    for key, val in sb_res.result.items():
                        payload[key] = val
                elif sb_res.ok and payload.get("value") is None:
                    payload["value"] = sb_res.result
                elif not sb_res.ok:
                    rec = self._make_log(
                        rid,
                        question_id,
                        question_date,
                        resp,
                        num_calls=num_calls,
                        parse_status="ok",
                        contract_valid=False,
                        sandbox_status=sandbox_status,
                        error_type=sb_res.error_type or "sandbox_error",
                        error_message=sb_res.error_message,
                    )
                    self._write_log(rec)
                    return PilotRunResult(
                        output=None,
                        validation_errors=(f"Sandbox error ({sb_res.error_type}): {sb_res.error_message}",),
                        log_record=rec,
                    )

        payload["execution_meta"] = ExecutionMeta(
            model=self.config.model,
            model_version=resp.model_version,
            seed=self.config.seed,
            temperature=self.config.temperature,
            num_llm_calls=num_calls,
            latency_ms=resp.latency_ms,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            total_tokens=resp.total_tokens,
            sandbox_used=sandbox_used,
            sandbox_ok=sandbox_ok,
        ).to_dict()

        errors = validate_output_contract(payload)
        output_obj = PipelineOutput.from_dict(payload) if not errors else None
        rec = self._make_log(
            rid,
            question_id,
            question_date,
            resp,
            num_calls=num_calls,
            parse_status="ok",
            contract_valid=(len(errors) == 0),
            sandbox_status=sandbox_status,
            output_status=output_obj.status.value if output_obj else None,
            error_type=None if not errors else "contract_validation_error",
            error_message="; ".join(errors),
        )
        self._write_log(rec)
        return PilotRunResult(output=output_obj, validation_errors=tuple(errors), log_record=rec)

    def run_batch(
        self,
        questions: list[dict[str, Any]],
        *,
        repeats: int = 1,
    ) -> dict[str, Any]:
        """Chạy hàng loạt để kiểm tra độ ổn định định dạng qua nhiều lần lặp."""
        results: list[PilotRunResult] = []
        for rep in range(repeats):
            for q in questions:
                res = self.run_question(
                    question_id=str(q["question_id"]),
                    question_text=str(q["question"]),
                    question_date=q.get("question_date"),
                    context_hint=str(q.get("context_hint", "")),
                    sandbox_context=q.get("sandbox_context"),
                    run_id=f"rep{rep + 1}_{q['question_id']}",
                )
                results.append(res)

        total = len(results)
        valid_count = sum(1 for r in results if r.is_valid)
        consistent_across_repeats = True
        if repeats > 1 and questions:
            by_qid: dict[str, list[str | None]] = {}
            for r in results:
                sig = (
                    json.dumps(
                        {
                            "status": r.output.status.value,
                            "value": r.output.value,
                            "rows": [row.to_dict() for row in r.output.rows],
                        },
                        sort_keys=True,
                    )
                    if r.output
                    else None
                )
                by_qid.setdefault(r.log_record.question_id, []).append(sig)
            consistent_across_repeats = all(len(set(sigs)) == 1 for sigs in by_qid.values())

        return {
            "total_runs": total,
            "valid_runs": valid_count,
            "format_stability_rate": round(valid_count / total, 4) if total else 0.0,
            "consistent_across_repeats": consistent_across_repeats,
            "results": results,
        }

    @staticmethod
    def _build_user_prompt(
        question_id: str,
        question_text: str,
        question_date: str | None,
        context_hint: str,
    ) -> str:
        parts = [f"question_id: {question_id}"]
        if question_date:
            parts.append(f"question_date: {question_date}")
        parts.append(f"question: {question_text}")
        if context_hint.strip():
            parts.append(f"context:\n{context_hint.strip()}")
        return "\n".join(parts)

    def _make_log(
        self,
        run_id: str,
        question_id: str,
        question_date: str | None,
        resp: Any,
        *,
        num_calls: int,
        parse_status: str,
        contract_valid: bool,
        sandbox_status: str,
        output_status: str | None = None,
        error_type: str | None = None,
        error_message: str = "",
    ) -> RunLogRecord:
        return RunLogRecord(
            run_id=run_id,
            question_id=question_id,
            question_date=question_date,
            pipeline_name=self.pipeline_name,
            model=self.config.model,
            model_version=resp.model_version,
            temperature=self.config.temperature,
            seed=self.config.seed,
            prompt_version=self.config.prompt_version,
            num_llm_calls=num_calls,
            latency_ms=resp.latency_ms,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            total_tokens=resp.total_tokens,
            parse_status=parse_status,
            contract_valid=contract_valid,
            sandbox_status=sandbox_status,
            output_status=output_status,
            error_type=error_type,
            error_message=error_message,
            raw_response=resp.text,
        )

    def _write_log(self, rec: RunLogRecord) -> None:
        if self.logger is not None:
            self.logger.write(rec)
