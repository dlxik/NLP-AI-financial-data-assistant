"""Danh mục trường gốc (lớp 1), chỉ số (lớp 1–2) và phép biến đổi (lớp 3) — Semantic Layer v1.0.

Mã nội bộ (``item_code``) là **mã chuẩn hóa** do TV1 gán khi nạp dữ liệu, độc lập với số hiệu
dòng của từng thông tư — nhờ đó thư viện không phải đổi khi mẫu biểu thay đổi
(TT200/2014 → TT99/2025 với BCTC riêng, TT202/2014 → TT43/2026 với BCTC hợp nhất, từ năm tài chính
2026; QĐ16/2007 sửa đổi bởi TT49/2014, TT22/2017, TT27/2021 với tổ chức tín dụng).
Cột ``template_refs`` chỉ để truy vết; bảng ánh xạ đầy đủ nằm ở
``docs/specs/danh-muc-chi-so-de-xuat.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

NON_FINANCIAL = "non_financial"
BANK = "bank"
GROUPS = frozenset({NON_FINANCIAL, BANK})
NF_ONLY = frozenset({NON_FINANCIAL})
BANK_ONLY = frozenset({BANK})

FLOW = "flow"
STOCK = "stock"

CONSOLIDATED = "consolidated"
SEPARATE = "separate"
SCOPES = frozenset({CONSOLIDATED, SEPARATE})

# Cửa sổ thời gian (lớp 3)
WINDOW_Q = "q"      # quý đơn lẻ (flow) / số dư cuối quý (stock)
WINDOW_YTD = "ytd"  # lũy kế từ đầu năm tài chính
WINDOW_TTM = "ttm"  # 4 quý gần nhất
WINDOWS = frozenset({WINDOW_Q, WINDOW_YTD, WINDOW_TTM})

# Phép so sánh (lớp 3)
CHANGE_YOY = "yoy"
CHANGE_QOQ = "qoq"
CHANGES = frozenset({CHANGE_YOY, CHANGE_QOQ})
CHANGE_LAG = {CHANGE_YOY: -4, CHANGE_QOQ: -1}


@dataclass(frozen=True)
class ItemDef:
    """Trường gốc trên BCTC (lớp 1)."""

    code: str
    name_vi: str
    item_type: str  # flow | stock
    unit: str
    groups: frozenset[str]
    template_refs: dict[str, str] = field(default_factory=dict)


ITEMS: dict[str, ItemDef] = {
    item.code: item
    for item in (
        ItemDef(
            "IS.NET_REVENUE", "Doanh thu thuần về bán hàng và cung cấp dịch vụ", FLOW, "VND", NF_ONLY,
            {"TT200/B02-DN": "Mã số 10", "TT99/B02-DN": "Mã số 10"},
        ),
        ItemDef(
            "IS.GROSS_PROFIT", "Lợi nhuận gộp về bán hàng và cung cấp dịch vụ", FLOW, "VND", NF_ONLY,
            {"TT200/B02-DN": "Mã số 20", "TT99/B02-DN": "Mã số 20"},
        ),
        ItemDef(
            "IS.NPAT", "Lợi nhuận sau thuế thu nhập doanh nghiệp", FLOW, "VND", GROUPS,
            {"TT200/B02-DN": "Mã số 60", "TT99/B02-DN": "Mã số 60", "TCTD/B03": "Mục XIII"},
        ),
        ItemDef(
            "IS.NPAT_PARENT", "Lợi nhuận sau thuế của cổ đông công ty mẹ", FLOW, "VND", GROUPS,
            {"TT202/B02-DN/HN": "Mã số 61 (TT43/2026: giữ nguyên)", "BCTC riêng": "= Mã số 60",
             "TCTD/B03-HN": "XIII − XIV (suy ra; không có dòng riêng)"},
        ),
        ItemDef(
            "BS.TOTAL_ASSETS", "Tổng tài sản", STOCK, "VND", GROUPS,
            {"TT200/B01-DN": "Mã số 270", "TT99/B01-DN": "Mã số 280 (270 nay là 'Tài sản dài hạn khác')",
             "TCTD/B02": "Tổng tài sản"},
        ),
        ItemDef(
            "BS.TOTAL_LIABILITIES", "Nợ phải trả", STOCK, "VND", NF_ONLY,
            {"TT200/B01-DN": "Mã số 300", "TT99/B01-DN": "Mã số 300"},
        ),
        ItemDef(
            "BS.EQUITY_TOTAL", "Vốn chủ sở hữu (gồm lợi ích cổ đông không kiểm soát)", STOCK, "VND", GROUPS,
            {"TT200/B01-DN": "Mã số 400", "TT99/B01-DN": "Mã số 400"},
        ),
        ItemDef(
            "BS.NCI", "Lợi ích cổ đông không kiểm soát", STOCK, "VND", GROUPS,
            {"TT202/B01-DN/HN": "Mã số 429 (TT43/2026: giữ nguyên)", "BCTC riêng": "không có (= 0)"},
        ),
        ItemDef(
            "BS.EQUITY_PARENT", "Vốn chủ sở hữu thuộc cổ đông công ty mẹ", STOCK, "VND", GROUPS,
            {"Doanh nghiệp (HN)": "Mã số 400 − Mã số 429",
             "TCTD/B02": "Vốn chủ sở hữu − lợi ích CĐ không kiểm soát (nếu có)"},
        ),
        ItemDef(
            "IS.BANK_INTEREST_INCOME", "Thu nhập lãi và các khoản thu nhập tương tự", FLOW, "VND", BANK_ONLY,
            {"TCTD/B03": "Dòng 1"},
        ),
        ItemDef(
            "IS.BANK_NII", "Thu nhập lãi thuần", FLOW, "VND", BANK_ONLY,
            {"TCTD/B03": "Mục I"},
        ),
        ItemDef(
            "IS.BANK_TOI", "Tổng thu nhập hoạt động (tổng mục I–VII)", FLOW, "VND", BANK_ONLY,
            {"TCTD/B03": "I + II + … + VII (= IX + VIII); không có dòng riêng — TV1 tính, ghi derived_from"},
        ),
    )
}


@dataclass(frozen=True)
class MetricDef:
    """Chỉ số được ``get_metric`` hỗ trợ.

    ``kind``:
        - ``flow`` / ``stock``: chỉ số lớp 1 đọc thẳng một trường gốc (``item_code``).
        - ``ratio_window``: tỷ số hai chỉ số flow trên cùng cửa sổ (biên lợi nhuận).
        - ``ratio_ttm``: tỷ số flow TTM / stock bình quân (ROE, ROA) — cửa sổ cố định.
        - ``ratio_stock``: tỷ số hai số dư cuối quý.
    """

    id: str
    name_vi: str
    layer: str  # base | derived
    kind: str
    groups: frozenset[str]
    unit: str  # VND | ratio | times
    formula_vi: str
    item_code: str | None = None
    numerator: str | None = None  # id chỉ số / item_code tử số (derived)
    denominator: str | None = None
    official: bool = True  # thuộc danh mục 14 chỉ số chính thức

    @property
    def windows(self) -> frozenset[str]:
        if self.kind in (FLOW, "ratio_window"):
            return WINDOWS
        return frozenset({WINDOW_Q})

    @property
    def changes(self) -> frozenset[str]:
        """Phép so sánh hỗ trợ: tăng trưởng % (VND) hoặc chênh lệch điểm % (ratio)."""
        if self.unit in ("VND", "ratio"):
            return CHANGES
        return frozenset()


METRICS: dict[str, MetricDef] = {
    m.id: m
    for m in (
        # ---------------- lớp 1: trường gốc ----------------
        MetricDef("net_revenue", "Doanh thu thuần", "base", FLOW, NF_ONLY, "VND",
                  "Doanh thu thuần (B02-DN mã 10)", item_code="IS.NET_REVENUE"),
        MetricDef("gross_profit", "Lợi nhuận gộp", "base", FLOW, NF_ONLY, "VND",
                  "Lợi nhuận gộp (B02-DN mã 20)", item_code="IS.GROSS_PROFIT"),
        MetricDef("npat", "Lợi nhuận sau thuế", "base", FLOW, GROUPS, "VND",
                  "LNST toàn bộ (B02-DN mã 60; TCTD mục XIII)", item_code="IS.NPAT"),
        MetricDef("npat_parent", "LNST cổ đông công ty mẹ", "base", FLOW, GROUPS, "VND",
                  "LNST của cổ đông công ty mẹ (B02-DN/HN mã 61)", item_code="IS.NPAT_PARENT"),
        MetricDef("total_assets", "Tổng tài sản", "base", STOCK, GROUPS, "VND",
                  "Tổng tài sản, số dư cuối quý", item_code="BS.TOTAL_ASSETS"),
        MetricDef("total_liabilities", "Nợ phải trả", "base", STOCK, NF_ONLY, "VND",
                  "Nợ phải trả (B01-DN mã 300), số dư cuối quý", item_code="BS.TOTAL_LIABILITIES"),
        MetricDef("equity_parent", "Vốn chủ sở hữu công ty mẹ", "base", STOCK, GROUPS, "VND",
                  "VCSH thuộc cổ đông công ty mẹ (400 − 429), số dư cuối quý", item_code="BS.EQUITY_PARENT"),
        MetricDef("bank_nii", "Thu nhập lãi thuần", "base", FLOW, BANK_ONLY, "VND",
                  "Thu nhập lãi thuần (B03/TCTD mục I)", item_code="IS.BANK_NII"),
        MetricDef("bank_toi", "Tổng thu nhập hoạt động", "base", FLOW, BANK_ONLY, "VND",
                  "Tổng thu nhập hoạt động (B03/TCTD mục I–VII)", item_code="IS.BANK_TOI"),
        MetricDef("bank_interest_income", "Thu nhập lãi và các khoản thu nhập tương tự", "base", FLOW,
                  BANK_ONLY, "VND", "Thu nhập lãi và các khoản tương tự (B03/TCTD dòng 1)",
                  item_code="IS.BANK_INTEREST_INCOME", official=False),
        # ---------------- lớp 2: chỉ số suy ra ----------------
        MetricDef("gross_margin", "Biên lợi nhuận gộp", "derived", "ratio_window", NF_ONLY, "ratio",
                  "Lợi nhuận gộp / Doanh thu thuần (cùng cửa sổ)",
                  numerator="gross_profit", denominator="net_revenue"),
        MetricDef("net_margin", "Biên lợi nhuận ròng", "derived", "ratio_window", NF_ONLY, "ratio",
                  "LNST toàn bộ (mã 60) / Doanh thu thuần (cùng cửa sổ)",
                  numerator="npat", denominator="net_revenue"),
        MetricDef("roe_ttm", "ROE 4 quý gần nhất (TTM)", "derived", "ratio_ttm", GROUPS, "ratio",
                  "Σ LNST cổ đông mẹ 4 quý / VCSH cổ đông mẹ bình quân",
                  numerator="npat_parent", denominator="equity_parent"),
        MetricDef("roa_ttm", "ROA 4 quý gần nhất (TTM)", "derived", "ratio_ttm", GROUPS, "ratio",
                  "Σ LNST toàn bộ 4 quý / Tổng tài sản bình quân",
                  numerator="npat", denominator="total_assets"),
        MetricDef("liabilities_to_equity", "Nợ phải trả trên vốn chủ sở hữu", "derived", "ratio_stock",
                  NF_ONLY, "times", "Nợ phải trả (mã 300) / VCSH (mã 400), cuối quý — không phải nợ vay/VCSH",
                  numerator="total_liabilities", denominator="BS.EQUITY_TOTAL"),
    )
}

OFFICIAL_METRICS = tuple(m for m in METRICS if METRICS[m].official)

# Các chỉ số mà khi hỏi cho ngân hàng phải hỏi làm rõ: Báo cáo kết quả hoạt động của TCTD
# (mẫu B03/TCTD theo QĐ16/2007, sửa đổi bởi TT49/2014, TT22/2017, TT27/2021) không có dòng "Doanh thu thuần".
BANK_CLARIFY_METRICS = frozenset({"net_revenue"})
BANK_REVENUE_CANDIDATES = ("bank_nii", "bank_toi", "bank_interest_income")


@dataclass(frozen=True)
class Transform:
    """Phép biến đổi lớp 3 = cửa sổ + (tùy chọn) phép so sánh.

    Cú pháp chuỗi: ``[ytd|ttm][_][yoy|qoq][_pp]``, ví dụ ``"yoy"``, ``"ytd"``, ``"ttm_yoy"``,
    ``"yoy_pp"``, ``"ytd_yoy_pp"``. ``None``/``""``/``"q"`` = quý đơn lẻ, không so sánh.
    """

    window: str = WINDOW_Q
    change: str | None = None
    pp: bool = False

    @property
    def name(self) -> str | None:
        parts = [p for p in (self.window if self.window != WINDOW_Q else None, self.change) if p]
        if self.pp:
            parts.append("pp")
        return "_".join(parts) or None


class TransformError(ValueError):
    """Phép biến đổi sai cú pháp hoặc không áp dụng cho chỉ số."""


def parse_transform(spec: str | None) -> Transform:
    if spec is None or spec in ("", WINDOW_Q):
        return Transform()
    tokens = spec.lower().split("_")
    window, change, pp = WINDOW_Q, None, False
    if tokens and tokens[0] in (WINDOW_YTD, WINDOW_TTM):
        window = tokens.pop(0)
    if tokens and tokens[0] in CHANGES:
        change = tokens.pop(0)
    if tokens and tokens[0] == "pp":
        pp = True
        tokens.pop(0)
    if tokens:
        raise TransformError(f"phép biến đổi không hợp lệ: {spec!r}")
    if pp and change is None:
        raise TransformError(f"'_pp' phải đi sau yoy/qoq: {spec!r}")
    return Transform(window, change, pp)


def check_transform(metric: MetricDef, t: Transform) -> None:
    """Ràng buộc kiểu giữa chỉ số và phép biến đổi (danh mục, mục 3)."""
    if t.window not in metric.windows:
        raise TransformError(
            f"cửa sổ {t.window!r} không áp dụng cho {metric.id!r} (hỗ trợ: {sorted(metric.windows)})"
        )
    if t.change is None:
        return
    if t.change not in metric.changes:
        raise TransformError(f"{metric.id!r} không hỗ trợ phép so sánh {t.change!r}")
    if metric.unit == "ratio" and not t.pp:
        raise TransformError(
            f"{metric.id!r} là tỷ lệ: dùng '{t.change}_pp' (chênh lệch điểm %), không dùng % tăng trưởng"
        )
    if metric.unit == "VND" and t.pp:
        raise TransformError(f"{metric.id!r} là giá trị tiền tệ: dùng '{t.change}' (% tăng trưởng), không dùng '_pp'")
    if t.window == WINDOW_YTD and t.change == CHANGE_QOQ:
        raise TransformError("lũy kế (ytd) chỉ so sánh với cùng kỳ năm trước (yoy), không so với quý trước")
