# Đặc tả quy tắc số liệu khó (4.3) và xử lý thời gian (4.4)

| | |
|---|---|
| **Phiên bản** | v1.0 — tích hợp đầy đủ vào Semantic Layer v1.0 (GĐ2). Thay đổi so với v0.1: R6 áp dụng cho mọi mẫu số bình quân; thêm R12 (xếp hạng), R13 (lan truyền trạng thái khi so sánh), R14 (ràng buộc kiểu phép biến đổi); T6–T7 đã cài đặt |
| **Người phụ trách** | TV2 (Semantic Layer & B0/C) |
| **Cài đặt tham chiếu** | [`src/fin_assistant/semantic/`](../../src/fin_assistant/semantic/) — mọi quy tắc dưới đây đều có unit test trong [`tests/semantic/`](../../tests/semantic/) |
| **Người dùng tài liệu** | TV1 (hợp đồng dữ liệu, mục 2), TV3 (output contract, mục 3), TV4 (hành động kỳ vọng khi viết câu hỏi, mục 3–5), TV5 (nhãn hành động & cảnh báo cụ thể, mục 3) |

> **Lưu ý về đánh số.** Kho mã chưa có bản Đề cương v3, nên các quy tắc được đánh số riêng: **R1–R11** cho số liệu khó (4.3) và **T1–T8** cho thời gian (4.4). Cần đối chiếu với Đề cương v3 trước khi đóng băng. Mọi ngưỡng nằm trong `RuleConfig` ([rules.py](../../src/fin_assistant/semantic/rules.py)). Khi đã chốt, nhóm đóng băng `RuleConfig` cùng Snapshot v1.0 và không sửa trong lúc chạy thí nghiệm.

---

## 1. Nguyên tắc chung

| # | Nguyên tắc | Hệ quả khi cài đặt |
|---|---|---|
| P1 | **Không trả số khi chỉ số không xác định hoặc thiếu đầu vào.** Thà báo thiếu còn hơn trả một con số sai mà không cảnh báo. | Hàm trả `status` khác `ok` và `value = None`; không có ngoại suy, nhân 4/3 hay lấy kỳ khác thay vào. |
| P2 | **Cảnh báo phải cụ thể**: nêu đúng mã, kỳ và đầu vào bị ảnh hưởng. | Mỗi `MetricWarning` mang `ticker`, `period`, `item_code`. Bộ chấm của TV5 chỉ công nhận cảnh báo loại này. |
| P3 | **Không thay thế chỉ tiêu một cách ngầm định.** | Ngân hàng hỏi "doanh thu thuần" → hỏi làm rõ (R9). |
| P4 | **Mọi con số đi kèm kỳ, công thức và nguồn.** | `MetricResult.period`, `formula`, `inputs[*].source_ref`. |
| P5 | **Quy ước nằm ở một chỗ.** | B0, B và C dùng chung thư viện này. Phương pháp A chỉ nhận mô tả công thức bằng văn bản, lấy từ chính tài liệu này. |

---

## 2. Hợp đồng dữ liệu đầu vào (đề xuất gửi TV1)

Thư viện đọc bảng long format `fact_financials` và bảng công ty. Dữ liệu vi phạm hợp đồng bị `FactStore` từ chối ngay (`DataContractError`), không tính tiếp.

### 2.1. Cột bắt buộc của `fact_financials`

| Cột | Kiểu | Quy ước |
|---|---|---|
| `ticker` | str | Phải có trong bảng công ty |
| `fiscal_year`, `fiscal_quarter` | int | Quý 1..4 của năm tài chính |
| `period_type` | `Q` \| `YTD` | `Q`: với `flow` là số **quý đơn lẻ**; với `stock` là **số dư cuối quý**. `YTD` (lũy kế từ đầu năm) chỉ dùng cho `flow` |
| `item_code` | str | Mã chuẩn hóa nội bộ (vd `IS.NET_REVENUE`). Xem [danh mục chỉ số](danh-muc-chi-so-de-xuat.md) |
| `item_type` | `flow` \| `stock` | Phải khớp danh mục |
| `value` | float | **Đơn vị đồng (VND)**. TV1 quy đổi từ triệu/tỷ trước khi bàn giao. Không để rỗng: thiếu thì bỏ dòng |
| `unit` | str | `VND` với chỉ tiêu tiền tệ |
| `scope` | `consolidated` \| `separate` | Báo cáo hợp nhất / riêng |
| `as_of_date` | date | Ngày **công bố** báo cáo chứa con số này |
| `report_version` | int | Tăng dần khi có bản công bố lại hoặc điều chỉnh |
| `source_ref` | str | Tọa độ ô số trên BCTC gốc (file, trang, dòng/mã số) |

Hai cột tùy chọn: `is_restated` (bool) và `derived_from` (str, mô tả cách suy ra, vd `FY2023 − 9T2023`).

**Bảng công ty:** `ticker`, `group` (`non_financial` \| `bank`). Cột `scope` là tùy chọn (mặc định `consolidated`).

### 2.2. Yêu cầu nghiệp vụ với dữ liệu

1. **Khóa duy nhất:** (`ticker`, kỳ, `period_type`, `item_code`, `scope`, `report_version`).
2. **Quý 4 đơn lẻ** của chỉ tiêu `flow`: lấy trực tiếp từ BCTC quý 4 nếu có. Nếu phải tính `FY − 9T`, TV1 ghi `derived_from`, và thư viện hiển thị một cảnh báo info `DERIVED_VALUE`.
3. **Điều chỉnh hồi tố:** thêm dòng mới với `report_version` lớn hơn, `as_of_date` là ngày công bố bản điều chỉnh, `is_restated = true`. **Không ghi đè dòng cũ.** Thư viện cần dòng cũ để trả lời đúng các câu hỏi đặt tại ngày trước khi điều chỉnh (T2).
4. **Ô trống trên BCTC:** dòng chỉ tiêu có trên mẫu biểu mà doanh nghiệp để trống được ghi `value = 0`, ví dụ lợi ích CĐ không kiểm soát (mã 429) của doanh nghiệp không có công ty con. Chỉ tiêu không thu thập được thì **không tạo dòng**. Nhờ vậy thư viện phân biệt được "bằng 0" với "thiếu".
5. **VCSH cổ đông mẹ:** nếu TV1 không tạo sẵn `BS.EQUITY_PARENT` thì thư viện tự tính `BS.EQUITY_TOTAL − BS.NCI` và yêu cầu có cả hai dòng.
6. **Phạm vi:** mặc định dùng báo cáo **hợp nhất**. Mã không lập báo cáo hợp nhất được khai `scope = separate` trong bảng công ty. Thư viện không trộn hai phạm vi cho cùng một mã.

---

## 3. Trạng thái kết quả ↔ hành động kỳ vọng

| `status` | Hành động hệ thống | Nhãn của TV5 | Có trả số? |
|---|---|---|---|
| `ok` | Trả số (có thể kèm cảnh báo) | trả số / cảnh báo | Có |
| `missing_data` | Báo thiếu dữ liệu, nêu rõ ô thiếu | báo thiếu | Không |
| `not_meaningful` | Báo chỉ số không xác định và nêu lý do | cảnh báo | Không |
| `needs_clarification` | Hỏi làm rõ, đưa danh sách lựa chọn (`candidates`) | hỏi làm rõ | Không |
| `not_applicable` | Từ chối có lý do (chỉ số không áp dụng cho nhóm, hoặc mã ngoài phạm vi) | từ chối | Không |
| `empty_valid` | Kết quả lọc có 0 dòng **hợp lệ** | 0 dòng | Có (tập rỗng) |

**Mã cảnh báo** (`WarnCode`). Cảnh báo mức `info` chỉ để minh bạch và không đổi trạng thái.

| Mã | Mức | Khi nào |
|---|---|---|
| `missing_input` | warning | Thiếu một ô đầu vào (nêu `item_code` và kỳ) |
| `not_yet_published` | warning | Kỳ chưa kết thúc hoặc chưa công bố tại ngày hỏi (T3) |
| `out_of_scope_ticker` | warning | Mã không có trong dữ liệu |
| `negative_equity` | warning | Có điểm VCSH ≤ 0 (R4) |
| `non_positive_base` | warning | Kỳ gốc của phép tăng trưởng ≤ 0 (R1) |
| `denominator_near_zero` | warning | Mẫu số dương nhưng < ngưỡng (R2) |
| `extreme_value` | warning | \|kết quả\| > ngưỡng; vẫn trả số (R3) |
| `fallback_ending_equity` | warning | Đã dùng VCSH cuối kỳ thay cho bình quân (R6, chỉ khi bật cờ) |
| `bank_no_net_revenue` | warning | Ngân hàng + "doanh thu thuần" (R9) |
| `metric_not_applicable` | warning | Chỉ số không áp dụng cho nhóm doanh nghiệp (R10) |
| `restated_value` | info | Ô số là bản điều chỉnh hồi tố (T2) |
| `derived_value` | info | Ô số là số suy ra (Q4 = FY − 9T; VCSH mẹ = 400 − 429) |
| `newer_period_available` | info | Bảng đa mã dùng kỳ chung, mã này đã có kỳ mới hơn (T5) |
| `mixed_periods` | warning | Bảng đa mã theo chính sách từng mã và các mã lệch kỳ (T5) |
| `partial_coverage` | warning | Một phần các mã không có kết quả số |
| `excluded_not_meaningful` | warning | Mã bị loại khỏi phép lọc vì chỉ số không xác định hoặc không áp dụng (R8) |

---

## 4. Quy tắc số liệu khó (mục 4.3)

### R1 — Mẫu số (kỳ gốc) ≤ 0
- **Áp dụng:** mọi phép tăng trưởng tương đối `(x_t − x_gốc) / x_gốc` và mọi tỷ số có mẫu số tiền tệ.
- **Quy tắc:** mẫu số ≤ 0 thì trả `not_meaningful` kèm `non_positive_base`. Riêng VCSH thì dùng mã `negative_equity` (R4).
- **Vẫn cung cấp:** chênh lệch tuyệt đối `details.abs_change`, để giao diện có thể nói "tăng 100 tỷ đồng từ mức 0".
- **Lý do:** gốc âm làm đảo dấu kết quả (lỗ ít đi lại thành "tăng trưởng âm"); gốc bằng 0 thì phép chia không xác định.

### R2 — Mẫu số gần 0
- **Quy tắc:** nếu `0 < mẫu số < near_zero_abs_vnd` thì trả `not_meaningful` kèm `denominator_near_zero`.
- **Ngưỡng đề xuất:** **1 tỷ đồng**. Với quy mô VN30, doanh thu hoặc VCSH quý dưới 1 tỷ đồng thực chất là bằng 0, và tỷ lệ tính ra (hàng nghìn %) không mang thông tin.
- **Vì sao dùng ngưỡng tuyệt đối:** ngưỡng tương đối (so với tử số) làm kết quả phụ thuộc vào chính đại lượng đang đo, khó giải thích. Phần "lớn bất thường" đã có R3 xử lý.

### R3 — Giá trị cực đoan
- **Quy tắc:** nếu mẫu số hợp lệ nhưng \|kết quả\| > `extreme_ratio` (đề xuất **10**, tức 1.000%) thì **vẫn trả số** với `ok` và gắn `extreme_value`.
- **Lý do:** con số đúng về số học, ví dụ doanh thu bất động sản bàn giao dồn vào một quý. Không trả số sẽ làm giảm tỷ lệ trả lời mà không có lý do chính đáng.

### R4 — Vốn chủ sở hữu ≤ 0
- **Quy tắc:** nếu **bất kỳ điểm VCSH nào** được dùng để tính bình quân ≤ 0 thì ROE (và mọi tỷ số chia cho VCSH) trả `not_meaningful` kèm `negative_equity`, nêu kỳ và giá trị VCSH.
- **Phân biệt:** ROE âm khi VCSH dương (doanh nghiệp lỗ) là **hợp lệ**, trả số bình thường.
- **Cặp đối lập bắt buộc:** doanh nghiệp lỗ và VCSH âm cho tỷ số *dương* (−200 / −600 ≈ +33%). Kết quả này **phải** bị chặn (test `test_negative_equity_and_loss_do_not_produce_positive_roe`).
- **Xếp hạng và lọc:** mã có ROE không xác định bị loại khỏi bảng xếp hạng hoặc phép lọc và được liệt kê trong `excluded` (R8). Không mã nào được "lọt" vào điều kiện `ROE > x`.

### R5 — Định nghĩa ROE TTM
```
ROE_TTM(t) = Σ LNST cổ đông công ty mẹ (t−3 … t) / VCSH cổ đông công ty mẹ bình quân
VCSH bình quân (mặc định, 2 điểm) = (VCSH cuối quý t−4 + VCSH cuối quý t) / 2
VCSH bình quân (tùy chọn, 5 điểm) = trung bình VCSH cuối các quý t−4, t−3, t−2, t−1, t
```
- **Tử số và mẫu số cùng thuộc cổ đông công ty mẹ.**
  - Tử số: mã 61 trên B02-DN/HN.
  - Mẫu số: mã 400 trừ mã 429 trên B01-DN/HN.
  - Các mã 61, 62, 429 chỉ có trên mẫu **hợp nhất** (TT202/2014, sửa đổi bởi TT43/2026; mã không đổi). Với BCTC riêng, LNST cổ đông mẹ = mã 60 và lợi ích CĐ không kiểm soát = 0.
  - Không lấy LNST toàn bộ (mã 60 trên báo cáo hợp nhất) chia cho VCSH công ty mẹ, vì như vậy tử và mẫu không cùng chủ sở hữu.
  - Quy ước này trùng với cách Vietstock tính ROEA (LNST cổ đông mẹ / bình quân đầu–cuối kỳ của VCSH − lợi ích CĐ không kiểm soát).
- **Vì sao mặc định 2 điểm:** khớp với cách tính trên BCTC năm (bình quân đầu kỳ/cuối kỳ), chỉ cần 2 ô số nên ít rủi ro thiếu dữ liệu, và dễ để TV4 tính tay Gold. Bản 5 điểm được giữ để đối chiếu với nguồn dữ liệu thương mại.
- **Áp dụng cho cả ngân hàng:** cùng công thức, cùng mã chuẩn hóa (`IS.NPAT_PARENT`, `BS.EQUITY_PARENT`).

### R6 — Thiếu số dư đầu kỳ (VCSH, tổng tài sản)
- Áp dụng cho mọi mẫu số bình quân: VCSH cổ đông mẹ (ROE) và tổng tài sản (ROA).
- **Mặc định:** `missing_data`. Cảnh báo `missing_input` nêu trường thiếu (`BS.EQUITY_PARENT`, `BS.TOTAL_ASSETS`) và kỳ thiếu, ví dụ Q3/2023.
- **Tùy chọn** `allow_ending_equity_fallback = True`: dùng **số cuối kỳ** thay cho bình quân, trả `ok` kèm `fallback_ending_equity`, và `details.avg_method = "ending_only"`.
- **Đề xuất cho thí nghiệm chính: giữ mặc định (tắt).** Fallback làm thay đổi định nghĩa chỉ số. Nếu bật, Gold của TV4 phải dùng cùng quy ước.

### R7 — Thiếu quý trong cửa sổ TTM
- Thiếu **bất kỳ** quý LNST nào trong 4 quý thì trả `missing_data` và nêu đúng quý thiếu.
- **Không** quy đổi năm từ ít hơn 4 quý (nhân 4/3, nhân 2…). Cờ fallback ở R6 cũng không bỏ qua được quy tắc này.

### R8 — Kết quả lọc 0 dòng
Phép lọc `screen(metric, tickers, op, threshold)`, với `op` thuộc `>`, `>=`, `<`, `<=`:

| Tình huống | `status` |
|---|---|
| Có ≥ 1 mã thỏa | `ok` (mã không đánh giá được nằm trong `excluded` kèm cảnh báo) |
| 0 mã thỏa, mọi mã đều đánh giá được | **`empty_valid`**: trả lời "không có mã nào" |
| 0 mã thỏa, có mã chỉ bị loại vì R4/R10 (không xác định hoặc không áp dụng) | `empty_valid` + `excluded_not_meaningful` liệt kê mã bị loại |
| 0 mã thỏa, có mã **thiếu dữ liệu** | **`missing_data`**: **không được** khẳng định "không có mã nào" |
| Có mã cần làm rõ chỉ tiêu (R9) | `needs_clarification` |
| Danh sách mã rỗng | `missing_data` |

Đây là cặp đối lập "rỗng hợp lệ vs thiếu mẫu số" của Benchmark.

### R9 — "Doanh thu thuần" của ngân hàng
- Báo cáo kết quả hoạt động của tổ chức tín dụng (mẫu **B03/TCTD**, QĐ16/2007 sửa đổi bởi TT49/2014, TT22/2017, TT27/2021) **không có** dòng "Doanh thu thuần". Mẫu này cũng không có cột mã số, chỉ đánh số thứ tự I–XV. "Tổng thu nhập hoạt động" không phải một dòng trên mẫu mà là tổng I + … + VII do người phân tích tính. Khi chỉ số `net_revenue` (kể cả biến đổi YoY, bảng đa mã, phép lọc) được hỏi cho mã thuộc nhóm `bank`, thư viện trả `needs_clarification`, kèm `bank_no_net_revenue` và 3 lựa chọn:
  1. `bank_nii`: Thu nhập lãi thuần;
  2. `bank_toi`: Tổng thu nhập hoạt động (tổng mục I–VII);
  3. `bank_interest_income`: Thu nhập lãi và các khoản thu nhập tương tự.
- Thư viện **không đọc bất kỳ ô số nào** trong ca này (`inputs = ()`). Như vậy không thể có chuyện thay ngầm bằng thu nhập lãi thuần.
- Kiểm tra này chạy **trước** khi xác định kỳ. Câu hỏi về nghĩa được giải quyết trước câu hỏi về dữ liệu.
- Bảng đa mã có cả ngân hàng và doanh nghiệp phi tài chính: trạng thái chung là `needs_clarification`, nhưng các dòng phi tài chính vẫn được tính sẵn để giao diện hiển thị cùng câu hỏi lại.

### R10 — Không áp dụng / ngoài phạm vi
- Chỉ số không xác định cho nhóm doanh nghiệp, ví dụ `bank_nii` cho doanh nghiệp phi tài chính, thì trả `not_applicable` kèm `metric_not_applicable`.
- Mã không có trong dữ liệu (ngoài VN30 đủ điều kiện) thì trả `not_applicable` kèm `out_of_scope_ticker`.
- Chỉ số hoặc phép biến đổi không có trong danh mục là **lỗi lập trình** (`UnknownMetricError`). B0 và bộ thực thi C phải kiểm tra theo danh mục trước khi gọi. Các câu mà C không biểu đạt được thì ghi nhận riêng theo mục 6.2 của Đề cương.

### R11 — Đơn vị, dạng số, làm tròn
- **Lưu trữ:** tiền tệ tính bằng **đồng** (float64). Tỷ lệ lưu ở dạng **phân số** (`0.25`), `unit = "ratio"`.
- **Phân biệt hai đơn vị:** **% tăng trưởng** (`ratio`, ví dụ +25%) khác với **chênh lệch điểm phần trăm** (`pp`, ví dụ biên LN tăng 1,2 điểm %). Ràng buộc kiểu ở R14 bảo đảm không thể tính nhầm loại này thành loại kia.
- Hệ số nợ phải trả / VCSH dùng đơn vị `times` (lần).
- **Hiển thị** ([fmt.py](../../src/fin_assistant/semantic/fmt.py)): tiền tệ ở đơn vị tỷ đồng, 1 chữ số thập phân; tỷ lệ 2 chữ số thập phân; dấu chấm phân tách nghìn, dấu phẩy thập phân. **Chỉ làm tròn khi hiển thị**, không làm tròn trong tính toán.
- **Gợi ý dung sai chấm cho TV5:** sai lệch tương đối ≤ 0,5% với tiền tệ; ≤ 0,05 điểm % với tỷ lệ. TV5 chốt con số cuối cùng.

### R12 — Xếp hạng
- `rank(metric, tickers, period, order, top_n)` chỉ xếp các dòng `ok`, **trên cùng một kỳ** (T5).
- Mã có chỉ số không xác định hoặc không áp dụng bị loại và được liệt kê (`excluded_not_meaningful`). Ví dụ: mã vốn chủ âm không bao giờ xuất hiện trong "ROE cao nhất".
- Có mã **thiếu dữ liệu** thì vẫn xếp phần còn lại nhưng gắn `partial_coverage` nêu tên mã: kết quả "cao nhất" có thể đổi nếu mã đó có dữ liệu.
- Hai mã bằng nhau giữ thứ tự theo mã cổ phiếu (ổn định, tái lập được). Mỗi dòng có `details.rank`.
- Có mã cần làm rõ (R9) → `needs_clarification`. Không mã nào xếp được → trạng thái theo thứ tự ưu tiên: cần làm rõ > thiếu dữ liệu > không xác định > không áp dụng.

### R13 — Lan truyền trạng thái khi so sánh hai kỳ
- Với YoY, QoQ, điểm %: nếu **một trong hai đầu** là `not_meaningful` thì kết quả là `not_meaningful`, kể cả khi đầu kia thiếu dữ liệu. Có thêm dữ liệu cũng không làm phép so sánh có nghĩa.
- Nếu không đầu nào `not_meaningful` nhưng có đầu thiếu dữ liệu thì trả `missing_data`.
- Cả hai đầu `ok` thì áp R1–R3 cho tăng trưởng % (tiền tệ), hoặc lấy hiệu trực tiếp cho điểm % (tỷ lệ).

### R14 — Ràng buộc kiểu giữa chỉ số và phép biến đổi
Cú pháp phép biến đổi: `[ytd|ttm][_][yoy|qoq][_pp]`.

| Loại chỉ số | Cửa sổ hợp lệ | So sánh hợp lệ |
|---|---|---|
| Tiền tệ flow (doanh thu, LN…) | quý, `ytd`, `ttm` | `yoy`, `qoq` → % tăng trưởng |
| Tiền tệ stock (tài sản, nợ, VCSH) | chỉ quý (số cuối kỳ) | `yoy`, `qoq` → % tăng trưởng |
| Tỷ lệ theo cửa sổ (biên LN) | quý, `ytd`, `ttm` (tỷ số của tổng, **không** phải trung bình các tỷ số) | **chỉ** `yoy_pp`, `qoq_pp` |
| ROE, ROA (TTM cố định) | chỉ quý | **chỉ** `yoy_pp`, `qoq_pp` |
| Nợ phải trả / VCSH (lần) | chỉ quý | chưa hỗ trợ ở v1.0 |

Thêm hai ràng buộc:
- Lũy kế chỉ so sánh với cùng kỳ năm trước (`ytd_qoq` không hợp lệ).
- Vi phạm ràng buộc → `TransformError`. Bộ thực thi truy vấn chuyển lỗi này thành `QueryError`, và trường hợp đó được ghi nhận là "không biểu đạt được".

---

## 5. Quy tắc thời gian (mục 4.4)

### T1 — Ngày hỏi (`as_of` = `question_date`)
Thư viện chỉ "thấy" các dòng có `as_of_date ≤ as_of`. `as_of = None` nghĩa là dùng toàn bộ Snapshot (để phát triển; **không dùng khi chấm**). Mỗi câu trong Benchmark phải có `question_date`.

### T2 — Phiên bản và điều chỉnh hồi tố
- Với mỗi ô số, lấy phiên bản **công bố muộn nhất nhưng không sau ngày hỏi**.
- Phép so sánh cùng kỳ (YoY) lấy kỳ gốc theo đúng quy tắc trên. Nếu kỳ gốc đã được điều chỉnh trước ngày hỏi thì dùng số **đã điều chỉnh** (khớp với cột "kỳ trước" trên BCTC hiện hành) và gắn `restated_value` (info).
- Hỏi tại một ngày **trước** khi có bản điều chỉnh thì phải ra số cũ. Test: `test_restated_base_is_used_and_disclosed`.

### T3 — "Chưa công bố" khác "thiếu dữ liệu"
- Kỳ chưa kết thúc tại ngày hỏi, hoặc đã có trong kho nhưng công bố sau ngày hỏi: trả `not_yet_published`.
- Kỳ đã công bố nhưng không có ô cần dùng: trả `missing_input`.
- Cả hai đều cho `missing_data`, nhưng thông điệp khác nhau. Benchmark có thể dùng cặp này để kiểm tra hành vi.

### T4 — "Kỳ gần nhất" khi hỏi **một mã**
- Là **quý mới nhất mà mã đã công bố BCTC** (có ít nhất một dòng quý) tính tới ngày hỏi.
- Nếu kỳ đó thiếu đầu vào của chỉ số được hỏi thì trả `missing_data`. Thư viện **không tự lùi về kỳ trước**, vì làm vậy người dùng sẽ nhận số của một kỳ khác mà không biết.
- Kỳ đã xác định luôn được hiển thị cạnh con số (`period`). `details.period_resolved_from = "latest"` cho biết kỳ được suy ra.

### T5 — "Kỳ gần nhất" khi hỏi **nhiều mã**
- **Mặc định `common`:** dùng **kỳ chung gần nhất**, tức kỳ nhỏ nhất trong các "kỳ gần nhất" của từng mã có dữ liệu. Mã nào đã có kỳ mới hơn được gắn `newer_period_available` (info).
- **Vì sao chọn `common`:** bảng so sánh hoặc xếp hạng chỉ có nghĩa khi các mã ở cùng kỳ. Trộn Q4 của mã A với Q3 của mã B là lỗi ngữ nghĩa mà Benchmark muốn bắt.
- **Tùy chọn `per_ticker`:** mỗi mã dùng kỳ gần nhất của riêng nó. Nếu các kỳ lệch nhau thì gắn `mixed_periods` (warning).
- Mã chưa có BCTC nào vẫn **giữ dòng** trong bảng với `missing_data`, không bị bỏ đi một cách im lặng.

### T6 — Quý đơn lẻ và lũy kế
- "Quý 3", "Q3" → quý đơn lẻ (`period_type = Q`). "9 tháng", "lũy kế", "từ đầu năm" → `YTD`.
- Chuyển YTD sang quý (`Q_t = YTD_t − YTD_{t−1}`) chỉ áp dụng cho `flow` và do TV1 thực hiện trong ETL (ghi `derived_from`). Chỉ tiêu `stock` không có lũy kế.
- **Lũy kế (`ytd`):** ưu tiên dòng `period_type = YTD` do TV1 nạp **đúng như cột "Lũy kế từ đầu năm" trên B02a-DN**, để khớp với số mà TV4 đọc khi tính Gold. Nếu không có dòng này thì cộng các quý Q1..t (thiếu quý nào thì trả `missing_data`) và gắn `derived_value` (info).
- **Cả năm** = `ytd` tại Q4.
- Cặp đối lập "Q3 vs lũy kế 9 tháng" có test: `test_ytd_yoy_uses_reported_cumulative_columns`.

### T7 — Phép biến đổi theo thời gian
| Phép | Định nghĩa | Trạng thái |
|---|---|---|
| YoY | so với **cùng quý năm trước** (t−4), cùng cửa sổ | ✅ v1.0 |
| QoQ | so với **quý liền trước** (t−1) | ✅ v1.0 |
| TTM | tổng 4 quý liên tiếp t−3..t (chỉ với `flow`) | ✅ v1.0 |
| YTD | lũy kế Q1..t của cùng năm tài chính (T6) | ✅ v1.0 |
| Điểm % | hiệu hai tỷ lệ (`yoy_pp`, `qoq_pp`) | ✅ v1.0 |
| Xếp hạng / lọc | R12 / R8 | ✅ v1.0 |

### T8 — Năm tài chính
Giả định năm tài chính trùng năm dương lịch với toàn bộ VN30 trong phạm vi. TV1 kiểm tra khi nạp dữ liệu. Nếu có ngoại lệ, mã đó được đánh dấu trong bảng công ty và loại khỏi các phép so sánh cùng kỳ đa mã cho tới khi có quy tắc riêng.

---

## 6. Thứ tự kiểm tra trong `get_metric`

1. Chỉ số có trong danh mục không? Nếu không → `UnknownMetricError`. Phép biến đổi có hợp lệ với chỉ số không (R14)? Nếu không → `TransformError`.
2. Mã có trong dữ liệu không? Nếu không → `not_applicable` (R10).
3. Ngân hàng + `net_revenue`? → `needs_clarification` (R9).
4. Chỉ số có áp dụng cho nhóm của mã không? Nếu không → `not_applicable` (R10).
5. Xác định kỳ: kỳ tường minh, hoặc `latest` theo T4. Không có kỳ nào → `missing_data`.
6. Đọc ô số theo T1–T3, rồi áp R1–R7.

Thứ tự này cố định để các phương pháp B0, B, C cho cùng một hành vi trên cùng một câu.

---

## 7. Ví dụ minh họa (dữ liệu giả lập trong `tests/semantic/conftest.py`)

| Lời gọi | Kết quả |
|---|---|
| `get_metric(s, "net_revenue", "AAA", "2024Q3", transform="yoy")` | `ok`, 0,25 (+25%), kỳ gốc Q3/2023 |
| `get_metric(s, "net_revenue", "CCC", "2024Q1", transform="yoy")` | `not_meaningful`, `non_positive_base` (kỳ gốc = 0); `abs_change` = 100 tỷ |
| `get_metric(s, "net_revenue", "CCC", "2024Q2", transform="yoy")` | `ok`, 24,0 (+2.400%), kèm `extreme_value` |
| `get_metric(s, "roe_ttm", "AAA", "2024Q3")` | `ok`, 530 / 5.400 ≈ 9,81% |
| `get_metric(s, "roe_ttm", "DDD", "2024Q3")` | `not_meaningful`, `negative_equity` (dù tỷ số "dương") |
| `get_metric(s, "roe_ttm", "EEE", "2024Q3")` | `missing_data`, thiếu `BS.EQUITY_PARENT` Q3/2023 |
| `get_metric(s, "net_revenue", "NHA", "latest")` | `needs_clarification`, candidates = NII / TOI / thu nhập lãi |
| `get_metric_multi(s, "roe_ttm", ["AAA","NHA"], "latest", as_of="2025-02-15")` | cả hai ở Q3/2024; AAA kèm `newer_period_available` (đã có Q4/2024) |
| `screen(s, "roe_ttm", ["AAA","EEE"], ">", 0.5, "2024Q3")` | `missing_data`, không phải `empty_valid` |

---

## 8. Các điểm cần nhóm quyết tại Cổng Giai đoạn 1

| # | Quyết định | Đề xuất của TV2 | Ảnh hưởng tới |
|---|---|---|---|
| D1 | Ngưỡng mẫu số gần 0 (R2) | 1 tỷ đồng | Gold (TV4), bộ chấm (TV5) |
| D2 | Ngưỡng giá trị cực đoan (R3) | 10 (1.000%) | Cảnh báo |
| D3 | VCSH bình quân (R5) | 2 điểm | Gold ROE |
| D4 | Fallback VCSH cuối kỳ (R6) | Tắt | Tỷ lệ trả lời ROE |
| D5 | Kỳ gần nhất đa mã (T5) | `common` | Câu so sánh/xếp hạng |
| D6 | Nguồn ngày công bố `as_of_date` | Ngày công bố thực tế trên HOSE/website doanh nghiệp. Nếu không thu thập được thì dùng **hạn chót theo TT96/2020** (VBHN 10/VBHN-BTC/2026) kèm cờ `as_of_is_estimated`: quý +20 ngày (riêng) / +30 ngày (hợp nhất); bán niên soát xét +45 / +60 ngày; năm kiểm toán +90 ngày | TV1, T1 |
| D7 | Giữ ngân hàng trong mẫu chính? | Giữ, nếu đủ dữ liệu cho NII/TOI/LNST/VCSH từ thân báo cáo | Phạm vi GĐ2 |
| D8 | Mẫu biểu đổi từ năm tài chính 2026: TT200 → **TT99/2025** (riêng), TT202 → **TT202 sửa bởi TT43/2026** (hợp nhất) | Dùng mã chuẩn hóa nội bộ. TV1 chọn bảng ánh xạ theo **năm tài chính + loại báo cáo**, không chỉ theo số mã. Ví dụ: tổng tài sản 270 → **280**; mã 21–24 trên B02 đổi nghĩa; lãi/lỗ công ty liên doanh liên kết trên B02/HN chuyển từ mã 24 sang 27 | ETL (TV1) |
| D9 | BCTC năm kiểm toán điều chỉnh số Q4 đã công bố | Ghi thành phiên bản mới của Q4 (`report_version` + 1, `is_restated`). Câu hỏi đặt trước ngày công bố BCTC kiểm toán thì vẫn ra số Q4 cũ (T2) | TV1, TV4 |

---

## 9. Truy vết quy tắc → test

| Quy tắc | Test (trong `tests/semantic/`) |
|---|---|
| R1 | `test_growth_non_positive_base_is_not_meaningful`, `TestNetRevenue::test_yoy_zero_base_not_meaningful` |
| R2 | `test_growth_near_zero_base_is_not_meaningful`, `test_check_denominator`, `TestRoeTtm::test_near_zero_equity` |
| R3 | `test_growth_extreme_value_still_answers_with_warning`, `TestNetRevenue::test_yoy_extreme_value_answers_with_warning` |
| R4 | `TestRoeTtm::test_negative_ending_equity_not_meaningful`, `…_negative_equity_and_loss_do_not_produce_positive_roe`, `…_negative_roe_with_positive_equity_is_valid` |
| R5 | `TestRoeTtm::test_non_financial_two_point`, `…_five_point_average`, `…_bank_two_point`, `…_bank_five_point`, `…_equity_parent_derived_from_total_minus_nci` |
| R6 | `…_missing_beginning_equity_default_is_missing`, `…_missing_beginning_equity_bank`, `…_missing_beginning_equity_with_explicit_fallback` |
| R7 | `…_missing_quarter_of_npat_is_named`, `…_no_annualisation_from_partial_year`, `…_fallback_does_not_hide_missing_npat` |
| R8 | `TestScreenZeroRows::*` |
| R9 | `TestBankNetRevenue::*`, `TestLatestMulti::test_bank_in_revenue_comparison_triggers_clarification` |
| R10 | `TestDispatch::test_out_of_scope_ticker`, `TestBankNetRevenue::test_bank_metric_not_applicable_to_non_financial` |
| T1–T3 | `test_store.py::test_lookup_respects_as_of_and_picks_latest_version`, `TestNetRevenue::test_not_yet_published_differs_from_missing`, `…_quarter_not_ended_at_question_date`, `…_restated_base_is_used_and_disclosed` |
| T4 | `test_store.py::test_latest_period_single_ticker`, `TestDispatch::test_latest_single_ticker_uses_question_date` |
| T5 | `TestLatestMulti::*` |
| T6 | `TestNetRevenue::test_derived_q4_is_disclosed`, `TestWindows::*`, `test_ytd_yoy_uses_reported_cumulative_columns` |
| T7 | `TestChanges::*`, `TestDerived::test_gross_margin_windows` |
| R12 | `TestRank::*` |
| R13 | `TestChanges::test_change_propagates_not_meaningful`, `…_roe_yoy_pp_needs_both_ends` |
| R14 | `test_check_transform_type_rules`, `test_parse_transform_rejects` |

Báo cáo coverage đầy đủ: [docs/reports/coverage-semantic-b0-v1.0.md](../reports/coverage-semantic-b0-v1.0.md).
