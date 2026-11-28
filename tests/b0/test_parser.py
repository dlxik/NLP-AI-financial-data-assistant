"""Bộ phân tích quy tắc B0: câu tiếng Việt → Query (tách mã, kỳ, chỉ số, phép toán)."""

import pytest

from fin_assistant.b0 import B0Parser, normalize, parse_number
from fin_assistant.semantic import Status

from .conftest import QDATE


# ================================================================ chuẩn hóa
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Doanh thu Quý 3/2024 của VNM", "doanh thu quy 3/2024 cua vnm"),
        ("Lợi nhuận   ĐẦU tư", "loi nhuan dau tu"),
        ("hỏi lại về lãi", "hoi laj ve lai"),          # "lại" ≠ "lãi"
        ("Tôi muốn biết TOI", "toj muon biet toi"),       # "tôi" ≠ TOI
        ("Q3 – 2024", "q3 - 2024"),
    ],
)
def test_normalize(text, expected):
    assert normalize(text) == expected


@pytest.mark.parametrize(
    "raw, value",
    [("15", 15), ("15,5", 15.5), ("15.5", 15.5), ("1.000", 1000), ("1.234,5", 1234.5),
     ("1,234,567", 1234567), ("-2,5", -2.5), ("10.000.000", 10_000_000)],
)
def test_parse_number(raw, value):
    assert parse_number(raw) == pytest.approx(value)


# ================================================================ câu → truy vấn
def q(store, question, policy="default", qdate=QDATE):
    return B0Parser(store, policy=policy).parse(question, qdate)


CASES = [
    # (câu hỏi, các trường kỳ vọng của Query)
    ("Doanh thu thuần quý 3/2024 của AAA là bao nhiêu?",
     dict(op="lookup", metric="net_revenue", tickers=("AAA",), period="2024Q3", transform=None)),
    ("doanh thu quy 3 nam 2024 cua aaa tang bao nhieu so voi cung ky?",
     dict(metric="net_revenue", tickers=("AAA",), period="2024Q3", transform="yoy")),
    ("Doanh thu Q3 2024 của AAA so với quý trước",
     dict(period="2024Q3", transform="qoq")),
    ("Doanh thu quý III/2024 của AAA", dict(period="2024Q3")),
    ("Doanh thu quý tư năm 2024 của AAA", dict(period="2024Q4")),
    ("Doanh thu 2024Q2 của AAA", dict(period="2024Q2")),
    ("Doanh thu 9 tháng đầu năm 2024 của AAA tăng bao nhiêu so với cùng kỳ?",
     dict(period="2024Q3", transform="ytd_yoy")),
    ("Doanh thu lũy kế quý 3/2024 của AAA", dict(period="2024Q3", transform="ytd")),
    ("Doanh thu 6 tháng đầu năm 2024 của AAA", dict(period="2024Q2", transform="ytd")),
    ("Doanh thu nửa đầu năm 2024 của AAA", dict(period="2024Q2", transform="ytd")),
    ("Doanh thu năm 2024 của AAA", dict(period="2024Q4", transform="ytd")),
    ("Doanh thu 4 quý gần nhất của AAA", dict(period="latest", transform="ttm")),
    ("Doanh thu Q3/2024 so với Q3/2023 của AAA", dict(period="2024Q3", transform="yoy")),
    ("Doanh thu Q3/2024 so với Q2/2024 của AAA", dict(period="2024Q3", transform="qoq")),
    ("Doanh thu quý gần nhất của AAA", dict(period="latest", transform=None)),
    ("Lợi nhuận gộp của AAA quý 2/2024 so với quý trước", dict(metric="gross_profit", transform="qoq")),
    ("LNST công ty mẹ của AAA quý 3/2024", dict(metric="npat_parent")),
    ("Lợi nhuận sau thuế của AAA quý 3/2024", dict(metric="npat")),
    ("Biên lợi nhuận gộp của AAA quý 3/2024", dict(metric="gross_margin", transform=None)),
    ("Biên lợi nhuận ròng 9 tháng 2024 của AAA", dict(metric="net_margin", transform="ytd")),
    ("Biên lợi nhuận gộp của AAA quý 3/2024 thay đổi bao nhiêu điểm phần trăm so với cùng kỳ?",
     dict(metric="gross_margin", transform="yoy_pp")),
    ("ROE của AAA quý 3/2024", dict(metric="roe_ttm", period="2024Q3", transform=None)),
    ("ROE năm 2024 của AAA", dict(metric="roe_ttm", period="2024Q4", transform=None)),
    ("roe 4 quý gần nhất của aaa", dict(metric="roe_ttm", period="latest", tickers=("AAA",))),
    ("ROA của Ngân hàng Nam Hà quý 3/2024", dict(metric="roa_ttm", tickers=("NHA",))),
    ("Tổng tài sản của NHA quý 3/2024", dict(metric="total_assets")),
    ("Tổng tài sản của AAA 6 tháng đầu năm 2024", dict(metric="total_assets", period="2024Q2", transform=None)),
    ("Nợ phải trả của AAA quý 3/2024", dict(metric="total_liabilities")),
    ("Nợ phải trả trên vốn chủ sở hữu của AAA quý 3/2024", dict(metric="liabilities_to_equity")),
    ("Vốn chủ sở hữu của Alpha Corp quý 3/2024", dict(metric="equity_parent", tickers=("AAA",))),
    ("Thu nhập lãi thuần của NHA quý 3/2024", dict(metric="bank_nii")),
    ("TOI của NHA quý 3/2024", dict(metric="bank_toi")),
    ("Tổng thu nhập hoạt động của NHA quý 3/2024", dict(metric="bank_toi")),
    ("Thu nhập lãi của NHA quý 3/2024", dict(metric="bank_interest_income")),
    ("So sánh ROE của AAA và NHA", dict(op="lookup", tickers=("AAA", "NHA"), period="latest")),
    ("ROE các ngân hàng quý 3/2024", dict(op="lookup", universe="bank", tickers=())),
    # xếp hạng
    ("Công ty nào có ROE cao nhất quý 3/2024?", dict(op="rank", order="desc", top_n=1, universe="all")),
    ("Top 3 công ty có doanh thu lớn nhất năm 2024", dict(op="rank", top_n=3, transform="ytd")),
    ("Ngân hàng nào có ROE thấp nhất quý 3/2024", dict(op="rank", order="asc", universe="bank")),
    ("Xếp hạng ROE các công ty quý 3/2024", dict(op="rank", top_n=None)),
    ("Top 2 doanh nghiệp tăng trưởng doanh thu cao nhất quý 3/2024",
     dict(op="rank", top_n=2, transform="yoy")),
    # lọc
    ("Những công ty nào có ROE trên 15% quý 3/2024?", dict(op="screen", cmp=">", threshold=0.15)),
    ("Công ty nào có ROE ít nhất 15,5% quý 3/2024?", dict(op="screen", cmp=">=", threshold=0.155)),
    ("Doanh nghiệp nào có doanh thu quý 3/2024 trên 1.000 tỷ đồng?",
     dict(op="screen", cmp=">", threshold=1e12)),
    ("Công ty nào có doanh thu quý 3/2024 dưới 1,2 nghìn tỷ?", dict(op="screen", cmp="<", threshold=1.2e12)),
    ("Công ty nào có tăng trưởng doanh thu quý 3/2024 trên 20%?",
     dict(op="screen", transform="yoy", threshold=0.2)),
    ("Công ty nào có nợ phải trả trên vốn chủ không quá 1 lần quý 3/2024?",
     dict(op="screen", metric="liabilities_to_equity", cmp="<=", threshold=1.0)),
    ("AAA có ROE trên 15% quý 3/2024 không?", dict(op="screen", tickers=("AAA",))),
    ("Công ty nào có lợi nhuận âm quý 3/2024?", dict(op="screen", cmp="<", threshold=0.0)),
]


@pytest.mark.parametrize("question, expected", CASES, ids=[c[0][:50] for c in CASES])
def test_parse_cases(store, question, expected):
    res = q(store, question)
    assert res.status is None, res.reason
    data = res.query.to_dict()
    data["tickers"] = tuple(data["tickers"])
    for key, value in expected.items():
        if key == "threshold":
            assert data[key] == pytest.approx(value), question
        else:
            assert data[key] == value, (question, key, data[key])
    assert res.query.as_of == QDATE


# ================================================================ giả định công khai (chính sách 'default')
@pytest.mark.parametrize(
    "question, fragment",
    [
        ("Doanh thu quý 3/2024 của AAA", "doanh thu thuần"),
        ("Lợi nhuận của AAA quý 3/2024", "cổ đông công ty mẹ"),
        ("Doanh thu của AAA", "kỳ gần nhất"),
        ("Doanh thu quý 3 của AAA", "quý 3/2024"),
        ("Doanh thu quý 3/2024 của AAA tăng trưởng thế nào", "cùng kỳ năm trước"),
        ("ROE năm 2024 của AAA", "TTM tại Q4/2024"),
        ("Hệ số nợ của AAA quý 3/2024", "không phải nợ vay"),
        ("Biên lợi nhuận gộp quý 3/2024 của AAA tăng bao nhiêu %", "điểm phần trăm"),
        ("Công ty nào có ROE trên 15 quý 3/2024", "15%"),
        ("Công ty nào có doanh thu quý 3/2024 trên 500", "500 tỷ đồng"),
        ("Công ty nào có ROE cao nhất quý 3/2024", "ROE tính trên 4 quý"),
        ("Top 3 doanh thu quý 3/2024", "toàn bộ các mã"),
    ],
)
def test_default_assumptions_are_disclosed(store, question, fragment):
    res = q(store, question)
    assert res.query is not None, res.reason
    assert any(fragment in a for a in res.assumptions), res.assumptions


def test_quarter_without_year_uses_latest_published(store):
    res = q(store, "Doanh thu quý 4 của AAA", qdate="2024-11-15")  # Q4/2024 chưa công bố
    assert res.query.period == "2023Q4"


def test_quarter_without_year_and_no_data_falls_back_to_date(store):
    res = q(store, "Doanh thu quý 2 của NEW", qdate="2024-11-15")
    assert res.query.period == "2024Q2"


# ================================================================ mơ hồ
def test_profit_ambiguity_policies(store):
    default = q(store, "Lợi nhuận của AAA quý 3/2024")
    assert default.query.metric == "npat_parent"
    clarify = q(store, "Lợi nhuận của AAA quý 3/2024", policy="clarify")
    assert clarify.status is Status.NEEDS_CLARIFICATION
    assert clarify.candidates == ("npat_parent", "npat", "gross_profit")


def test_margin_ambiguity_always_clarifies(store):
    res = q(store, "Biên lợi nhuận của AAA quý 3/2024")
    assert res.status is Status.NEEDS_CLARIFICATION
    assert res.candidates == ("gross_margin", "net_margin")


def test_clear_question_not_clarified_under_clarify_policy(store):
    """Không hỏi thừa trên câu đã rõ nghĩa (RQ3)."""
    res = q(store, "Doanh thu thuần quý 3/2024 của AAA", policy="clarify")
    assert res.status is None and res.query.metric == "net_revenue"


def test_invalid_policy(store):
    with pytest.raises(ValueError):
        B0Parser(store, policy="guess")


# ================================================================ từ chối có lý do
@pytest.mark.parametrize(
    "question, fragment",
    [
        ("EPS của AAA năm 2024", "chưa có trong danh mục"),
        ("Lợi nhuận trước thuế của AAA quý 3/2024", "lợi nhuận trước thuế"),
        ("Doanh thu tài chính của AAA quý 3/2024", "tài chính"),
        ("Nợ vay của AAA quý 3/2024", "nợ vay"),
        ("Doanh thu và lợi nhuận gộp của AAA quý 3/2024", "một chỉ số"),
        ("Thời tiết hôm nay thế nào?", "không nhận diện được chỉ số"),
        ("Doanh thu quý 3/2024 là bao nhiêu?", "không xác định được mã"),
        ("Doanh thu Q3/2024 so với Q1/2023 của AAA", "hai kỳ"),
        ("Doanh thu lũy kế Q3/2024 so với Q2/2024 của AAA", "cùng kỳ năm trước"),
        ("ROE 9 tháng 2024 của AAA", "TTM"),
        ("Tổng tài sản 4 quý gần nhất của AAA", "số dư"),
        ("Nợ phải trả trên vốn chủ của AAA quý 3/2024 tăng bao nhiêu so với cùng kỳ", "chưa hỗ trợ"),
        ("Doanh thu 9 tháng 2024 so với quý trước của AAA", "cùng kỳ năm trước"),
    ],
)
def test_unsupported_questions_abstain(store, question, fragment):
    res = q(store, question)
    assert res.query is None
    assert res.status is Status.NOT_APPLICABLE
    assert fragment in res.reason


def test_unknown_uppercase_ticker_is_kept_for_out_of_scope_refusal(store):
    res = q(store, "ROE của XYZ quý 3/2024")
    assert res.query.tickers == ("XYZ",)


def test_uppercase_words_are_not_tickers(store):
    res = q(store, "ROE và TTM của AAA quý 3/2024")
    assert res.query.tickers == ("AAA",)


def test_lowercase_common_word_not_taken_as_ticker_in_cased_question(store):
    """'nhà' trong câu có chữ hoa không bị hiểu là mã NHA."""
    res = q(store, "Nhà đầu tư hỏi: doanh thu quý 3/2024 của AAA")
    assert res.query.tickers == ("AAA",)
