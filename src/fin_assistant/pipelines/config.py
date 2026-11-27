"""Quản lý cấu hình LLM thử nghiệm (TV3).

Cấu hình được lưu trong ``configs/llm.*.json`` để đóng băng tham số tái lập thí nghiệm
(model, phiên bản API, temperature, seed, format log). Không lưu API key trong file cấu hình.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset({"api_key", "secret", "secret_key", "token"})


@dataclass(frozen=True)
class LLMConfig:
    """Cấu hình gọi LLM đã chuẩn hóa."""

    config_version: str = "0.1"
    status: str = "draft_pilot_defaults_pending_team_lock"
    provider: str = "mock"
    model: str = "TBD_TEAM_LOCK"
    api_version: str = "TBD_TEAM_LOCK"
    base_url: str = ""
    api_key_env: str = "LLM_API_KEY"
    temperature: float = 0.0
    seed: int | None = 42
    max_tokens: int = 1024
    timeout_sec: float = 30.0
    max_retries: int = 2
    max_repair_calls: int = 0
    prompt_version: str = "pilot-v0.1"
    log_format: str = "jsonl"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMConfig:
        for bad_key in _FORBIDDEN_SECRET_KEYS:
            if bad_key in data and str(data[bad_key]).strip():
                raise ValueError(
                    f"Do not store secrets ('{bad_key}') in config files; use .env and api_key_env"
                )
        cfg = cls(
            config_version=str(data.get("config_version", "0.1")),
            status=str(data.get("status", "draft")),
            provider=str(data.get("provider", "mock")),
            model=str(data["model"]),
            api_version=str(data.get("api_version", "")),
            base_url=str(data.get("base_url", "")),
            api_key_env=str(data.get("api_key_env", "LLM_API_KEY")),
            temperature=float(data.get("temperature", 0.0)),
            seed=int(data["seed"]) if data.get("seed") is not None else None,
            max_tokens=int(data.get("max_tokens", 1024)),
            timeout_sec=float(data.get("timeout_sec", 30.0)),
            max_retries=int(data.get("max_retries", 2)),
            max_repair_calls=int(data.get("max_repair_calls", 0)),
            prompt_version=str(data.get("prompt_version", "pilot-v0.1")),
            log_format=str(data.get("log_format", "jsonl")),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.timeout_sec <= 0:
            raise ValueError("timeout_sec must be positive")
        if self.max_retries < 0 or self.max_repair_calls < 0:
            raise ValueError("max_retries and max_repair_calls must be non-negative")
        if self.log_format != "jsonl":
            raise ValueError("log_format must be 'jsonl'")

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "api_version": self.api_version,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
            "timeout_sec": self.timeout_sec,
            "max_retries": self.max_retries,
            "max_repair_calls": self.max_repair_calls,
            "prompt_version": self.prompt_version,
            "log_format": self.log_format,
        }


def load_llm_config(path: str | Path) -> LLMConfig:
    """Đọc và kiểm tra cấu hình LLM từ file JSON."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("LLM config JSON must be an object")
    return LLMConfig.from_dict(raw)
