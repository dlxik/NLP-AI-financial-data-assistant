"""Chuẩn hóa câu hỏi tiếng Việt cho B0: NFC → viết thường → bỏ dấu → gộp khoảng trắng.

Bỏ dấu giúp B0 hiểu cả câu gõ không dấu ("doanh thu quy 3 cua VNM"). Một số từ có dấu mà bỏ dấu
sẽ trùng thuật ngữ được "bảo vệ" trước khi bỏ dấu (vd "lại" ≠ "lãi", "tôi" ≠ "TOI").
"""

from __future__ import annotations

import re
import unicodedata

_PROTECT = {
    "lại": "laj",   # "hỏi lại", "còn lại" — không phải "lãi"
    "tôi": "toj",   # đại từ — không phải TOI
    "tới": "toj",
    "nợ xấu": "no xau",
}

_SPACE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize(text: str) -> str:
    """Văn bản dùng để khớp mẫu: không dấu, viết thường, một khoảng trắng."""
    text = unicodedata.normalize("NFC", text).lower()
    for word, repl in _PROTECT.items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", repl, text)
    text = strip_accents(text)
    text = text.replace("–", "-").replace("—", "-")
    return _SPACE.sub(" ", text).strip()


def parse_number(raw: str) -> float:
    """Số kiểu Việt Nam/quốc tế: '1.234,5' → 1234.5; '15,5' → 15.5; '1.000' → 1000; '15.5' → 15.5."""
    raw = raw.strip()
    negative = raw.startswith("-")
    raw = raw.lstrip("-")
    if "." in raw and "," in raw:
        value = float(raw.replace(".", "").replace(",", "."))
    elif "," in raw:
        # một dấu phẩy = thập phân (quy ước VN); nhiều dấu phẩy = phân tách nghìn kiểu Anh
        value = float(raw.replace(",", "")) if raw.count(",") > 1 else float(raw.replace(",", "."))
    elif "." in raw:
        parts = raw.split(".")
        if all(len(p) == 3 for p in parts[1:]) and len(parts) >= 2:
            value = float(raw.replace(".", ""))  # dấu chấm phân tách nghìn
        else:
            value = float(raw)
    else:
        value = float(raw)
    return -value if negative else value
