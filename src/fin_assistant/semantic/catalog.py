"""Danh mục trường gốc (lớp 1) và định nghĩa chỉ số của bản pilot.

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

FLOW = "flow"
STOCK = "stock"

CONSOLIDATED = "consolidated"
SEPARATE = "separate"
SCOPES = frozenset({CONSOLIDATED, SEPARATE})


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
            "IS.NET_REVENUE",
            "Doanh thu thuần về bán hàng và cung cấp dịch vụ",
            FLOW, "VND", frozenset({NON_FINANCIAL}),
            {"TT200/B02-DN": "Mã số 10", "TT99/B02-DN": "Mã số 10"},
        ),
        ItemDef(
            "IS.NPAT",
            "Lợi nhuận sau thuế thu nhập doanh nghiệp",
            FLOW, "VND", GROUPS,
            {"TT200/B02-DN": "Mã số 60", "TT99/B02-DN": "Mã số 60", "TCTD/B03": "Mục XIII"},
        ),
        ItemDef(
            "IS.NPAT_PARENT",
            "Lợi nhuận sau thuế của cổ đông công ty mẹ",
            FLOW, "VND", GROUPS,
            {"TT202/B02-DN/HN": "Mã số 61 (TT43/2026: giữ nguyên)", "BCTC riêng": "= Mã số 60",
             "TCTD/B03-HN": "XIII − XIV (suy ra; không có dòng riêng)"},
        ),
        ItemDef(
            "BS.EQUITY_TOTAL",
            "Vốn chủ sở hữu (gồm lợi ích cổ đông không kiểm soát)",
            STOCK, "VND", GROUPS,
            {"TT200/B01-DN": "Mã số 400", "TT99/B01-DN": "Mã số 400"},
        ),
        ItemDef(
            "BS.NCI",
            "Lợi ích cổ đông không kiểm soát",
            STOCK, "VND", GROUPS,
            {"TT202/B01-DN/HN": "Mã số 429 (TT43/2026: giữ nguyên)", "BCTC riêng": "không có (= 0)"},
        ),
        ItemDef(
            "BS.EQUITY_PARENT",
            "Vốn chủ sở hữu thuộc cổ đông công ty mẹ",
            STOCK, "VND", GROUPS,
            {"Doanh nghiệp (HN)": "Mã số 400 − Mã số 429", "TCTD/B02": "Vốn chủ sở hữu − lợi ích CĐ không kiểm soát (nếu có)"},
        ),
        ItemDef(
            "IS.BANK_INTEREST_INCOME",
            "Thu nhập lãi và các khoản thu nhập tương tự",
            FLOW, "VND", frozenset({BANK}),
            {"TCTD/B03": "Dòng 1"},
        ),
        ItemDef(
            "IS.BANK_NII",
            "Thu nhập lãi thuần",
            FLOW, "VND", frozenset({BANK}),
            {"TCTD/B03": "Mục I"},
        ),
        ItemDef(
            "IS.BANK_TOI",
            "Tổng thu nhập hoạt động (tổng mục I–VII)",
            FLOW, "VND", frozenset({BANK}),
            {"TCTD/B03": "I + II + … + VII (= IX + VIII); không có dòng riêng — TV1 tính, ghi derived_from"},
        ),
    )
}


@dataclass(frozen=True)
class MetricDef:
    """Chỉ số được ``get_metric`` hỗ trợ."""

    id: str
    name_vi: str
    layer: str  # base | derived
    groups: frozenset[str]
    unit: str
    formula_vi: str
    item_code: str | None = None  # chỉ với chỉ số lớp 1 (base)
    transforms: frozenset[str] = frozenset()


METRICS: dict[str, MetricDef] = {
    m.id: m
    for m in (
        MetricDef(
            "net_revenue", "Doanh thu thuần", "base", frozenset({NON_FINANCIAL}), "VND",
            "Doanh thu thuần quý đơn lẻ (B02-DN mã 10)",
            item_code="IS.NET_REVENUE", transforms=frozenset({"yoy"}),
        ),
        MetricDef(
            "npat_parent", "LNST cổ đông công ty mẹ", "base", GROUPS, "VND",
            "LNST của cổ đông công ty mẹ, quý đơn lẻ",
            item_code="IS.NPAT_PARENT", transforms=frozenset({"yoy"}),
        ),
        MetricDef(
            "equity_parent", "Vốn chủ sở hữu công ty mẹ", "base", GROUPS, "VND",
            "VCSH thuộc cổ đông công ty mẹ, số dư cuối quý",
            item_code="BS.EQUITY_PARENT", transforms=frozenset({"yoy"}),
        ),
        MetricDef(
            "bank_interest_income", "Thu nhập lãi và các khoản thu nhập tương tự", "base",
            frozenset({BANK}), "VND", "Thu nhập lãi và các khoản tương tự, quý đơn lẻ",
            item_code="IS.BANK_INTEREST_INCOME", transforms=frozenset({"yoy"}),
        ),
        MetricDef(
            "bank_nii", "Thu nhập lãi thuần", "base", frozenset({BANK}), "VND",
            "Thu nhập lãi thuần, quý đơn lẻ",
            item_code="IS.BANK_NII", transforms=frozenset({"yoy"}),
        ),
        MetricDef(
            "bank_toi", "Tổng thu nhập hoạt động", "base", frozenset({BANK}), "VND",
            "Tổng thu nhập hoạt động (mục I–VII), quý đơn lẻ",
            item_code="IS.BANK_TOI", transforms=frozenset({"yoy"}),
        ),
        MetricDef(
            "roe_ttm", "ROE 4 quý gần nhất (TTM)", "derived", GROUPS, "ratio",
            "ROE_TTM(t) = Σ LNST cổ đông mẹ (t−3..t) / VCSH cổ đông mẹ bình quân",
        ),
    )
}

# Các chỉ số mà khi hỏi cho ngân hàng phải hỏi làm rõ: Báo cáo kết quả hoạt động của TCTD
# (mẫu B03/TCTD theo QĐ16/2007, sửa đổi bởi TT49/2014, TT22/2017, TT27/2021) không có dòng "Doanh thu thuần".
BANK_CLARIFY_METRICS = frozenset({"net_revenue"})
BANK_REVENUE_CANDIDATES = ("bank_nii", "bank_toi", "bank_interest_income")
