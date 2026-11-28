# NLP-AI Financial Data Assistant

Trợ lý hỏi đáp số liệu BCTC nhóm **VN30** bằng tiếng Việt. Dự án so sánh có kiểm soát 4 phương pháp:

Repo hiện gồm mã nền và pilot Giai đoạn 1. B0/semantic đã có thêm phần Giai đoạn 2 trên nhánh TV2; A, B, C và demo chưa có bản chạy hoàn chỉnh. [Kế hoạch 4 giai đoạn](kehoach.md).

| Mã | Phương pháp |
|---|---|
| **B0** | Quy tắc / template, không dùng LLM |
| **A** | LLM sinh code Pandas |
| **B** | LLM sinh code gọi thư viện chỉ số (semantic layer) |
| **C** | LLM sinh truy vấn JSON, chạy bằng bộ thực thi giới hạn |

Kết quả dự kiến được đánh giá bằng 4 đại lượng: tỷ lệ trả lời, tỷ lệ sai trong câu đã trả lời, tỷ lệ đúng toàn tập và tỷ lệ lỗi âm thầm.

## Cấu trúc thư mục

```
.
├── kehoach.md                      Kế hoạch 4 giai đoạn, 5 thành viên
├── pyproject.toml                  Gói Python `fin-assistant` (src layout)
├── docs/
│   ├── data/          TV1: schema, danh sách VN30, nguồn dữ liệu
│   ├── research/      Tài liệu liên quan
│   ├── specs/         Quy tắc số liệu, B0, output contract và bộ chấm
│   ├── qa/            Quy trình kiểm toán 100 giá trị
│   └── reports/       Báo cáo tiến độ, coverage và kiểm tra tích hợp
├── src/fin_assistant/
│   ├── semantic/      TV2: Semantic Layer v1.0 (get_metric, get_metric_multi, rank, screen, Query/execute)
│   ├── b0/            TV2: phương pháp B0 — phân tích câu tiếng Việt bằng quy tắc → Query → semantic layer
│   ├── etl/           TV1: schema, quy đổi YTD→Q và manifest pilot
│   ├── pipelines/     TV3: runner, output contract, cấu hình và sandbox pilot
│   └── evaluation/    TV5: bộ chấm v1
├── tests/             Test theo từng phân hệ: etl, semantic, b0, pipelines, evaluation
├── data/reference/    Danh mục và manifest TV1; dữ liệu thô/Snapshot giữ ngoài Git
├── benchmark/phase1/ Bộ 30 câu pilot TV4; Test chính giữ ngoài repo
├── evaluation/        Fixture tấn công bộ chấm và mẫu kiểm toán
├── configs/           Cấu hình đóng băng (RuleConfig, cấu hình LLM)
├── scripts/           Script chạy batch / tái lập kết quả
└── notebooks/         Khám phá dữ liệu
```

## Cài đặt & chạy test

```bash
python -m pip install -e ".[dev]"
python -m pytest
node benchmark/phase1/validate.mjs                  # Node.js 18+, kiểm tra cấu trúc pilot TV4
```

## Ví dụ dùng thư viện chỉ số

```python
from fin_assistant.semantic import FactStore, get_metric, rank, describe

store = FactStore(facts_df, companies_df)  # facts_df theo hợp đồng dữ liệu (đặc tả, mục 2)

r = get_metric(store, "net_revenue", "AAA", "2024Q3", transform="yoy", as_of="2024-11-15")
r.status    # Status.OK / MISSING_DATA / NOT_MEANINGFUL / NEEDS_CLARIFICATION / ...
r.value     # 0.25 (tức +25%)
r.inputs    # các ô số đã dùng, kèm source_ref để truy vết
describe(r) # "Tăng trưởng doanh thu thuần so với cùng kỳ Q3/2024 của AAA: 25,00%"

get_metric(store, "net_revenue", "NHA", "latest")  # ngân hàng → NEEDS_CLARIFICATION, không tự thay bằng NII
get_metric(store, "roe_ttm", "DDD", "2024Q3")      # vốn chủ âm → NOT_MEANINGFUL
get_metric(store, "net_revenue", "AAA", "2024Q3", transform="ytd_yoy")  # lũy kế 9 tháng so với cùng kỳ
get_metric(store, "gross_margin", "AAA", "2024Q3", transform="yoy_pp")  # thay đổi biên LN gộp, điểm %
rank(store, "roe_ttm", store.tickers(), "latest", top_n=5, as_of="2025-02-15")
```

Phép biến đổi: `[ytd|ttm][_][yoy|qoq][_pp]` — xem R14 trong [đặc tả](docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md).

## Ví dụ dùng B0

```python
from fin_assistant.b0 import B0System

b0 = B0System(store)                      # policy="clarify" để hỏi lại khi câu mơ hồ (RQ3)
ans = b0.answer("Doanh thu 9 tháng đầu năm 2024 của VNM tăng bao nhiêu so với cùng kỳ?", "2024-11-15")
ans.status          # Status.OK
ans.interpretation  # "Chỉ số: … · Đối tượng: VNM · Kỳ: 2024Q3 (tính tới ngày hỏi 2024-11-15)"
ans.query.to_json() # truy vấn có cấu trúc — cùng định dạng phương pháp C sẽ dùng
ans.text            # câu trả lời có kỳ cạnh số + giả định + lời miễn trừ
ans.to_dict()       # JSON cho output contract / bộ chấm
```

## Phân công

| Mã | Vai trò | Thư mục chính |
|---|---|---|
| TV1 | Data & ETL | `src/fin_assistant/etl`, `data/` |
| TV2 | Semantic Layer & B0/C | `src/fin_assistant/semantic`, `src/fin_assistant/b0`, `docs/specs/` |
| TV3 | LLM Pipeline, Sandbox & Demo | `src/fin_assistant/pipelines` |
| TV4 | Benchmark & Test Keeper | `benchmark/` (Test giữ ngoài repo) |
| TV5 | Evaluation, QA & Statistics | `src/fin_assistant/evaluation` |

## Benchmark pilot của TV4

- [Hồ sơ 30 câu và Gold](benchmark/phase1/README.md)
- [Bản đọc câu hỏi và lời giải](benchmark/phase1/PILOT_VA_GOLD.md)

Gold pilot được trợ lý hỗ trợ chép và tính từ báo cáo gốc; Hiền đã duyệt kết quả kiểm chứng của trợ lý. Bước TV5 kiểm tra độc lập và nghiệm thu cổng giai đoạn vẫn còn chờ. Các PDF nguồn không nằm trong Git; URL và SHA256 được ghi trong manifest.

Pilot TV4 dùng `FPT`, `HPG`, `VNM`, `VCB`, `CTG`; danh sách pilot TV1 dùng `FPT`, `HPG`, `MWG`, `VCB`, `TCB`. Quyết định bộ mã pilot chung và ánh xạ schema dữ liệu/Gold cần được chốt trước khi chạy đánh giá thật. Xem [báo cáo tích hợp](docs/reports/integration-review.md).

## Bộ chấm TV5

Bộ chấm v1 xử lý câu đơn, bảng nhiều mã và hành động; có bộ ca tấn công tự động và quy trình kiểm toán 100 giá trị. Xem [đặc tả đánh giá](docs/specs/evaluation-v1.md) và [báo cáo Giai đoạn 1](docs/reports/linh_giai_doan_1.md).
