# NLP-AI Financial Data Assistant

Trợ lý hỏi đáp số liệu báo cáo tài chính VN30 bằng tiếng Việt, có semantic layer,
pipeline LLM, truy vết nguồn và benchmark độc lập.

## Nhánh `linh` — TV5 Giai đoạn 1

Nhánh này hiện triển khai Bộ chấm v1 độc lập:

- chấm câu đơn, bảng nhiều mã và hành động;
- xuất bốn đại lượng `A/N`, `W/A`, `(A-W)/N` và lỗi âm thầm;
- lọc cảnh báo chung chung;
- phân biệt `empty_valid`, thiếu dữ liệu, không có ý nghĩa và cần làm rõ;
- chấm bảng ở cấp dòng và toàn câu;
- phát hiện hỏi lại không cần thiết;
- có fixture “tấn công bộ chấm” và quy trình kiểm toán 100 giá trị.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python scripts/score_results.py --gold gold.json --pred predictions.jsonl
```

Đặc tả chi tiết nằm tại `docs/specs/evaluation-v1.md`.
