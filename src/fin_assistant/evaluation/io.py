"""Đọc/ghi JSON hoặc JSONL cho script chấm batch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import GoldCase


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError(f"{source} must contain a JSON array or JSONL records")
    return payload


def load_gold(path: str | Path) -> list[GoldCase]:
    return [GoldCase.from_dict(record) for record in load_records(path)]
