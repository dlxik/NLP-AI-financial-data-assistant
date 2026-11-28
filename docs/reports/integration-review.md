# Kiểm tra tích hợp các nhánh — 28/11/2026

## Phạm vi đã hợp nhất

Tích hợp `origin/main` (pilot TV4), `origin/cheese` (TV1), `origin/cuc` (TV2),
`origin/lanh` (TV3), `origin/linh` (TV5) và giữ lịch sử commit của từng nhánh.

Đã gom mã Python dưới `src/fin_assistant/{etl,semantic,b0,pipelines,evaluation}`;
test nằm trong `tests/` theo phân hệ; tài liệu TV1 chuyển vào `docs/data/`.
`pyproject.toml` là cấu hình gói và test chung, dependency ETL tùy chọn nằm ở
`.[etl]`. `.gitignore` hợp nhất quy tắc loại dữ liệu thô, snapshot, PDF và Test kín.

## Kiểm tra đã chạy

- `python -m pytest -q`: toàn bộ test hiện có đạt sau khi di chuyển ETL.
- `node benchmark/phase1/validate.mjs`: đạt kiểm tra nội bộ 30 câu, 27 ô,
  6 cặp đối lập. Máy tích hợp không có 5 PDF gốc nên bước hash PDF là `0/5`.
- `node benchmark/phase1/validate.mjs --gate`: chưa đạt cổng Giai đoạn 1;
  30 phiếu tự kiểm của Hiền và mẫu TV5 vẫn để trống theo dữ liệu hiện có.

Các test trên kiểm tra từng phân hệ riêng; chưa chứng minh luồng ETL → B0/LLM →
chấm benchmark chạy được trên dữ liệu thật.

## Việc cần chốt theo thành viên

### TV1 — Chi: ETL và dữ liệu

1. Pilot TV1 chọn `FPT, HPG, MWG, TCB, VCB`; bộ 30 câu của TV4 dùng
   `FPT, HPG, VNM, VCB, CTG`. Hai bộ đều có 3 phi tài chính và 2 ngân hàng,
   nhưng khác 2 mã. Cần chọn một bộ pilot chung hoặc mở rộng dữ liệu đủ cho cả 7 mã.
2. Schema TV1 dùng `consolidation_scope`, `entity_group`, `report_version` dạng
   chữ (`original/reviewed/audited/restated`) và mã khoản mục như `net_revenue`.
   `FactStore` TV2 yêu cầu `scope`, bảng công ty có `group`, version dạng số nguyên,
   mã khoản mục như `IS.NET_REVENUE`; `FY` cũng cần quy ước thành YTD/Q phù hợp.
   Chưa có adapter được nhóm duyệt, nên không đưa trực tiếp Snapshot TV1 vào TV2.
3. Manifest 115 báo cáo TV1 mới là checklist có trạng thái `PENDING`; repo chưa có
   Snapshot 5 năm hoặc PDF nguồn để xác minh tại máy tích hợp.

### TV2 — Cúc: Semantic Layer và B0

1. Semantic và B0 có test riêng; B0 trả object `{method, question, result, ...}`.
   TV3/TV5 nhận các trường Output Contract ở cấp cao nhất như `question_id`,
   `answer_type`, `metric`, `status`. Cần hàm chuyển B0 → `PipelineOutput` trước
   khi đánh giá chung.
2. ROE pilot TV4 dùng **tổng** LNST và **tổng** vốn chủ, gồm lợi ích cổ đông
   không kiểm soát. ROE mặc định của TV2 là LNST/vốn chủ **thuộc cổ đông mẹ**.
   Đây là hai chỉ số khác nhau; phải chọn quy ước Gold và semantic trước khi chấm.
3. Nhánh TV2 đã có một phần Giai đoạn 2 (14 chỉ số và B0). Báo cáo coverage riêng
   của TV2 đo trên dữ liệu giả lập, chưa xác nhận tính đúng với Snapshot thật.

### TV3 — Lanh: LLM pipeline và sandbox

1. Cấu hình pilot vẫn `provider=mock`, model và API version là `TBD_TEAM_LOCK`.
   Chưa có đo độ ổn định với model thật, phương pháp A/B/C hay demo hoàn chỉnh.
2. Output Contract v0.1 có `ratio` cho tỷ lệ và 16 WarnCode dạng chữ thường.
   Gold TV4 dùng đơn vị `pct` với giá trị theo phần trăm, và mã như
   `BANK_REVENUE_UNDEFINED`, `MISSING_OPENING_EQUITY`. Cần quy tắc chuyển đổi
   đơn vị và mã trước khi kết nối với TV5; không đổi Gold gốc âm thầm.

### TV4 — Hiền: Benchmark và Gold

1. Pilot 30 câu đã có trên `main`; việc push nhầm không làm mất nội dung. Hồ sơ
   ghi Hiền đã duyệt kiểm chứng do trợ lý thực hiện. Các trường Hiền tự đọc nguồn,
   tự tính và TV5 kiểm tra độc lập vẫn chưa được xác nhận.
2. Gold ở `benchmark/phase1/pilot_gold.json` dùng schema riêng
   (`expected_action`, `rows`, `required_warning`, `clarification`). Bộ chấm TV5
   nhận `status`, `answer_type`, `metric`, `required_warning_codes`.
   Chưa có bản chuyển đổi Gold được duyệt; cần chốt cùng chính sách ROE, đơn vị
   và cảnh báo ở trên.
3. Các PDF nguồn không nằm trong repo. Manifest có URL và SHA256 để tải đúng bản;
   kiểm tra hash cần chạy lại ở máy có PDF.

### TV5 — Linh: Bộ chấm và QA

1. Bộ chấm v1 và fixture tấn công đã có test riêng, nhưng chưa chạy trên 30 câu
   pilot của TV4 vì schema Gold và Output Contract chưa được chốt.
2. Chưa có biên bản TV5 truy ngược mẫu Gold về PDF và chưa thực hiện phiên
   tấn công bộ chấm với đầu ra pilot thật. Giao thức kiểm toán 100 giá trị mới là
   biểu mẫu; kiểm toán thực tế chờ Snapshot TV1 ở Giai đoạn 2.

## Thứ tự kết nối tiếp theo

1. Nhóm chốt 5 mã pilot và định nghĩa ROE; TV4 xác nhận Gold tương ứng.
2. TV1/TV2 chốt hợp đồng `fact_financials`, version và mã khoản mục; tạo adapter
   có test trên Snapshot mẫu và đối chiếu PDF.
3. TV3/TV5 chốt Output Contract, đơn vị phần trăm, mã cảnh báo; tạo bộ chuyển
   B0 và Gold TV4 vào schema chấm chung.
4. TV5 chấm pilot, tự kiểm mẫu nguồn và chạy tấn công bộ chấm; sau đó mới xét
   Phase Gate Giai đoạn 1.
