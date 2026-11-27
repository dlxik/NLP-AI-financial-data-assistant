# Đặc tả Output Contract v0.1 (TV3 — LLM Pipeline)

| | |
|---|---|
| **Phiên bản** | v0.1 — bản dự thảo Giai đoạn 1 (chờ chốt cùng TV5 & TV2 tại Cổng GĐ1) |
| **Người phụ trách** | TV3 (LLM Pipeline, Sandbox & Demo) |
| **Người tích hợp chính** | TV5 (Bộ chấm v1), TV2 (Semantic Layer B0/B/C) |
| **Mã nguồn & Validator** | `src/fin_assistant/pipelines/contract.py` |

---

## 1. Mục tiêu thiết kế

Mọi pipeline trong hệ thống (**B0, A, B, C** và các thí nghiệm phụ **B1, D**) khi chạy trả lời câu hỏi phải xuất JSON theo cùng một **Output Contract** để:
1. **Bộ chấm v1 (TV5)** đọc thống nhất được cả kết quả đơn trị, bảng nhiều mã, phép lọc 0 dòng, và các hành động không trả số (`missing_data`, `not_meaningful`, `needs_clarification`, `not_applicable`).
2. **Kiểm tra cảnh báo cụ thể (TV5):** Tách rõ cảnh báo có nêu đối tượng bị ảnh hưởng (`ticker`, `period`, `item_code`) khỏi cảnh báo chung chung.
3. **Tương thích với TV2 (`MetricResult` / `MultiResult`):** Dùng chung tập `Status`, `WarnCode` và cấu trúc `InputRef` (`source_ref`) để phục vụ ghép B/C ở GĐ2–GĐ3 và Demo truy vết ở GĐ4.

---

## 2. Cấu trúc JSON chuẩn (`PipelineOutput`)

```json
{
  "contract_version": "0.1",
  "question_id": "pilot_001",
  "question_date": "2025-02-15",
  "pipeline": "pilot_llm",
  "status": "ok",
  "answer_type": "single",
  "metric": "net_revenue_yoy",
  "ticker": "VNM",
  "period": "2024Q4",
  "value": 0.0425,
  "unit": "ratio",
  "period_policy": null,
  "rows": [],
  "excluded": [],
  "formula": "(REV(2024Q4) - REV(2023Q4)) / REV(2023Q4)",
  "interpreted_query": {
    "ticker": "VNM",
    "tickers": ["VNM"],
    "metric": "net_revenue",
    "period": "2024Q4",
    "transform": "yoy",
    "scope": "consolidated",
    "assumptions": ["kỳ gần nhất đơn mã theo ngày hỏi 2025-02-15"]
  },
  "inputs": [
    {
      "item_code": "IS.NET_REVENUE",
      "ticker": "VNM",
      "period": "2024Q4",
      "value": 15400000000000.0,
      "unit": "VND",
      "source_ref": "VNM_2024Q4_B02.pdf#p2:L10",
      "report_version": 1,
      "as_of_date": "2025-01-30",
      "is_restated": false,
      "derived_from": null
    }
  ],
  "warnings": [],
  "candidates": [],
  "message": "Tăng trưởng doanh thu thuần YoY quý 4/2024 của VNM là 4,25%.",
  "execution_meta": {
    "model": "TBD_TEAM_LOCK",
    "model_version": "TBD_TEAM_LOCK",
    "seed": 42,
    "temperature": 0.0,
    "num_llm_calls": 1,
    "latency_ms": 412.5,
    "prompt_tokens": 320,
    "completion_tokens": 110,
    "total_tokens": 430,
    "sandbox_used": false,
    "sandbox_ok": null
  },
  "details": {}
}
```

---

## 3. Bảng trạng thái (`status`) và quy tắc ràng buộc

| `status` | Ý nghĩa / Hành động | Tính vào `A` (đã trả lời)? | Ràng buộc bắt buộc |
|---|---|---|---|
| `ok` | Trả số hợp lệ (có thể kèm cảnh báo) | Có | `single`: `value` là số hữu hạn, có `ticker` & `period`. `table`: `rows` khác rỗng và có ≥ 1 dòng `ok`. |
| `empty_valid` | Phép lọc chạy trên dữ liệu đầy đủ, 0 dòng thỏa | Có | `answer_type = "table"`, `value = null`, `rows = []`. |
| `missing_data` | Thiếu ô số đầu vào hoặc kỳ chưa công bố | Không | `value = null`; có cảnh báo (`missing_input` / `not_yet_published`) hoặc `message` giải thích. |
| `not_meaningful` | Không xác định (mẫu số ≤ 0, gần 0, VCSH ≤ 0) | Không | `value = null`; có cảnh báo cụ thể (`negative_equity`, `non_positive_base`, `denominator_near_zero`). |
| `needs_clarification` | Câu hỏi mơ hồ hoặc dùng chỉ tiêu không áp dụng cần làm rõ | Không | `value = null`; `candidates` là danh sách lựa chọn khác rỗng. |
| `not_applicable` | Chỉ tiêu không áp dụng cho nhóm DN / mã ngoài phạm vi | Không | `value = null`; có cảnh báo (`metric_not_applicable` / `out_of_scope_ticker`) hoặc `message`. |

---

## 4. Quy tắc cảnh báo cụ thể (`warnings`)

Mỗi phần tử trong `warnings` có cấu trúc:

```json
{
  "code": "negative_equity",
  "message": "Vốn chủ sở hữu cổ đông công ty mẹ tại 2024Q3 <= 0 (-120 tỷ VND), không tính ROE.",
  "ticker": "HAG",
  "period": "2024Q3",
  "item_code": "BS.EQUITY_PARENT",
  "severity": "warning"
}
```

- **Quy tắc chống cảnh báo chung chung:** Với mọi `warning` có `severity = "warning"` (trừ các cảnh báo tổng hợp cấp bảng `mixed_periods`, `partial_coverage`, `excluded_not_meaningful`), bắt buộc phải có ít nhất một trong các trường định vị `ticker`, `period`, hoặc `item_code`. Validator sẽ đánh lỗi nếu hệ thống chỉ phát cảnh báo chung chung.
- Tập `code` chuẩn dùng chung với đặc tả TV2 gồm 16 mã: `missing_input`, `not_yet_published`, `out_of_scope_ticker`, `negative_equity`, `non_positive_base`, `denominator_near_zero`, `extreme_value`, `fallback_ending_equity`, `bank_no_net_revenue`, `metric_not_applicable`, `restated_value`, `derived_value`, `newer_period_available`, `mixed_periods`, `partial_coverage`, `excluded_not_meaningful`.

---

## 5. Các điểm cần chốt với TV5 tại Cổng GĐ1

1. Cách tính sai số và khớp bảng nhiều mã (`rows`): khớp theo `(ticker, period)` hay chỉ theo `ticker` khi dùng `period_policy = "common"`.
2. Chuẩn đơn vị trả về trong `value` cho Bộ chấm: `ratio` (ví dụ `0.0425` cho 4,25%) hay phần trăm (`4.25`), và `VND` gốc cho chỉ tiêu tiền tệ.
3. Cách quy đổi khi LLM trả lỗi parse JSON / lỗi sandbox: có ánh xạ sang trạng thái `missing_data` hay giữ `parse_error` trong log runner để Bộ chấm tính là *không trả lời / sai*.
