# Rà soát điều khoản sử dụng & quyền chia sẻ lại nguồn dữ liệu (TV1 — Tuần 1)

- **Người thực hiện:** Chi (TV1 — Data & ETL Engineer)
- **Ngày rà soát:** 2026-11-27
- **Phạm vi:** Nguồn dữ liệu tài chính có cấu trúc và BCTC gốc (PDF) phục vụ kho `fact_financials` của dự án *AI Financial Data Assistant*.

---

## 1. Mục tiêu rà soát

Theo Kế hoạch triển khai Giai đoạn 1 (Tuần 1–3) và yêu cầu tuân thủ bản quyền ở Giai đoạn 4 (mục 3.4 Đề cương v3), TV1 cần xác định rõ:
1. Nguồn dữ liệu cấu trúc chính nào đủ tin cậy cho chuỗi **≥5 năm theo quý** của rổ **VN30** (cả nhóm phi tài chính theo TT 200/2014/TT-BTC và nhóm ngân hàng theo TT 49/2014/TT-NHNN).
2. Phân biệt rạch ròi giữa **giấy phép phần mềm công cụ trích xuất** và **quyền sở hữu / chia sẻ lại dữ liệu**.
3. Chốt **chính sách lưu trữ nội bộ vs chia sẻ công khai** khi công bố repository nghiên cứu.

---

## 2. Đánh giá chi tiết từng nhóm nguồn dữ liệu

### 2.1. Công cụ `vnstock` và các API nguồn cấu trúc (VCI / TCBS / SSI)

| Khía cạnh | Đánh giá chi tiết |
|---|---|
| **Bản chất pháp lý của `vnstock`** | `vnstock` là thư viện Python chạy phía client (*client-side wrapper/automation toolkit*), không phải nhà cung cấp dữ liệu gốc. Giấy phép phần mềm mã nguồn mở (MIT/giấy phép đi kèm module) **không cấp quyền sở hữu hay quyền tái phân phối dữ liệu của bên thứ ba**. |
| **Nguồn dữ liệu phía sau** | Dữ liệu BCTC kéo qua `vnstock` (ví dụ cổng VCI/Vietcap, TCBS, SSI) là dữ liệu thuộc hệ thống của các công ty chứng khoán tương ứng. |
| **Điều khoản sử dụng (ToS)** | Cho phép sử dụng ở mức độ nghiên cứu cá nhân, học tập, phân tích nội bộ; tuân thủ giới hạn tốc độ gọi API (*rate limit*). **Không cho phép** cào hàng loạt để xây dịch vụ thương mại cạnh tranh hoặc phân phối lại nguyên bản cơ sở dữ liệu đã chuẩn hóa của bên thứ ba. |
| **Độ tin cậy cho ETL** | Tốt cho việc lấy nhanh chuỗi BCTC nhiều năm ở dạng bảng, nhưng có nguy cơ khác biệt quy ước gộp/đổi tên khoản mục hoặc làm tròn so với BCTC gốc -> **bắt buộc đối chiếu chéo với PDF gốc** (100 mẫu phân tầng ở GĐ2). |

### 2.2. Cổng tổng hợp tài chính (CafeF, VietstockFinance)

| Nguồn | Dữ liệu cấu trúc (Bảng số) | File BCTC gốc (PDF) | Quyền chia sẻ lại |
|---|---|---|---|
| **VietstockFinance** | Có hệ thống phân tách rõ tài khoản Free/Basic/Pro/Premium; kiểm soát bản quyền chặt với tính năng xuất Excel/Data Explorer và bảng chỉ số tính sẵn. | Cung cấp link/file công bố thông tin từ doanh nghiệp/Sở. | **Không** chia sẻ lại bảng dữ liệu giá trị gia tăng xuất từ Vietstock; nếu trích dẫn số liệu phải ghi rõ nguồn và chỉ dùng cho nghiên cứu. |
| **CafeF** | Bảng KQKD/CĐKT/LCTT trực tuyến thuộc cơ sở dữ liệu trình bày của VCCorp. | Cho phép tải miễn phí nhiều file PDF/Excel BCTC gốc do doanh nghiệp công bố. | **Không** sao chép/phân phối lại toàn bộ CSDL dạng bảng của CafeF; các **file PDF BCTC gốc** vốn là tài liệu công bố bắt buộc của doanh nghiệp. |

### 2.3. Nguồn sơ cấp chính thức (HOSE, HNX, UBCKNN, Cổng IR Doanh nghiệp)

| Nguồn | Bản chất dữ liệu | Điều khoản & Quyền chia sẻ lại |
|---|---|---|
| **HOSE / HNX / UBCKNN (IDS/CBTT)** | Dữ liệu công bố thông tin bắt buộc theo quy định pháp luật chứng khoán Việt Nam. | Số liệu tài chính gốc trong BCTC đã công bố là thông tin đại chúng phục vụ nhà đầu tư và thị trường. |
| **Website IR của doanh nghiệp** (FPT, Hòa Phát, MWG, Vietcombank, Techcombank...) | Nguồn gốc chuẩn xác nhất (có chữ ký, dấu mộc, ngày công bố chính thức, bản soát xét bán niên & kiểm toán năm, thuyết minh BCTC). | Được phép tải về, lưu trữ phục vụ nghiên cứu, trích dẫn chính xác `source_report_id` và dẫn liên kết tới bản công bố chính thức. |

---

## 3. Quyết định kiến trúc nguồn & chính sách chia sẻ của dự án

### 3.1. Phân tầng nguồn sử dụng trong Pipeline ETL
1. **Nguồn dữ liệu cấu trúc chính cho ETL tự động:** `vnstock` (ưu tiên adapter nguồn **VCI**, đối chiếu chéo **TCBS** khi có sai lệch) dùng để nạp nhanh dữ liệu số lịch sử ≥5 năm về lưu trữ cục bộ trong môi trường nghiên cứu của nhóm.
2. **Nguồn chân lý gốc (Ground Truth / Đối chiếu chéo):** **BCTC hợp nhất bản PDF gốc** tải từ **Cổng IR doanh nghiệp** (bổ sung từ **HOSE / UBCKNN / CafeF** đối với các kỳ cũ nếu trang IR doanh nghiệp thay đổi đường dẫn).
   - Mọi bản ghi trong `fact_financials` đều phải gắn `source_report_id`, `as_of_date`, `report_version` và `source_ref` để truy vết về BCTC gốc.

### 3.2. Quy tắc chia sẻ & công bố (Tuân thủ mục 3.4 Kế hoạch)
- **Không commit hoặc phát hành công khai** nguyên bản toàn bộ kho dữ liệu tải từ API của bên thứ ba (VCI/TCBS/Vietstock/CafeF) lên public repository.
- **Những gì được phép đưa lên Git / công bố:**
  1. Toàn bộ **mã nguồn ETL**, **schema `fact_financials`**, **script kiểm tra toàn vẹn & quy đổi YTD→Q**.
  2. Bảng **danh mục VN30 chốt ngày**, bảng **phân loại mã giữ/loại**, và **danh mục link/manifest BCTC gốc**.
  3. **Dữ liệu giả lập / mẫu minh họa nhỏ** phục vụ unit test và tái chạy demo minh họa (không phân phối hàng loạt CSDL thương mại của bên thứ ba).
  4. Bộ **Snapshot nội bộ** được lưu cục bộ (`.gitignore` với các file dữ liệu lớn/nguồn thứ ba nếu chưa có quyền phân phối lại) và kiểm soát bằng **SHA-256 hash** để TV2–TV5 tái lập chính xác cùng phiên bản dữ liệu.

---

## 4. Rủi ro nguồn dữ liệu & biện pháp giảm thiểu (Tuần 1–3)

| Rủi ro | Tác động | Biện pháp kiểm soát của TV1 |
|---|---|---|
| API của nguồn thứ ba (VCI/TCBS) đổi endpoint hoặc giới hạn rate limit | Gián đoạn bước kéo dữ liệu | Thiết kế lớp adapter tách rời (`source_adapter`), cache cục bộ dữ liệu thô theo mã, có cơ chế fallback sang file CSV/PDF gốc. |
| Số liệu trên API đã tự động *restate* hoặc làm tròn khác BCTC quý công bố lần đầu | Sai lệch `as_of_date` hoặc sai với Gold của TV4 | Lưu trường `report_version` và `is_restated`; đối chiếu bắt buộc 5 mã pilot với PDF gốc ở GĐ1 và 100 mẫu phân tầng ở GĐ2. |
| Doanh nghiệp thay đổi cấu trúc báo cáo giữa các kỳ (hoặc ngân hàng dùng mẫu TT49 khác phi tài chính TT200) | Lệch tên chỉ tiêu khi map sang `fact_financials` | Tách rõ `entity_group` (`non_financial` vs `bank`) ngay từ schema; không dùng chung mapping mù cho hai nhóm. |
