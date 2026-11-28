# Báo cáo coverage unit test — Semantic Layer v1.0 & B0

| | |
|---|---|
| **Ngày chạy** | 28/11/2026 |
| **Môi trường** | Python 3.13.5, pytest 9.2.0, pytest-cov (coverage.py, đo cả **nhánh**) — Windows |
| **Phạm vi đo** | `src/fin_assistant/semantic/` (thư viện chỉ số) và `src/fin_assistant/b0/` (phương pháp B0) |
| **Kết quả** | **341 test, tất cả đạt** · coverage **100% dòng, 100% nhánh** (1.468 câu lệnh, 532 nhánh) |

Lệnh tái lập:

```bash
pip install -e ".[dev]"
pytest --cov --cov-report=term-missing      # cấu hình nguồn đo trong pyproject.toml, ngưỡng tối thiểu 95%
```

## 1. Coverage theo module

| Module | Câu lệnh | Nhánh | Coverage |
|---|---:|---:|---:|
| `semantic/api.py` (get_metric, multi, rank, screen) | 142 | 68 | 100% |
| `semantic/metrics.py` (engine lớp 1–3, quy tắc 4.3) | 204 | 84 | 100% |
| `semantic/store.py` (hợp đồng dữ liệu, as_of, phiên bản) | 156 | 64 | 100% |
| `semantic/query.py` (truy vấn có cấu trúc, dùng chung B0/C) | 103 | 32 | 100% |
| `semantic/catalog.py` (14 chỉ số, phép biến đổi) | 98 | 30 | 100% |
| `semantic/result.py`, `rules.py`, `periods.py`, `fmt.py`, `__init__.py` | 298 | 78 | 100% |
| `b0/parser.py` (phân tích câu tiếng Việt) | 316 | 152 | 100% |
| `b0/system.py`, `lexicon.py`, `normalize.py`, `__init__.py` | 151 | 24 | 100% |
| **Tổng** | **1.468** | **532** | **100%** |

**Loại trừ.** Có 2 nhánh được đánh dấu `# pragma: no cover`. Cả hai là nhánh phòng vệ, không chạm tới được qua API công khai vì truy vấn đã được kiểm tra trước đó:
- `query.py`: bắt `UnknownMetricError`/`TransformError` trong `execute`, vốn đã bị `Query.validate()` chặn;
- `b0/system.py`: bắt `QueryError` sau khi bộ phân tích đã validate truy vấn.

## 2. Phân bổ test theo nhóm ca

| File | Số test | Nội dung chính |
|---|---:|---|
| `tests/semantic/test_periods_rules.py` | 32 | Kỳ (phân tích chuỗi, dịch kỳ, TTM), ngưỡng mẫu số R1–R3, `RuleConfig`, phép so sánh giới hạn |
| `tests/semantic/test_store.py` | 15 | Hợp đồng dữ liệu, chọn phiên bản theo ngày hỏi (T1–T2), kỳ gần nhất đơn mã (T4) |
| `tests/semantic/test_pilot_metrics.py` | 38 | 3 đại lượng pilot GĐ1, vốn chủ âm, thiếu đầu kỳ, ngân hàng (R9), hồi tố |
| `tests/semantic/test_v1_metrics.py` | 66 | 14 chỉ số, ràng buộc kiểu phép biến đổi, YTD (ưu tiên cột lũy kế công bố) / TTM / QoQ / YoY / điểm % |
| `tests/semantic/test_multi_and_screen.py` | 16 | Kỳ gần nhất đa mã (T5), quy tắc 0 dòng (R8) |
| `tests/semantic/test_rank_query.py` | 37 | Xếp hạng (R12), nhóm mã, `Query` (JSON, validate, 13 ca truy vấn sai), bộ thực thi |
| `tests/semantic/test_edge_cases.py` | 25 | Vi phạm hợp đồng dữ liệu, hiển thị, nhánh hiếm |
| `tests/b0/test_parser.py` | 96 | 49 câu → truy vấn kỳ vọng; 12 giả định công khai; mơ hồ theo 2 chính sách; 13 ca từ chối có lý do |
| `tests/b0/test_system.py` | 16 | B0 đầu–cuối: trạng thái hành động, câu hiểu lại, kỳ cạnh số, JSON |
| **Tổng** | **341** | |

## 3. Ca biên bắt buộc đã có test

| Ca biên | Test tiêu biểu |
|---|---|
| Kỳ gốc ≤ 0 / gần 0 / giá trị cực đoan | `test_yoy_zero_base_not_meaningful`, `…near_zero…`, `…extreme_value…` |
| Vốn chủ âm (ROE, nợ/VCSH) và cặp "lỗ / VCSH âm ra ROE dương" | `test_negative_equity_and_loss_do_not_produce_positive_roe`, `test_liabilities_to_negative_equity_not_meaningful` |
| Mã vốn chủ âm bị loại khỏi xếp hạng và lọc | `TestRank::test_negative_equity_excluded_and_disclosed`, `test_negative_equity_never_passes_a_positive_filter` |
| Thiếu đầu kỳ (ROE, ROA) có/không fallback | `test_missing_beginning_equity_*`, `test_roa_missing_assets_with_fallback` |
| Không ngoại suy từ ít hơn 4 quý | `test_no_annualisation_from_partial_year`, `test_ytd_missing_quarter_is_named` |
| 0 dòng hợp lệ vs thiếu dữ liệu | `TestScreenZeroRows::*`, `test_screen_empty_valid_vs_missing` (B0) |
| Kỳ gần nhất đơn mã vs đa mã | `test_latest_period_single_ticker`, `TestLatestMulti::*`, `test_rank_uses_common_latest_period` |
| Q3 vs lũy kế 9 tháng | `test_ytd_yoy_uses_reported_cumulative_columns` |
| % YoY vs điểm % | `test_ratio_change_is_percentage_points`, `test_check_transform_type_rules` |
| Top tuyệt đối vs tốc độ tăng | `test_rank_on_growth` |
| Chưa công bố vs thiếu dữ liệu; hồi tố | `test_not_yet_published_differs_from_missing`, `test_restated_base_is_used_and_disclosed` |
| "Doanh thu thuần" ngân hàng (đơn mã, đa mã, lọc, xếp hạng, B0) | `TestBankNetRevenue::*`, `test_bank_revenue_*` |

## 4. Lỗi phát hiện nhờ test trong quá trình phát triển

1. **Thiếu VCSH đầu kỳ bị dùng VCSH cuối kỳ một cách âm thầm** (bản pilot, GĐ1). Đã sửa: mặc định trả `missing_data`.
2. **Phép so sánh khi một đầu "không xác định".** Ví dụ kỳ hiện tại vốn chủ âm, kỳ gốc thiếu dữ liệu: hàm trả `missing_data`, gợi ý rằng có thêm dữ liệu thì trả lời được. Đã sửa: `not_meaningful` được ưu tiên.
3. **B0 nhận "III" (quý III) là mã cổ phiếu**, khiến kỳ bị hiểu thành cả năm. Đã thêm số La Mã vào danh sách loại trừ.
4. **B0 bỏ sót điều kiện "lợi nhuận âm"** vì từ gợi ý "nào" bị bước nhận diện nhóm mã tiêu thụ trước. Đã sửa: tìm từ gợi ý trên toàn câu.

## 5. Giới hạn của báo cáo này

- Coverage 100% nghĩa là mọi dòng và nhánh **đã được chạy**, **không** có nghĩa là thư viện đúng trên dữ liệu thật. Toàn bộ test dùng **dữ liệu giả lập** (mã AAA, NHA…). Việc khớp với BCTC gốc được kiểm chứng riêng qua Gold độc lập (TV4) và kiểm toán 100 giá trị (TV5).
- Ca câu hỏi của B0 trong `test_parser.py` do TV2 tự viết để kiểm thử, **không** phải tập Dev/Test của Benchmark. Độ chính xác của B0 phải đo trên tập Dev (GĐ2) và tập Test niêm phong (GĐ3).
