"""Từ vựng quy tắc của B0 — mọi mẫu viết trên văn bản **đã bỏ dấu, viết thường** (xem ``normalize``).

Thứ tự trong mỗi danh sách là thứ tự ưu tiên: mẫu cụ thể/dài trước, mẫu chung sau. Mỗi đoạn đã
khớp bị "tiêu thụ" (thay bằng khoảng trắng) nên mẫu chung không khớp lại phần của mẫu cụ thể.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- nhãn đặc biệt cho chỉ số -------------------------------------------------
AMBIG_PROFIT = "@ambiguous_profit"
AMBIG_MARGIN = "@ambiguous_margin"
UNSUPPORTED = "@unsupported"


@dataclass(frozen=True)
class MetricPattern:
    pattern: re.Pattern[str]
    target: str  # id chỉ số | AMBIG_* | UNSUPPORTED
    label: str = ""  # mô tả cho thông điệp (chỉ số ngoài danh mục / giả định)
    assumption: str | None = None  # giả định "nhẹ" luôn hiển thị (vd "doanh thu" → doanh thu thuần)


def _p(regex: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){regex}(?![a-z0-9])")


METRIC_PATTERNS: tuple[MetricPattern, ...] = (
    # --- lớp 2: tỷ số (viết trước vì chứa từ của lớp 1) -------------------------
    MetricPattern(_p(r"(?:bien|ty suat) (?:loi nhuan|lai) gop|bien gop|gross margin"
                     r"|(?:ty le )?loi nhuan gop tren doanh thu(?: thuan)?"), "gross_margin"),
    MetricPattern(_p(r"(?:bien|ty suat) (?:loi nhuan|lai) (?:rong|sau thue|thuan)|bien rong|net margin"
                     r"|(?:ty le )?loi nhuan (?:rong|sau thue) tren doanh thu(?: thuan)?"), "net_margin"),
    MetricPattern(_p(r"(?:bien|ty suat) (?:loi nhuan|lai)"), AMBIG_MARGIN),
    MetricPattern(_p(r"roe|ty suat (?:loi nhuan )?tren von chu(?: so huu)?|ty suat sinh loi tren von chu(?: so huu)?"),
                  "roe_ttm"),
    MetricPattern(_p(r"roa|ty suat (?:loi nhuan )?tren tong tai san|ty suat sinh loi tren tong tai san"),
                  "roa_ttm"),
    MetricPattern(_p(r"no vay(?: tren von chu(?: so huu)?)?|vay no|no vay rong"), UNSUPPORTED,
                  "nợ vay (danh mục chỉ có nợ phải trả)"),
    MetricPattern(_p(r"(?:ty le |he so )?no phai tra (?:tren|/) ?von chu(?: so huu)?|no ?/ ?von chu(?: so huu)?"
                     r"|d ?/ ?e|don bay tai chinh|he so no(?: tren von chu(?: so huu)?)?"),
                  "liabilities_to_equity", assumption="hiểu 'nợ' là nợ phải trả (mã 300), không phải nợ vay"),
    MetricPattern(_p(r"no phai tra|tong no(?: phai tra)?"), "total_liabilities"),
    MetricPattern(_p(r"tong tai san|quy mo tai san"), "total_assets"),
    MetricPattern(_p(r"von chu so huu|vcsh|von chu"), "equity_parent",
                  assumption="vốn chủ sở hữu thuộc cổ đông công ty mẹ (400 − 429)"),
    # --- ngân hàng ---------------------------------------------------------------
    MetricPattern(_p(r"thu nhap lai thuan|nii"), "bank_nii"),
    MetricPattern(_p(r"tong thu nhap hoat dong|tong thu nhap thuan hoat dong"), "bank_toi"),
    MetricPattern(_p(r"thu nhap lai va (?:cac khoan )?(?:thu nhap )?tuong tu|thu nhap lai"), "bank_interest_income"),
    # --- ngoài danh mục (B0 từ chối có lý do, không đoán) --------------------------
    MetricPattern(_p(r"doanh thu (?:hoat dong )?tai chinh"), UNSUPPORTED, "doanh thu hoạt động tài chính"),
    MetricPattern(_p(r"loi nhuan truoc thue|lntt|lai truoc thue"), UNSUPPORTED, "lợi nhuận trước thuế"),
    MetricPattern(_p(r"ebitda|ebit|dong tien tu do|fcf|nim|no xau|eps|p ?/ ?e|p ?/ ?b|co tuc|gia co phieu"
                     r"|von hoa|luu chuyen tien|dong tien|hang ton kho|gia von"), UNSUPPORTED,
                  "chỉ số chưa có trong danh mục (EPS, EBITDA, dòng tiền, P/E, nợ xấu…)"),
    # --- lớp 1 -------------------------------------------------------------------
    MetricPattern(_p(r"loi nhuan gop|lai gop"), "gross_profit"),
    MetricPattern(_p(r"(?:loi nhuan sau thue|lnst|lai rong|loi nhuan|lai)(?: thuoc| cua| danh cho)?"
                     r"(?: co dong)? (?:cong ty me|cty me|me)"), "npat_parent"),
    MetricPattern(_p(r"loi nhuan sau thue|lnst|lai sau thue"), "npat"),
    MetricPattern(_p(r"loi nhuan rong|lai rong|loi nhuan|lai"), AMBIG_PROFIT),
    MetricPattern(_p(r"doanh thu thuan"), "net_revenue"),
    MetricPattern(_p(r"doanh thu(?: ban hang)?(?: va cung cap dich vu)?|doanh so"), "net_revenue",
                  assumption="hiểu 'doanh thu' là doanh thu thuần (B02-DN mã 10)"),
)

# Từ viết tắt chỉ khớp trên văn bản gốc **viết hoa** (tránh "tôi" → TOI).
CASE_SENSITIVE_METRICS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![A-Za-z])TOI(?![A-Za-z])"), "bank_toi"),
)

AMBIGUITIES = {
    AMBIG_PROFIT: {
        "default": "npat_parent",
        "candidates": ("npat_parent", "npat", "gross_profit"),
        "assumption": "hiểu 'lợi nhuận' là LNST của cổ đông công ty mẹ (mã 61)",
        "question": "Bạn muốn xem loại lợi nhuận nào: LNST cổ đông công ty mẹ, LNST toàn bộ hay lợi nhuận gộp?",
    },
    AMBIG_MARGIN: {
        "default": None,  # không có mặc định hợp lý → luôn hỏi làm rõ
        "candidates": ("gross_margin", "net_margin"),
        "assumption": None,
        "question": "Bạn muốn xem biên lợi nhuận gộp hay biên lợi nhuận ròng?",
    },
}

# --- mã / nhóm mã -------------------------------------------------------------
TICKER_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{2})(?![A-Za-z0-9])")
NOT_TICKERS = frozenset({
    "ROE", "ROA", "TTM", "YOY", "QOQ", "NII", "TOI", "EPS", "VND", "CIR", "NIM", "FCF", "BCTC", "USD",
    "HOSE", "HNX", "DTT", "CSH", "LNG", "BĐS", "CEO", "GDP", "ETF", "IPO", "LDR", "CAR", "NPL",
    "III", "VII", "XII", "XIV", "XIII",  # số La Mã (quý III, mục VII…)
})
UNIVERSE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_p(r"(?:cac |nhom |nhung )?ngan hang|nhom bank"), "bank"),
    (_p(r"(?:cac |nhom )?(?:doanh nghiep|cong ty) phi tai chinh"), "non_financial"),
    (_p(r"vn30|vn 30|tat ca(?: cac)?(?: ma| cong ty| doanh nghiep| co phieu)?|toan bo(?: cac)?(?: ma)?"
        r"|cac ma|cac cong ty|cac doanh nghiep|nhung cong ty|nhung doanh nghiep|cac co phieu"
        r"|cong ty nao|doanh nghiep nao|ma nao|co phieu nao"), "all"),
)

# --- kỳ -----------------------------------------------------------------------
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "mot": 1, "nhat": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4}
_Q = r"(iv|i{1,3}|[1-4]|mot|nhat|hai|ba|bon|tu)"
QUARTER_YEAR_RE = _p(rf"(?:quy|q)\s*{_Q}\s*(?:/|-|\s)\s*(?:nam\s*)?(\d{{4}})")
YEAR_QUARTER_RE = _p(r"(\d{4})\s*[-/ ]?\s*q([1-4])")
QUARTER_ONLY_RE = _p(rf"(?:quy|q)\s*{_Q}")
MONTHS_WORDS = {"ba": 3, "sau": 6, "chin": 9, "muoi hai": 12}
YTD_MONTHS_RE = _p(r"(3|6|9|12|ba|sau|chin|muoi hai)\s*thang(?:\s*dau)?(?:\s*nam)?(?:\s*(?:nam\s*)?(\d{4}))?")
HALF_YEAR_RE = _p(r"(?:nua dau nam|ban nien|6 thang dau nam)(?:\s*(?:nam\s*)?(\d{4}))?")
YTD_WORD_RE = _p(r"luy ke(?: tu dau nam)?(?: den)?|tu dau nam(?: den)?")
TTM_RE = _p(r"(?:4|bon) quy (?:gan nhat|gan day|lien tiep gan nhat)|12 thang (?:gan nhat|gan day|qua)|ttm"
            r"|(?:4|bon) quy (?:lien tiep )?(?:tinh )?den")
YEAR_RE = _p(r"(?:ca |trong |cua )?nam (?:tai chinh )?(\d{4})")
BARE_YEAR_RE = _p(r"((?:19|20)\d{2})")
LATEST_RE = _p(r"(?:quy |ky )?(?:gan nhat|moi nhat|hien tai|hien nay|vua qua|vua roi|gan day nhat)")

# --- phép so sánh --------------------------------------------------------------
QOQ_RE = _p(r"so voi quy (?:lien )?truoc(?: do)?|qoq|quy truoc")
YOY_RE = _p(r"so voi cung ky(?: nam (?:truoc|ngoai))?|cung ky(?: nam (?:truoc|ngoai))?|yoy"
            r"|so voi (?:nam|ky) (?:truoc|ngoai)")
CHANGE_RE = _p(r"tang truong|tang (?:bao nhieu|them|hay giam)|giam bao nhieu|thay doi|bien dong|tang giam"
               r"|tang hay giam")
PP_RE = re.compile(r"diem (?:phan tram|%)|(?<![a-z])pp(?![a-z])|percentage point")
PERCENT_WORD_RE = re.compile(r"%|phan tram")

# --- xếp hạng / lọc ------------------------------------------------------------
TOP_N_RE = _p(r"top\s*(\d+)|(\d+)\s*(?:ma|cong ty|doanh nghiep|ngan hang|co phieu|dn)")
DESC_RE = _p(r"cao nhat|lon nhat|nhieu nhat|dan dau|tot nhat|manh nhat|top")
ASC_RE = _p(r"thap nhat|nho nhat|it nhat|kem nhat|yeu nhat|cuoi bang")
RANK_ALL_RE = _p(r"xep hang|sap xep")

_COMP_WORDS = (
    ("khong vuot qua", "<="), ("khong qua", "<="), ("toi da", "<="), ("<=", "<="),
    ("khong duoi", ">="), ("it nhat", ">="), ("toi thieu", ">="), (">=", ">="), ("tu", ">="),
    ("vuot qua", ">"), ("vuot", ">"), ("lon hon", ">"), ("cao hon", ">"), ("tren", ">"), (">", ">"),
    ("nho hon", "<"), ("thap hon", "<"), ("duoi", "<"), ("<", "<"),
)
COMP_OPS = dict(_COMP_WORDS)
COMP_RE = re.compile(
    r"(?<![a-z0-9])(?P<op>" + "|".join(re.escape(w) for w, _ in _COMP_WORDS) + r")\s*"
    r"(?P<num>-?\d+(?:[.,]\d+)*)\s*"
    r"(?P<unit>%|phan tram|nghin ty|ngan ty|ty(?: dong)?|trieu(?: dong)?|lan)?(?![a-z0-9])"
)
SIGN_RE = _p(r"(?:bi |co (?:gia tri )?)?(am|duong)")
SCREEN_CUE_RE = _p(r"nao|nhung|loc|liet ke")
