# Đặc tả Phương pháp B0 (không LLM)

| | |
|---|---|
| **Phiên bản** | v1.0 (Giai đoạn 2) |
| **Người phụ trách** | TV2 |
| **Mã nguồn** | [`src/fin_assistant/b0/`](../../src/fin_assistant/b0/); test: [`tests/b0/`](../../tests/b0/) |
| **Vai trò trong thí nghiệm** | Baseline quy tắc. So sánh B0 vs LLM trả lời câu hỏi "họ câu nào quy tắc đã đủ" (Đề cương, mục 6.2) |

## 1. Luồng xử lý

```
câu tiếng Việt ──► chuẩn hóa ──► bộ phân tích quy tắc ──► Query ──► bộ thực thi ──► semantic layer ──► câu trả lời
                  (bỏ dấu)      (mã, kỳ, chỉ số, phép)   (JSON)    (query.execute)   (get_metric…)    (kỳ cạnh số, giả định)
```

- **`Query`** ([query.py](../../src/fin_assistant/semantic/query.py)) là ngôn ngữ truy vấn **dùng chung** với phương pháp C. B0 sinh `Query` bằng quy tắc; C (GĐ3) sẽ để LLM sinh `Query` theo `Query.json_schema()`. Hai phương pháp chạy cùng một bộ thực thi nên chênh lệch kết quả giữa B0 và C chỉ đến từ **khâu hiểu câu**.
- B0 **không chứa công thức tài chính**. Mọi phép tính và quy tắc 4.3–4.4 đều nằm trong semantic layer.

## 2. Chuẩn hóa ([normalize.py](../../src/fin_assistant/b0/normalize.py))

- Chuẩn hóa NFC, chuyển chữ thường, bỏ dấu (đ → d), gộp khoảng trắng. B0 hiểu được cả câu gõ không dấu.
- Một số từ được **bảo vệ trước khi bỏ dấu** để không trùng thuật ngữ: "lại" ≠ "lãi", "tôi"/"tới" ≠ TOI.
- Số theo quy ước Việt Nam: `1.234,5` = 1234,5; `15,5` = 15,5; `1.000` = 1000.

## 3. Các thành phần được tách

Thứ tự tách là cố định. Đoạn đã khớp bị tiêu thụ để mẫu chung không khớp lại phần của mẫu cụ thể.

| Bước | Thành phần | Ví dụ nhận diện |
|---|---|---|
| 1 | **Mã** | Mã viết hoa (`VNM`); mã viết thường chỉ khi cả câu viết thường; tên gọi trong cột `aliases` của bảng công ty ("Vinamilk") |
| 2 | **Top-N, nhóm mã** | "top 5", "3 công ty"; "các ngân hàng" → `bank`; "VN30", "công ty nào" → `all` |
| 3 | **Kỳ** | "quý 3/2024", "Q3 2024", "quý III năm 2024", "quý tư", "2024Q3"; "9 tháng đầu năm", "6 tháng", "bán niên", "lũy kế"; "năm 2024"; "4 quý gần nhất", "TTM"; "gần nhất", "hiện nay" |
| 4 | **Điều kiện lọc** | "trên / lớn hơn / vượt", "ít nhất / tối thiểu / từ", "dưới / nhỏ hơn", "tối đa / không quá" + số + đơn vị (%, tỷ, nghìn tỷ, triệu, lần); "… nào … âm/dương" |
| 5 | **So sánh thời gian** | "so với quý trước", "QoQ"; "so với cùng kỳ", "YoY"; "tăng trưởng", "tăng bao nhiêu", "thay đổi"; "điểm phần trăm" |
| 6 | **Chỉ số** | Từ vựng trong [lexicon.py](../../src/fin_assistant/b0/lexicon.py), ánh xạ vào 14 chỉ số (mục 4) |
| 7 | **Xếp hạng** | "cao nhất / lớn nhất / dẫn đầu", "thấp nhất / nhỏ nhất", "xếp hạng / sắp xếp" |

**Ghép thành truy vấn:**
- Có điều kiện lọc → `screen`. Có từ xếp hạng hoặc top-N → `rank`. Còn lại → `lookup`.
- "Q3/2024 so với Q3/2023" được quy về `yoy`; "Q3/2024 so với Q2/2024" quy về `qoq`.
- `rank`/`screen` không nêu mã → xét toàn bộ danh mục (có ghi giả định).

## 4. Ánh xạ kỳ theo loại chỉ số

| Câu hỏi | Chỉ số flow (doanh thu, LN…) | Tỷ số flow (biên LN) | ROE/ROA (TTM) | Số dư (tài sản, nợ, VCSH) / nợ/VCSH |
|---|---|---|---|---|
| "quý 3/2024" | quý đơn lẻ Q3/2024 | quý Q3/2024 | TTM đến Q3/2024 (giả định) | cuối Q3/2024 |
| "9 tháng 2024", "lũy kế" | `ytd` @Q3 | `ytd` @Q3 | **từ chối** (chỉ có TTM) | cuối Q3 (giả định) |
| "năm 2024" | `ytd` @Q4 = cả năm (giả định) | `ytd` @Q4 | TTM @Q4 = ROE năm (giả định) | cuối năm (giả định) |
| "4 quý gần nhất" | `ttm` | `ttm` | TTM | **từ chối** |
| không nêu kỳ | kỳ gần nhất tại ngày hỏi (giả định) | ← | ← | ← |
| "quý 3" không nêu năm | quý 3 gần nhất đã công bố tại ngày hỏi (giả định) | ← | ← | ← |

**Phép so sánh:**
- Với chỉ số tiền tệ: % tăng trưởng (`yoy`, `qoq`).
- Với chỉ số tỷ lệ: luôn tính **chênh lệch điểm %** (`yoy_pp`). Nếu câu hỏi nói "%" thì B0 ghi giả định "hiểu là điểm phần trăm".
- Lũy kế chỉ so sánh với cùng kỳ năm trước.

## 5. Câu mơ hồ: 2 chính sách (phục vụ RQ3)

`B0System(store, policy=...)`:

| Cụm từ | `policy="default"` (mặc định công khai) | `policy="clarify"` (hỏi lại 1 lượt) |
|---|---|---|
| "lợi nhuận", "lãi" | LNST cổ đông mẹ + ghi giả định | Hỏi: LNST mẹ / LNST toàn bộ / LN gộp |
| "biên lợi nhuận" (không nói gộp/ròng) | **Hỏi làm rõ** (không có mặc định hợp lý) | Hỏi làm rõ |
| "doanh thu" của **ngân hàng** | **Hỏi làm rõ** (R9, do thư viện xử lý) | Hỏi làm rõ |
| "doanh thu" (phi tài chính) | Doanh thu thuần + ghi giả định | *(không hỏi; mơ hồ mức thấp)* |
| "nợ", "hệ số nợ", "đòn bẩy" | Nợ phải trả/VCSH + ghi "không phải nợ vay" | *(không hỏi)* |
| Không nêu kỳ / không nêu năm / "tăng trưởng" không nêu gốc | Kỳ gần nhất / năm gần nhất / YoY + ghi giả định | *(không hỏi)* |

Giả định luôn nằm trong `B0Answer.assumptions` và được in ở dòng "Giả định: …" của câu trả lời.

## 6. B0 từ chối (không đoán)

Các trường hợp sau trả `not_applicable` kèm `reason`:
- **Chỉ số ngoài danh mục:** EPS, EBITDA, LNTT, doanh thu tài chính, dòng tiền, P/E, nợ xấu, nợ vay…
- **Nhiều chỉ số trong một câu:** "doanh thu và lợi nhuận".
- **Không xác định được mã** (câu `lookup` không có mã hay nhóm mã), hoặc **không nhận diện được chỉ số**.
- **Hai kỳ không quy được về YoY/QoQ**, lũy kế so với quý trước, ROE "9 tháng", số dư "4 quý gần nhất".
- **Phép so sánh trên nợ/VCSH** (chưa hỗ trợ ở v1.0).
- **Mã viết hoa ngoài dữ liệu** (vd `XYZ`): được giữ lại để thư viện trả `out_of_scope_ticker`.

Các câu B0 từ chối được tính vào **tỷ lệ không trả lời** (giảm A/N), không tính là sai. Đây đúng là tình huống thước đo 4 đại lượng được thiết kế để phản ánh.

## 7. Đầu ra (`B0Answer.to_dict()`)

```json
{
  "method": "B0",
  "question": "…", "question_date": "2025-02-15",
  "status": "ok | missing_data | not_meaningful | needs_clarification | not_applicable | empty_valid",
  "interpretation": "Chỉ số: … · Đối tượng: … · Kỳ: … (tính tới ngày hỏi …) · Phép: …",
  "assumptions": ["…"], "candidates": ["bank_nii", "…"], "reason": null,
  "query":  { "op": "lookup", "metric": "net_revenue", "tickers": ["VNM"], "period": "2024Q3", "transform": "yoy", "…": "…" },
  "result": { "…": "MetricResult.to_dict() hoặc MultiResult.to_dict(), có inputs[*].source_ref" },
  "text": "Tăng trưởng doanh thu thuần so với cùng kỳ Q3/2024 của VNM: 25,00%\nGiả định: …\nThông tin chỉ nhằm mục đích tham khảo…"
}
```

## 8. Giới hạn đã biết

- Mỗi câu chỉ có một chỉ số và một phép toán. Không hỗ trợ câu ghép ("doanh thu tăng nhưng lợi nhuận giảm?") và không hỗ trợ hội thoại nhiều lượt.
- Từ vựng là danh sách đóng, nên cách diễn đạt nằm ngoài danh sách sẽ bị từ chối. Cần bổ sung dựa trên **tập Dev** (không dùng tập Test) và ghi nhật ký thay đổi từ vựng.
- Tên công ty chỉ nhận diện được khi TV1 cung cấp cột `aliases` trong bảng công ty.
- Ngưỡng lọc không có đơn vị được hiểu theo đơn vị của chỉ số (%, tỷ đồng, lần) và có ghi giả định. Cách đoán này có thể sai với câu viết tắt lạ.
