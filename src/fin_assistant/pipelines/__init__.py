"""TV3 — LLM pipeline (A, B, B1, D), sandbox thực thi, demo truy vết.

Phương pháp B gọi ``fin_assistant.semantic.get_metric``; output contract dùng chung khóa với
``MetricResult.to_dict()`` và ``MultiResult.to_dict()``.
"""

from fin_assistant.pipelines.config import LLMConfig, load_llm_config
from fin_assistant.pipelines.contract import (
    AnswerType,
    ExecutionMeta,
    InputRef,
    InterpretedQuery,
    MetricRow,
    PipelineOutput,
    Status,
    WarnCode,
    WarningItem,
    validate_output_contract,
)
from fin_assistant.pipelines.llm_client import LLMClient, LLMResponse, MockLLMClient, OpenAICompatibleClient
from fin_assistant.pipelines.logging import RunLogger, RunLogRecord
from fin_assistant.pipelines.runner import PilotPipelineRunner
from fin_assistant.pipelines.sandbox import SandboxConfig, SandboxExecutor, SandboxResult

__all__ = [
    "AnswerType",
    "ExecutionMeta",
    "InputRef",
    "InterpretedQuery",
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "MetricRow",
    "MockLLMClient",
    "OpenAICompatibleClient",
    "PilotPipelineRunner",
    "PipelineOutput",
    "RunLogRecord",
    "RunLogger",
    "SandboxConfig",
    "SandboxExecutor",
    "SandboxResult",
    "Status",
    "WarnCode",
    "WarningItem",
    "load_llm_config",
    "validate_output_contract",
]
