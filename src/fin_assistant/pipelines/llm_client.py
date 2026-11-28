"""Giao diện gọi LLM chuẩn hóa (Mock offline & OpenAI-compatible HTTP client)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol

from fin_assistant.pipelines.config import LLMConfig


@dataclass(frozen=True)
class LLMResponse:
    """Kết quả thô trả về từ một lượt gọi LLM."""

    text: str
    model_version: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0


class LLMClient(Protocol):
    """Giao diện trừu tượng cho mọi backend LLM."""

    def generate(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> LLMResponse: ...


class MockLLMClient:
    """Client giả lập chạy offline, xác định theo prompt/hàm phản hồi để test runner & format."""

    def __init__(
        self,
        responder: Callable[[str, str, LLMConfig], str] | None = None,
        *,
        canned_responses: dict[str, str] | None = None,
    ) -> None:
        self._responder = responder
        self._canned = canned_responses or {}

    def generate(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> LLMResponse:
        t0 = time.perf_counter()
        if self._responder is not None:
            text = self._responder(system_prompt, user_prompt, config)
        else:
            text = ""
            for key, value in self._canned.items():
                if key in user_prompt:
                    text = value
                    break
            if not text:
                raise KeyError("MockLLMClient received unmapped prompt")

        prompt_toks = max(1, (len(system_prompt) + len(user_prompt)) // 4)
        comp_toks = max(1, len(text) // 4)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return LLMResponse(
            text=text,
            model_version=config.api_version or config.model,
            prompt_tokens=prompt_toks,
            completion_tokens=comp_toks,
            total_tokens=prompt_toks + comp_toks,
            latency_ms=elapsed_ms,
        )


class OpenAICompatibleClient:
    """Client HTTP dùng thư viện chuẩn cho các endpoint tương thích Chat Completions."""

    def generate(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> LLMResponse:
        if not config.base_url.strip():
            raise ValueError("base_url is required for OpenAICompatibleClient")
        api_key = os.environ.get(config.api_key_env, "").strip()
        if not api_key:
            raise EnvironmentError(
                f"Missing API key in environment variable '{config.api_key_env}'"
            )

        url = config.base_url.rstrip("/") + "/chat/completions"
        body: dict[str, object] = {
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if config.seed is not None:
            body["seed"] = config.seed

        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        last_err: Exception | None = None
        for attempt in range(config.max_retries + 1):
            t0 = time.perf_counter()
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=config.timeout_sec) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                choices = raw.get("choices") or []
                text = str(choices[0]["message"]["content"]) if choices else ""
                usage = raw.get("usage") or {}
                p_tok = int(usage.get("prompt_tokens", 0))
                c_tok = int(usage.get("completion_tokens", 0))
                t_tok = int(usage.get("total_tokens", p_tok + c_tok))
                model_ver = str(raw.get("model", config.api_version or config.model))
                return LLMResponse(
                    text=text,
                    model_version=model_ver,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=t_tok,
                    latency_ms=latency_ms,
                )
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as exc:
                last_err = exc
                if attempt < config.max_retries:
                    time.sleep(min(2.0**attempt, 4.0))
        raise RuntimeError(f"LLM API call failed after retries: {last_err}")
