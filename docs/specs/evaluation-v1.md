# Đặc tả Bộ chấm v1 — TV5, Giai đoạn 1

## 1. Phạm vi

Bộ chấm nhận Gold độc lập và đầu ra theo Output Contract v0.1. Bộ chấm không import
semantic layer hoặc pipeline LLM, tránh dùng lại logic của hệ thống đang được đánh giá.

Hỗ trợ ba loại đầu ra:

- `single`: một giá trị cho một mã/kỳ;
- `table`: bảng nhiều mã, xếp hạng hoặc lọc;
- `action`: thiếu dữ liệu, không có ý nghĩa, cần làm rõ hoặc không áp dụng.

## 2. Bốn đại lượng bắt buộc

Với `N` câu, `A` là số câu có trạng thái `ok` hoặc `empty_valid`, `W` là số câu sai
trong số đã trả lời:

1. Tỷ lệ trả lời: `A/N`.
2. Tỷ lệ sai trong câu đã trả lời: `W/A`.
3. Tỷ lệ đúng toàn tập: `(A-W)/N`.
4. Lỗi âm thầm: câu đã trả lời sai nhưng không có cảnh báo cụ thể đúng loại mà Gold yêu cầu.

Vì ba tỷ lệ đầu không ghi nhận một hành động từ chối đúng, báo cáo bổ sung
`behavior_accuracy`. Chỉ số này đúng khi toàn bộ trạng thái, loại câu trả lời, giá trị,
mã/kỳ, cảnh báo bắt buộc và lựa chọn làm rõ đều khớp Gold.

## 3. So khớp

- Số dùng đồng thời `abs_tol` và `rel_tol` do Gold quy định.
- Đơn vị, mã, kỳ và metric phải khớp.
- Bảng mặc định ghép theo `(ticker, period)`; Gold có thể đổi `row_key_fields`.
- Bảng được chấm cả từng dòng và exact-match toàn câu. Thiếu, thừa hoặc trùng khóa đều sai.
- `empty_valid` là một câu đã trả lời đúng; không được đánh đồng với `missing_data`.
- `needs_clarification` có thể yêu cầu tập `required_candidates`.

## 4. Cảnh báo cụ thể

Cảnh báo được công nhận khi có `code`, `message` và ít nhất một trường định vị:
`ticker`, `period` hoặc `item_code`. Cảnh báo định vị sai mã/kỳ không thỏa Gold.

Ba cảnh báo tổng hợp cấp bảng (`mixed_periods`, `partial_coverage`,
`excluded_not_meaningful`) được miễn trường định vị.

## 5. Tấn công bộ chấm

Fixture `evaluation/fixtures/attack_cases.json` chứa tối thiểu:

- đảo kỳ nhưng giữ nguyên giá trị;
- hoán đổi giá trị giữa hai mã;
- dùng cảnh báo chung chung để che lỗi;
- luôn hỏi lại mọi câu.

Mọi ca phải làm `behavior_accuracy < 1`. Nếu một ca được điểm tuyệt đối, Phase Gate dừng
để sửa bộ chấm trước khi mở rộng Benchmark.

## 6. Chạy

```powershell
python -m pytest
python scripts/score_results.py --gold gold.json --pred predictions.jsonl
```
