# Đặc tả Schema `fact_financials` & Quy ước ETL Pilot (TV1 — Tuần 1)

- **Người thực hiện:** Chi (TV1 — Data & ETL Engineer)
- **Phiên bản:** `v0.1-pilot` (Tuần 1 — Giai đoạn 1)
- **Phạm vi:** Chuẩn hóa dữ liệu BCTC dạng long format (`fact_financials`) cho 5 mã pilot (`FPT`, `HPG`, `MWG`, `VCB`, `TCB`) và làm nền cho Snapshot v1.0 ở Giai đoạn 2.

---

## 1. Cấu trúc bảng `fact_financials` (Long Format)

Mỗi dòng biểu diễn **một giá trị của một khoản mục tài chính**, tại một kỳ kế toán xác định, gắn với một phiên bản báo cáo và tọa độ nguồn cụ thể.

| Tên cột | Kiểu dữ liệu | Bắt buộc | Mô tả & Quy ước |
|---|---|---|---|
| `fact_id` | `string` | Có | Khóa định danh duy nhất của dòng dữ liệu (deterministic hash từ `ticker|statement_type|item_code|fiscal_year|fiscal_quarter|period_type|consolidation_scope|report_version`). |
| `ticker` | `string` | Có | Mã cổ phiếu viết hoa (`FPT`, `HPG`, `MWG`, `VCB`, `TCB`...). |
| `entity_group` | `string` | Có | Phân loại chuẩn BCTC: `non_financial` \| `bank`. |
| `statement_type` | `string` | Có | Loại báo cáo: `IS` (KQKD), `BS` (CĐKT), `CF` (LCTT). |
| `item_code` | `string` | Có | Mã chỉ tiêu chuẩn hóa nội bộ (xem Bảng 2). |
| `item_name_vi` | `string` | Có | Tên tiếng Việt theo BCTC chuẩn tương ứng. |
| `item_type` | `string` | Có | Bản chất kế toán: `flow` (lưu lượng theo kỳ: IS, CF) hoặc `stock` (thời điểm cuối kỳ: BS). |
| `fiscal_year` | `int` | Có | Năm tài chính (VD: `2025`, `2026`). |
| `fiscal_quarter` | `int` | Có | Quý tài chính `1..4` (dùng `0` nếu `period_type == "FY"`). |
| `period_type` | `string` | Có | `Q` (quý đơn lẻ), `YTD` (lũy kế từ đầu năm), `FY` (cả năm). |
| `period_start` | `date` (`YYYY-MM-DD`) | Có | Ngày bắt đầu kỳ (với `stock` có thể ghi ngày đầu kỳ báo cáo hoặc trùng `period_end` theo quy ước thống nhất — ở đây ghi ngày đầu kỳ quý/năm). |
| `period_end` | `date` (`YYYY-MM-DD`) | Có | Ngày kết thúc kỳ (VD: `2026-09-30` cho Q3/2026). |
| `value` | `float64` | Có | Giá trị số đã quy về **đơn vị chuẩn `VND`** (không làm tròn hàng tỷ trong kho gốc). |
| `unit` | `string` | Có | Luôn là `VND` sau bước chuẩn hóa ETL. |
| `consolidation_scope` | `string` | Có | Phạm vi hợp nhất: `consolidated` (ưu tiên mặc định) \| `parent` (công ty mẹ). |
| `as_of_date` | `date` (`YYYY-MM-DD`) | Có | Ngày công bố / phát hành báo cáo (để tránh rò rỉ dữ liệu tương lai tại `question_date`). |
| `report_version` | `string` | Có | Mức độ kiểm chứng: `original` (tự lập) \| `reviewed` (soát xét) \| `audited` (kiểm toán) \| `restated` (điều chỉnh hồi tố). |
| `is_restated` | `bool` | Có | `True` nếu là số liệu điều chỉnh lại từ kỳ sau / hồi tố; ngược lại `False`. |
| `source_report_id` | `string` | Có | Mã định danh báo cáo gốc, VD: `FPT_2026Q3_CONSOL_ORIG`. |
| `source_ref` | `string` | Có | Tọa độ truy vết về BCTC gốc (VD: `page=4;table=KQKD;row_code=10;label=Doanh thu thuần...` hoặc `vnstock:vci:2026Q3` trước khi đối chiếu PDF). |
| `derived_from` | `string` (JSON) | Không | Nếu giá trị quý `Q` được suy ra từ `YTD`/`FY` (VD: `Q3 = YTD_9M - YTD_6M` hoặc `Q4 = FY - YTD_9M`), lưu danh sách `fact_id` và công thức đã dùng; nếu lấy trực tiếp từ nguồn thì để rỗng `""`. |
| `ingested_at` | `datetime` (ISO-8601) | Có | Thời điểm chạy ETL nạp bản ghi. |

---

## 2. Ánh xạ chỉ tiêu Pilot (phục vụ 3 đại lượng của TV2)

Theo `kehoach.md` (mục 2.1 — TV2), giai đoạn pilot sử dụng 3 đại lượng:
1. **Doanh thu quý & tăng trưởng YoY** (nhóm phi tài chính)
2. **ROE TTM** (cả nhóm phi tài chính và ngân hàng)
3. **Ca xử lý "doanh thu thuần của ngân hàng"** (hệ thống phải trả cảnh báo / yêu cầu làm rõ, **không tự đánh đồng** với thu nhập lãi thuần).

Do đó, kho `fact_financials` Pilot tách biệt chỉ tiêu nguồn như sau:

| `entity_group` | `item_code` | `statement_type` | `item_type` | Tên khoản mục chuẩn trên BCTC | Ghi chú chuẩn kế toán |
|---|---|---|---|---|---|
| `non_financial` | `net_revenue` | `IS` | `flow` | Doanh thu thuần về bán hàng và cung cấp dịch vụ | Mã số `10` (TT 200/2014/TT-BTC). |
| `non_financial` | `net_income_parent` | `IS` | `flow` | Lợi nhuận sau thuế của cổ đông công ty mẹ | Mã số `61` (TT 200). Dùng ưu tiên cho ROE cổ đông mẹ (chờ TV2 chốt cuối cùng trong mục 4.3). |
| `non_financial` | `net_income_total` | `IS` | `flow` | Lợi nhuận sau thuế thu nhập doanh nghiệp | Mã số `60` (TT 200). Lưu song song để đối chiếu nếu cần. |
| `non_financial` | `equity_total` | `BS` | `stock` | Vốn chủ sở hữu | Mã số `400` (TT 200). |
| `non_financial` | `equity_parent` | `BS` | `stock` | Vốn chủ sở hữu thuộc cổ đông công ty mẹ | Mã số `410` trừ lợi ích CĐ không kiểm soát (`429` nếu tách riêng trên CĐKT) — phục vụ đối chiếu mẫu số ROE với `net_income_parent`. |
| `bank` | `net_interest_income` | `IS` | `flow` | Thu nhập lãi thuần | Mã số `I` (TT 49/2014/TT-NHNN). **Tuyệt đối không gán nhãn `net_revenue`.** |
| `bank` | `total_operating_income` | `IS` | `flow` | Tổng thu nhập hoạt động (TOI) | Tổng thu nhập lãi thuần + lãi/lỗ thuần dịch vụ, ngoại hối, chứng khoán, khác (TT 49). |
| `bank` | `net_income_parent` | `IS` | `flow` | Lợi nhuận sau thuế của cổ đông của Ngân hàng | Theo KQKD hợp nhất TT 49. |
| `bank` | `net_income_total` | `IS` | `flow` | Lợi nhuận sau thuế | Theo KQKD hợp nhất TT 49. |
| `bank` | `equity_total` | `BS` | `stock` | Vốn chủ sở hữu | Theo CĐKT hợp nhất TT 49. |

> **Nguyên tắc khóa ca ngân hàng:** Nhóm `bank` **không có** `item_code = "net_revenue"` trong `fact_financials`. Nhờ vậy, bất kỳ truy vấn nào tìm doanh thu thuần cho ngân hàng đều không thể vô tình đọc nhầm thu nhập lãi thuần ở tầng dữ liệu.

---

## 3. Quy tắc chuyển đổi `YTD → Q` (Quý đơn lẻ)

Một số BCTC (hoặc bản soát xét bán niên / kiểm toán năm) chỉ công bố số lũy kế (`YTD` 6 tháng, 9 tháng hoặc `FY` 12 tháng). Quy đổi sang quý đơn lẻ `Q` chỉ được phép thực hiện khi thỏa **tất cả 5 điều kiện**:
1. **`item_type == "flow"`**: Chỉ áp dụng cho khoản mục lưu lượng (`IS`, `CF`). **Cấm tuyệt đối** trừ kỳ đối với khoản mục thời điểm (`stock` trên `BS`).
2. **Cùng `ticker`, `item_code`, `fiscal_year`, `consolidation_scope`, `unit`**.
3. **Niên độ tài chính khớp**: Hiện cả 5 mã pilot (`FPT`, `HPG`, `MWG`, `VCB`, `TCB`) đều có năm tài chính kết thúc `31/12`.
4. **Tương thích phiên bản (`report_version`)**: Không tự ý lấy số kiểm toán năm (`audited`) trừ đi số tự lập 9 tháng (`original`) nếu giữa 2 kỳ có điều chỉnh hồi tố làm lệch chuẩn mà không gắn cờ cảnh báo; tốt nhất ghi rõ trong `derived_from` cả `source_report_id` của hai vế.
5. **Công thức chuẩn**:
   - `Q1 = YTD(Q1)` (hoặc dùng trực tiếp `Q1`)
   - `Q2 = YTD(6M) - YTD(Q1)` (hoặc `YTD(6M) - Q1`)
   - `Q3 = YTD(9M) - YTD(6M)`
   - `Q4 = FY - YTD(9M)`
   - Mỗi giá trị suy ra bắt buộc ghi JSON vào `derived_from`, ví dụ: `{"formula": "YTD_Q3 - YTD_Q2", "inputs": ["fact_id_ytd_q3", "fact_id_ytd_q2"], "version_pair": ["original", "reviewed"]}`.
