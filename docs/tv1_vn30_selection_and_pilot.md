# Chốt danh mục VN30, Phân loại mã & Lựa chọn 5 mã Pilot (TV1 — Tuần 1)

- **Người thực hiện:** Chi (TV1 — Data & ETL Engineer)
- **Ngày chốt danh mục (Freeze Date):** `2026-11-27`
- **Cơ sở rà soát:** Danh mục thành phần chỉ số VN30 do HOSE công bố tại kỳ rà soát tháng 7/2026 (có hiệu lực từ ngày `2026-08-03`, bổ sung `MCH`, `TCX`; loại `TPB`, `PLX`; trước đó tháng 5/2026 bổ sung `BSR` thay `DGC` và tháng 2/2026 bổ sung `VPL` thay `BCM`).
- **Tệp dữ liệu cấu trúc:** [`vn30_constituents_2026-11-27.csv`](file:///d:/NLP/NLP-AI-financial-data-assistant/data/reference/vn30_constituents_2026-11-27.csv)

---

## 1. Tổng hợp phân loại 30 mã VN30

| Nhóm phân loại | Số lượng | Danh sách mã | Ghi chú |
|---|---:|---|---|
| **Giữ lại — Phi tài chính (`non_financial`)** | **15** | `BSR`, `FPT`, `GAS`, `GVR`, `HPG`, `MCH`, `MSN`, `MWG`, `POW`, `SAB`, `VHM`, `VIC`, `VJC`, `VNM`, `VRE` | Áp dụng chuẩn BCTC doanh nghiệp (TT 200/2014/TT-BTC), đều có chuỗi BCTC công khai ≥5 năm (`BSR` giao dịch UPCoM từ 03/2018 trước khi chuyển HOSE 01/2025; `MCH` giao dịch UPCoM từ 2017 trước khi chuyển HOSE). |
| **Giữ lại — Ngân hàng (`bank`)** | **11** | `ACB`, `BID`, `CTG`, `HDB`, `MBB`, `SSB`, `STB`, `TCB`, `VCB`, `VIB`, `VPB` | Áp dụng chuẩn BCTC TCTD (TT 49/2014/TT-NHNN). `SSB` niêm yết HOSE từ `2021-03-24` (đến `2026-11-27` là >5,5 năm, cần kiểm tra độ phủ các quý đầu 2021 khi ETL). Nhóm ngân hàng sẽ được đánh giá lại ở cổng Phase Gate GĐ1 (có giữ trong mẫu chính hay tách tập mở rộng). |
| **Loại (`EXCLUDE`)** | **4** | `BVH`, `SSI`, `TCX`, `VPL` | Xem bảng lý do chi tiết bên dưới. |
| **Tổng cộng** | **30** | **26 mã giữ lại / 4 mã loại** | |

### Chi tiết các mã bị loại (`EXCLUDE`)

1. **`SSI` (CTCP Chứng khoán SSI):** Thuộc nhóm **Chứng khoán**, lập BCTC theo Thông tư 334/2016/TT-BTC (doanh thu môi giới, lãi/lỗ FVTPL, AFS, cho vay ký quỹ...), không tương thích hệ chỉ số doanh thu thuần & vốn chủ phi tài chính hay ngân hàng.
2. **`TCX` (CTCP Chứng khoán Kỹ Thương — TCBS):** Thuộc nhóm **Chứng khoán** (TT 334/2016/TT-BTC) **đồng thời** mới niêm yết trên HOSE từ `2025-10-21` nên không đủ chuỗi lịch sử niêm yết công khai ≥5 năm.
3. **`BVH` (Tập đoàn Bảo Việt):** Thuộc nhóm **Bảo hiểm / Tài chính hỗn hợp**, lập BCTC theo Thông tư 232/2012/TT-BTC (hợp nhất bảo hiểm nhân thọ, phi nhân thọ, quỹ dự phòng nghiệp vụ...), cấu trúc khoản mục khác biệt hoàn toàn.
4. **`VPL` (CTCP Vinpearl):** Dù thuộc nhóm **Phi tài chính** (Du lịch & Nghỉ dưỡng), nhưng mới tái niêm yết độc lập trên HOSE từ `2025-05-13` (trước đó hủy niêm yết năm 2011 để sáp nhập vào Vingroup), không đảm bảo chuỗi BCTC quý niêm yết công khai liên tục ≥5 năm dưới tư cách pháp nhân độc lập.

> **Lưu ý cho Giai đoạn 2:** Khi chạy ETL toàn bộ 26 mã giữ lại, nếu phát hiện mã nào thiếu BCTC quý trong giai đoạn đầu 2021 (ví dụ `SSB` quý 1/2021 hoặc các quý chuyển đổi sàn của `BSR`, `MCH`), TV1 sẽ ghi nhận cụ thể trong nhật ký dữ liệu trước khi đóng băng Snapshot v1.0.

---

## 2. Lựa chọn 5 mã Pilot cho Giai đoạn 1 (Tuần 1–3)

Tiêu chí theo `kehoach.md`: **3 mã phi tài chính khác ngành + 2 mã ngân hàng**, có thanh khoản/minh bạch CBTT cao, đủ BCTC quý ≥5 năm (`Q1/2021 – Q3/2026`, tổng 23 quý/mã).

| STT | Mã | Tên doanh nghiệp | Nhóm | Ngành chi tiết | Lý do chọn vào Pilot | Cổng IR chính thức (nguồn BCTC PDF) |
|---|---|---|---|---|---|---|
| 1 | **`FPT`** | CTCP FPT | `non_financial` | Công nghệ thông tin & Viễn thông | Tăng trưởng ổn định, báo cáo tiếng Việt & Anh đầy đủ, rõ ràng. | `https://fpt.com.vn/en/investor/reports/financial-report` |
| 2 | **`HPG`** | CTCP Tập đoàn Hòa Phát | `non_financial` | Sản xuất công nghiệp / Thép & Vật liệu | Doanh nghiệp sản xuất chu kỳ, có biến động mạnh biên lợi nhuận & doanh thu quý qua các chu kỳ -> kiểm thử tốt ca YoY/ROE. | `https://www.hoaphat.com.vn/bao-cao-tai-chinh` |
| 3 | **`MWG`** | CTCP Đầu tư Thế Giới Di Động | `non_financial` | Bán lẻ tiêu dùng | Ngành bán lẻ biên lợi nhuận mỏng, từng có giai đoạn suy giảm mạnh lợi nhuận 2023 -> kiểm thử tốt ca biên ROE TTM & mẫu số nhỏ. | `https://mwg.vn` (Mục Quan hệ nhà đầu tư) |
| 4 | **`VCB`** | Ngân hàng TMCP Ngoại thương Việt Nam | `bank` | Ngân hàng (TMCP Nhà nước chi phối) | Ngân hàng đầu ngành theo TT49/2014/TT-NHNN, chuẩn mực đối chiếu ca *"doanh thu thuần của ngân hàng"* & ROE TTM ngân hàng. | `https://www.vietcombank.com.vn` (Mục Nhà đầu tư) |
| 5 | **`TCB`** | Ngân hàng TMCP Kỹ thương Việt Nam | `bank` | Ngân hàng (TMCP Tư nhân) | Đại diện nhóm ngân hàng tư nhân quy mô lớn, cơ cấu thu nhập ngoài lãi cao (dễ kiểm chứng sự khác biệt NII vs TOI). | `https://techcombank.com` (Mục Quan hệ nhà đầu tư) |

---

## 3. Kế hoạch phạm vi thời gian Pilot

- **Cửa sổ dữ liệu tối thiểu 5 năm gần nhất:** Từ **Q1/2021** đến **Q3/2026** (23 kỳ quý: `2021Q1..2021Q4`, `2022Q1..2022Q4`, `2023Q1..2023Q4`, `2024Q1..2024Q4`, `2025Q1..2025Q4`, `2026Q1..2026Q3`), cộng thêm các báo cáo **Năm kiểm toán 2021–2025** và **Bán niên soát xét 2021–2026** để hỗ trợ tính TTM, kiểm chứng `Q4 = FY - 9M_YTD` (nếu cần) và đối chiếu `report_version`.
- **Để tính tăng trưởng YoY cho Q1/2021 (nếu hỏi) hoặc TTM tại Q1/2021:** Khuyến nghị kéo thêm dữ liệu nền **năm 2020** (`2020Q1..2020Q4`) trong ETL thử nghiệm để các phép biến đổi YoY/TTM trên cửa sổ 5 năm không bị thiếu đầu kỳ ở năm đầu.
