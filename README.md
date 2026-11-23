# NLP-AI Financial Data Assistant

Trợ lý hỏi đáp số liệu BCTC nhóm **VN30** bằng tiếng Việt. Dự án so sánh có kiểm soát 4 phương pháp:

| Mã | Phương pháp |
|---|---|
| **B0** | Quy tắc / template, không dùng LLM |
| **A** | LLM sinh code Pandas |
| **B** | LLM sinh code gọi thư viện chỉ số (semantic layer) |
| **C** | LLM sinh truy vấn JSON, chạy bằng bộ thực thi giới hạn |

Kết quả được đánh giá bằng 4 đại lượng: tỷ lệ trả lời, tỷ lệ sai trong câu đã trả lời, tỷ lệ đúng toàn tập và tỷ lệ lỗi âm thầm. Kế hoạch chi tiết: [kehoach.md](kehoach.md).

## Cấu trúc thư mục

```
.
├── kehoach.md                      Kế hoạch 4 giai đoạn, 5 thành viên
├── pyproject.toml                  Gói Python `fin-assistant` (src layout)
├── docs/
│   ├── research/
│   │   └── tong-quan-tai-lieu.md   Công trình liên quan, chuẩn mực BCTC VN, khoảng trống nghiên cứu
│   └── specs/
│       ├── dac-ta-quy-tac-so-lieu-va-thoi-gian.md   Đặc tả quy tắc 4.3 (số liệu khó) & 4.4 (thời gian)
│       └── danh-muc-chi-so-de-xuat.md               14 chỉ số đề xuất cho GĐ2, tách 3 lớp
├── src/fin_assistant/
│   ├── semantic/      TV2: thư viện chỉ số (get_metric, get_metric_multi, screen)
│   ├── etl/           TV1: nạp & chuẩn hóa fact_financials, Snapshot
│   ├── pipelines/     TV3: pipeline LLM A/B/B1/D, sandbox, demo
│   └── evaluation/    TV5: bộ chấm, thống kê
├── tests/semantic/    Unit test thư viện chỉ số (dữ liệu giả lập)
├── data/              Dữ liệu (không commit dữ liệu thô / Snapshot)
├── benchmark/dev/     Tập Dev công khai (tập Test niêm phong KHÔNG nằm trong repo)
├── configs/           Cấu hình đóng băng (RuleConfig, cấu hình LLM)
├── scripts/           Script chạy batch / tái lập kết quả
└── notebooks/         Khám phá dữ liệu
```

## Cài đặt & chạy test

```bash
pip install -e ".[dev]"
pytest
```

## Ví dụ dùng thư viện chỉ số

```python
from fin_assistant.semantic import FactStore, get_metric, describe

store = FactStore(facts_df, companies_df)  # facts_df theo hợp đồng dữ liệu (đặc tả, mục 2)

r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="yoy", as_of="2024-11-15")
r.status    # Status.OK / MISSING_DATA / NOT_MEANINGFUL / NEEDS_CLARIFICATION / ...
r.value     # 0.25 (tức +25%)
r.inputs    # các ô số đã dùng, kèm source_ref để truy vết
describe(r) # "Tăng trưởng doanh thu thuần so với cùng kỳ Q3/2024 của AAA: 25,00%"

get_metric(store, "net_revenue", "NHA", "latest")  # ngân hàng → NEEDS_CLARIFICATION, không tự thay bằng NII
get_metric(store, "roe_ttm", "DDD", "2024Q3")      # vốn chủ âm → NOT_MEANINGFUL
```

## Phân công

| Mã | Vai trò | Thư mục chính |
|---|---|---|
| TV1 | Data & ETL | `src/fin_assistant/etl`, `data/` |
| TV2 | Semantic Layer & B0/C | `src/fin_assistant/semantic`, `docs/specs/` |
| TV3 | LLM Pipeline, Sandbox & Demo | `src/fin_assistant/pipelines` |
| TV4 | Benchmark & Test Keeper | `benchmark/` (Test giữ ngoài repo) |
| TV5 | Evaluation, QA & Statistics | `src/fin_assistant/evaluation` |
