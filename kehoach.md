# Kế hoạch triển khai chi tiết — AI Financial Data Assistant (4 Giai đoạn, 5 Thành viên)

> **Cơ sở lập kế hoạch:** Dựa trên `AI_Financial_Data_Assistant_Proposal_v3.md`.
> **Nguyên tắc vận hành:** Mỗi giai đoạn kéo dài ~3–4 tuần (tổng ~14 tuần). Trong từng giai đoạn, **5 thành viên làm việc độc lập theo luồng riêng**, chỉ sử dụng đầu vào đã đóng băng từ cổng giai đoạn trước. Cuối mỗi giai đoạn có **Phiên tổng kết & Cổng kiểm duyệt (Phase Gate)** để nghiệm thu, đồng bộ gói bàn giao và quyết định chuyển giai đoạn.

---

## 0. Điều chỉnh phạm vi do không thực hiện khảo sát

Vì bỏ bước khảo sát người dùng bên ngoài (mục 8.1 của Đề cương v3), kế hoạch điều chỉnh 3 điểm sau để vẫn giữ nguyên tính chặt chẽ phương pháp luận:

1. **Chọn bộ 10–15 chỉ số:** Chốt trực tiếp từ cấu trúc chuẩn BCTC Việt Nam (phi tài chính và ngân hàng) kết hợp đối chiếu các công trình gần nhất (ViNumQA, ViFinQA, VCBS AI) thay vì thống kê từ khảo sát.
2. **Nguồn Benchmark (≥100 câu):** Nhóm tự xây dựng có hệ thống theo **họ câu**, cặp đối lập và các tình huống số liệu khó (không áp dụng tiêu chí ≥30% câu từ khảo sát; ghi rõ giới hạn này trong báo cáo).
3. **Đánh giá RQ3 (mục 8.4, quy tắc số 5):** Do không có "ý định đã xác nhận" từ người dùng thật, **không dùng đáp án do nhóm tự đoán để kết luận chính sách nào hiểu người dùng hơn**. Hệ thống chỉ được đánh giá về:
   - Khả năng **phát hiện câu mơ hồ** trên tập câu mơ hồ được gắn nhãn,
   - Tỷ lệ **hỏi lại không cần thiết** trên tập câu đã rõ nghĩa,
   - Độ chính xác và độ minh bạch khi hiển thị giả định mặc định vs hỏi làm rõ 1 lượt.

---

## 1. Phân công vai trò cố định cho 5 thành viên

Việc phân vai được thiết kế để bảo đảm nguyên tắc **tách biệt độc lập** của Đề cương v3 (người viết bộ hàm không viết gold, người giữ Test tách khỏi người tối ưu mô hình, người kiểm tra độc lập với người gán nhãn): chi, cúc, lanh, hiền, linh

| Mã | Vai trò | Trọng tâm trách nhiệm xuyên suốt |
|----|---------|----------------------------------|
| **TV1** | **Data & ETL Engineer** | Nguồn dữ liệu, danh sách VN30 đủ điều kiện, schema `fact_financials`, quy đổi YTD→Q, quản lý `as_of_date` & `report_version`, đóng băng Snapshot. |
| **TV2** | **Semantic Layer & B0/C Engineer** | Đặc tả quy tắc số liệu khó & thời gian, thư viện hàm chỉ số + unit test, baseline quy tắc **B0**, phương pháp truy vấn có cấu trúc **C**. |
| **TV3** | **LLM Pipeline, Sandbox & Demo Engineer** | Hạ tầng gọi LLM (cố định seed/version/log), sandbox thực thi an toàn, phương pháp **A** & **B** (và B1/D nếu kịp), giao diện **Demo truy vết nguồn**. |
| **TV4** | **Benchmark Lead & Test Keeper** | Đối chiếu tài liệu, thiết kế họ câu & cặp đối lập, **giữ kín tập Test chính**, tính **Gold độc lập từ báo cáo gốc** (không dùng code của TV2). |
| **TV5** | **Evaluation, QA & Statistical Auditor** | Bộ chấm 4 đại lượng, "tấn công bộ chấm", kiểm tra chéo Gold (Cohen's kappa), kiểm toán 100 mẫu dữ liệu phân tầng, test sandbox, thống kê Bootstrap & tái lập kết quả. |

---

## 2. Giai đoạn 1: Khởi tạo, Pilot (5 mã, 30 câu) & Khóa bộ chấm (Tuần 1–3)

**Mục tiêu giai đoạn:** Xác minh tính khả thi dữ liệu & tài liệu liên quan; hoàn thành pilot trên 5 mã (3 phi tài chính, 2 ngân hàng) với 3 đại lượng; xây dựng và kiểm tra độ bền của Bộ chấm trước khi mở rộng quy mô.

### 2.1. Công việc độc lập của 5 thành viên

- **TV1 (Data & ETL):**
  - Rà soát điều khoản sử dụng và quyền chia sẻ lại của nguồn dữ liệu cấu trúc chính.
  - Chốt ngày lấy danh mục VN30; lập bảng phân loại mã giữ lại và mã loại (chứng khoán, bảo hiểm...) kèm lý do.
  - Dựng pipeline ETL thử nghiệm cho **5 mã pilot** (3 phi tài chính khác ngành + 2 ngân hàng) trong ≥5 năm gần nhất.
  - Thu thập đầy đủ file báo cáo tài chính gốc (PDF) của 5 mã pilot để phục vụ đối chiếu chéo.
  - *Đầu ra:* Bảng danh mục VN30 chốt ngày; Snapshot pilot 5 mã + kho BCTC gốc pilot.

- **TV2 (Semantic Layer & B0/C):**
  - Viết tài liệu đặc tả chốt quy ước cho **quy tắc số liệu khó (mục 4.3)** và **xử lý thời gian (mục 4.4)** (ngưỡng mẫu số gần 0, vốn chủ âm, thiếu đầu kỳ, 0 dòng, "kỳ gần nhất" đơn mã vs đa mã).
  - Cài đặt bộ hàm pilot cho **3 đại lượng**: (1) Doanh thu quý & tăng trưởng YoY (nhóm phi tài chính), (2) ROE TTM (cả 2 nhóm), (3) Ca xử lý "doanh thu thuần của ngân hàng" (trả cảnh báo/yêu cầu làm rõ, không tự thay bằng thu nhập lãi thuần).
  - Viết unit test kiểm chứng các hàm pilot trên dữ liệu giả lập (kể cả ca biên).
  - Đề xuất danh mục **10–15 chỉ số chính thức** phân tách 3 lớp (trường gốc, chỉ số suy ra, phép biến đổi) cho giai đoạn 2.
  - *Đầu ra:* Tài liệu đặc tả quy tắc 4.3–4.4; Thư viện hàm pilot + unit test; Danh mục 10–15 chỉ số đề xuất.

- **TV3 (LLM Pipeline & Sandbox):**
  - Chốt cấu hình LLM thử nghiệm (mô hình, phiên bản API, `temperature`, `seed`, format log token/độ trễ/số lượt gọi).
  - Thiết lập khung **sandbox thực thi cô lập** mức cơ bản (tách tiến trình, khóa mạng, giới hạn quyền đọc/ghi và RAM/CPU).
  - Xây dựng giao diện đầu vào/đầu ra chuẩn (JSON response contract) cho các pipeline LLM để tương thích với Bộ chấm của TV5.
  - Chạy thử luồng sinh câu trả lời nháp trên tập ví dụ tự tạo để đo độ ổn định định dạng.
  - *Đầu ra:* Pipeline runner chuẩn hóa logging; Sandbox v0.1; Đặc tả Output Contract cho hệ thống.

- **TV4 (Benchmark & Test Keeper):**
  - Đọc và đối chiếu **ViNumQA, ViFinQA, VCBS AI**: lấy ~30 câu, gắn nhãn theo kiểu đầu vào, số kỳ, số doanh nghiệp, loại phép toán để xác định khoảng trống nghiên cứu.
  - Xây dựng **30 câu Pilot** bám sát 3 đại lượng pilot, trong đó bắt buộc có: ca *"doanh thu thuần của ngân hàng"*, câu mơ hồ, và các **cặp câu đối lập** có dữ liệu thật làm 2 cách hiểu cho kết quả khác nhau.
  - Tự tra cứu BCTC gốc (của 5 mã pilot) và tính tay **đáp án Gold cho 30 câu Pilot** (ghi rõ nguồn ô số và công thức tính, tuyệt đối không chạy code của TV2).
  - Thiết kế khung phân loại **họ câu (question families)** cho tập Benchmark 100+ câu ở Giai đoạn 2.
  - *Đầu ra:* Báo cáo đối chiếu 3 công trình (~30 câu gắn nhãn); Bộ 30 câu Pilot + Gold độc lập; Khung thiết kế họ câu v1.

- **TV5 (Evaluation & QA):**
  - Xây dựng **Bộ chấm tự động v1** theo đúng mục 7.1:
    - Công bố đồng thời **4 đại lượng**: Tỷ lệ trả lời ($A/N$), Tỷ lệ sai trong câu đã trả lời ($W/A$), Tỷ lệ đúng toàn tập ($(A-W)/N$), Tỷ lệ lỗi âm thầm (sai + thiếu cảnh báo cụ thể).
    - Cài đặt bộ lọc cảnh báo: loại bỏ cảnh báo chung chung, chỉ công nhận cảnh báo nêu đúng mã/kỳ/đầu vào bị ảnh hưởng.
    - Hỗ trợ chấm bảng nhiều mã (cả cấp độ dòng và cấp độ toàn câu) và chấm hành động (mơ hồ / thiếu dữ liệu / từ chối / rỗng hợp lệ).
  - Thiết kế bộ dữ liệu kiểm thử cho buổi **"tấn công bộ chấm"** (mục 10).
  - Soạn quy trình & biểu mẫu lấy mẫu phân tầng 100 giá trị cho Giai đoạn 2.
  - *Đầu ra:* Mã nguồn Bộ chấm v1; Bộ ca tấn công bộ chấm; Quy trình kiểm toán phân tầng 100 giá trị.

### 2.2. Tổng kết cuối Giai đoạn 1 & Điều kiện chuyển Giai đoạn 2

**Nội dung buổi tổng kết:**
1. **Kiểm tra 3 điều kiện Pilot (Mục 10):**
   - *Điều kiện 1 (Truy vết Gold):* TV5 lấy ngẫu nhiên các đáp án Gold trong 30 câu Pilot của TV4, tự lần ngược về ô số trên BCTC gốc để tính lại — phải khớp 100%.
   - *Điều kiện 2 (Phân biệt hành vi):* Bộ chấm của TV5 chạy thử để chứng minh phân biệt được rạch ròi: *trả sai*, *hỏi thừa*, *báo thiếu đúng*, và *lọc ra 0 dòng*.
   - *Điều kiện 3 (Cặp đối lập thực chất):* Xác nhận mỗi cặp đối lập trong 30 câu Pilot đều cho 2 kết quả khác nhau trên dữ liệu 5 mã.
2. **Thực hiện buổi "Tấn công bộ chấm":**
   - TV5 (vai trò người kiểm tra) chủ động đưa các đầu ra giả lập lỗi vào Bộ chấm: (a) đảo kỳ báo cáo, (b) hoán đổi giá trị giữa 2 mã, (c) gắn cảnh báo chung vào đáp án sai, (d) luôn hỏi lại mọi câu.
   - **Quy tắc cứng:** Nếu Bộ chấm cho điểm đẹp hoặc cho qua bất kỳ ca nào ở trên, dừng mở rộng câu hỏi để sửa Bộ chấm ngay lập tức.
3. **Ra quyết định phạm vi Ngân hàng:**
   - Đánh giá xem nhóm 2 ngân hàng pilot có cần quá nhiều quy tắc riêng làm chậm tiến độ hay không; quyết định giữ lại trong mẫu chính hay chuyển sang tập mở rộng.
4. **Gói bàn giao sang Giai đoạn 2:**
   - Danh mục VN30 chốt ngày & danh mục 10–15 chỉ số chính thức; Đặc tả quy tắc 4.3–4.4 đã đóng băng; Bộ chấm v1 đã qua tấn công.

---

## 3. Giai đoạn 2: Dữ liệu chuẩn hóa, Semantic Layer, Benchmark & Khóa Test (Tuần 4–6)

**Mục tiêu giai đoạn:** Hoàn thành kho dữ liệu VN30 ≥5 năm, kiểm toán 100 giá trị phân tầng, cài đặt đủ 10–15 chỉ số + B0, hoàn thiện và **khóa sớm tập câu hỏi Test chính**.

### 3.1. Công việc độc lập của 5 thành viên

- **TV1 (Data & ETL):**
  - Mở rộng ETL cho toàn bộ nhóm VN30 đủ điều kiện (≥5 năm) theo đúng schema `fact_financials` (long format, đủ các trường `item_type` flow/stock, `as_of_date`, `report_version`, `is_restated`, `source_ref`, `derived_from`...).
  - Cài đặt quy tắc chuyển đổi YTD → quý đơn lẻ (chỉ áp dụng cho `flow`, kiểm tra đồng bộ niên độ, đơn vị, phạm vi hợp nhất và tương thích phiên bản).
  - Xuất thêm bảng **wide format** phục vụ phương pháp A/B và bảng dữ liệu thô CSV phục vụ B1 (nếu chạy).
  - Đóng gói **Snapshot dữ liệu v1.0** kèm toàn bộ metadata và mã hóa hash kiểm tra toàn vẹn.
  - *Đầu ra:* Kho `fact_financials` & bảng wide (Snapshot v1.0); Tài liệu dữ liệu tách riêng 3 lớp.

- **TV2 (Semantic Layer & B0):**
  - Cài đặt đầy đủ **10–15 chỉ số** (nhóm phi tài chính và phần ngân hàng từ thân báo cáo nếu được giữ ở GĐ1) thành thư viện Python chuẩn hóa (`get_metric(...)` và các phép biến đổi YoY, QoQ, TTM, xếp hạng).
  - Tích hợp toàn bộ quy tắc số liệu khó (4.3) và thời gian (4.4) vào thư viện; viết unit test phủ toàn bộ ca chuẩn và ca biên.
  - Xây dựng hoàn chỉnh **Phương pháp B0 (Không LLM)**: bộ phân tích quy tắc/template nhận **nguyên câu tiếng Việt** (tách thực thể, kỳ, chỉ số, phép toán) và gọi thẳng thư viện hàm.
  - *Đầu ra:* Thư viện Semantic Layer v1.0 + báo cáo coverage unit test; Hệ thống B0 hoàn chỉnh.

- **TV3 (LLM Pipeline A, B & Sandbox):**
  - Hoàn thiện **Sandbox thực thi v1.0** có kiểm soát chặt chẽ cho Pandas (ngăn đọc file hệ thống, chặn import nguy hiểm, timeout thực thi).
  - Cài đặt **Phương pháp A**: LLM sinh code Pandas trực tiếp trên bảng wide chuẩn hóa, đầu vào prompt chỉ gồm mô tả schema và công thức bằng văn bản.
  - Cài đặt **Phương pháp B**: LLM sinh code Pandas kết hợp gọi thư viện hàm `get_metric(...)` của TV2 (áp dụng cùng mô hình, seed, tập few-shot trên các câu mẫu giả lập của khung thiết kế).
  - Xây dựng bộ test khả năng chống chịu bảo mật sơ bộ cho Sandbox.
  - *Đầu ra:* Hệ thống A & Hệ thống B sẵn sàng chạy batch; Sandbox v1.0.

- **TV4 (Benchmark & Test Keeper):**
  - Soạn thảo bộ Benchmark chính **≥100 câu**, chia tách độc lập thành **tập Dev** và **tập Test chính** theo **họ câu** (bảo đảm không rò rỉ biến thể diễn đạt giữa Dev và Test).
  - Đưa vào đầy đủ các cặp đối lập bắt buộc (mục 8.3: Q3 vs lũy kế 9M, % YoY vs điểm %, top tuyệt đối vs tốc độ tăng, rỗng hợp lệ vs thiếu mẫu số, ROE vốn chủ âm vs dương) và một số bảng số tự tạo (đánh dấu rõ) để cô lập logic tính toán.
  - Đưa vào nhóm câu hỏi mơ hồ (được gắn nhãn loại mơ hồ để đánh giá khả năng phát hiện mơ hồ & chính sách hiển thị/hỏi lại).
  - **Khóa danh sách câu hỏi tập Test chính** (chỉ TV4 nắm giữ tập Test; bàn giao tập Dev cho TV2/TV3 phát triển).
  - Tự tính **Gold sơ bộ** từ báo cáo gốc cho toàn bộ tập Dev và tập Test.
  - *Đầu ra:* Tập Dev (bàn giao chung); Tập Test chính đã khóa danh sách câu (lưu mật); Bảng Gold độc lập.

- **TV5 (Evaluation & QA):**
  - Thực hiện **kiểm tra 100 giá trị lấy mẫu phân tầng** từ dữ liệu đầu ra của TV1 đối chiếu trực tiếp với báo cáo tài chính gốc theo 4 trục: ngành (phi tài chính/ngân hàng), loại báo cáo (BS/IS/CF), kỳ (quý/YTD), loại giá trị (gốc/dẫn xuất). Lập báo cáo lỗi **chi tiết theo từng tầng**.
  - Gán nhãn độc lập **hành động kỳ vọng** (trả số / báo thiếu / cảnh báo / hỏi làm rõ / 0 dòng) và kiểm tra chéo một mẫu ngẫu nhiên câu hỏi của TV4 để tính **hệ số đồng thuận Cohen's kappa**.
  - Thực hiện kiểm thử xâm nhập/bảo mật cho Sandbox của TV3 (ghi nhận số ca test, số ca bị chặn, các giới hạn quan sát được).
  - Cập nhật Bộ chấm v1.1 để hỗ trợ chấm hàng loạt cho ≥100 câu, tự động xuất phân tích theo từng họ câu.
  - *Đầu ra:* Báo cáo kiểm toán 100 giá trị theo từng tầng; Chỉ số Cohen's kappa; Báo cáo test Sandbox; Bộ chấm v1.1.

### 3.2. Tổng kết cuối Giai đoạn 2 & Điều kiện chuyển Giai đoạn 3

**Nội dung buổi tổng kết:**
1. **Nghiệm thu Snapshot dữ liệu:** Rà soát báo cáo 100 mẫu phân tầng của TV5. Nếu phát hiện lỗi hệ thống ở tầng nào (ví dụ YTD→Q hoặc đơn vị), TV1 sửa lỗi ngay trong phiên, sau đó **Khóa cứng Snapshot v1.0** (không sửa đổi dữ liệu trong lúc chạy thí nghiệm GĐ3).
2. **Hoàn thiện & niêm phong Gold Test:** TV4 đối chiếu lại Gold tập Test dựa trên Snapshot v1.0 đã khóa (kiểm tra kỳ khả dụng, trường hợp thiếu dữ liệu tại ngày hỏi `question_date`). Xử lý các ca bất đồng nhãn (nếu Cohen's kappa chưa đạt ngưỡng thống nhất). **Niêm phong hoàn toàn tập Test + Gold Test** (TV2, TV3 không được tiếp cận).
3. **Nghiệm thu công cụ:** Xác nhận unit test của TV2 đạt 100%, Sandbox của TV3 vượt qua bài kiểm tra của TV5.
4. **Gói bàn giao sang Giai đoạn 3:** Snapshot v1.0; Thư viện chỉ số v1.0; Tập Dev công khai cho TV2/TV3 tối ưu; Tập Test niêm phong (chỉ TV4/TV5 giữ).

---

## 4. Giai đoạn 3: Hoàn thiện C, Thí nghiệm chính & Chẩn đoán lỗi (Tuần 7–10)

**Mục tiêu giai đoạn:** Hoàn thành phương pháp C (và B1/D nếu đủ thời gian), tối ưu các hệ thống trên tập Dev, chạy đánh giá nhiều lần trên tập Test niêm phong, thực hiện thí nghiệm chẩn đoán và phân tích thống kê Bootstrap.

### 4.1. Công việc độc lập của 5 thành viên

- **TV1 (Data Support & Auxiliary Formats):**
  - Chuẩn bị định dạng dữ liệu **CSV thô** (giữ nguyên cấu trúc chưa chuẩn hóa) phục vụ thí nghiệm phụ **B1** (nếu được kích hoạt).
  - Nạp Snapshot v1.0 vào **DuckDB** với schema SQL tương ứng phục vụ thí nghiệm phụ **D (Text-to-SQL)** (nếu được kích hoạt).
  - Hỗ trợ kiểm tra các ca nghi vấn về số liệu báo cáo gốc phát sinh trong quá trình chạy tập Dev/Chẩn đoán (chỉ đọc, không sửa Snapshot v1.0).
  - *Đầu ra:* Kho CSV thô cho B1; Database DuckDB cho D; Nhật ký giải trình các ca dữ liệu biên.

- **TV2 (Method C & Diagnostic Gold Queries):**
  - Xây dựng hoàn chỉnh **Phương pháp C**: LLM sinh truy vấn có cấu trúc (JSON theo schema định sẵn) và bộ thực thi giới hạn phép toán **dùng chung thư viện hàm với B**. Ghi nhận rõ các câu trên tập Dev mà ngôn ngữ truy vấn của C không biểu đạt được.
  - Tinh chỉnh bộ quy tắc **B0** trên tập Dev.
  - Chuẩn bị bộ công cụ chuyển đổi **truy vấn chuẩn của người gán nhãn** (dùng cho thí nghiệm chẩn đoán mục 6.5 — nhận đầu vào JSON chuẩn để chạy lại bộ thực thi, tách lỗi hiểu câu khỏi lỗi thực thi).
  - *Đầu ra:* Hệ thống C hoàn chỉnh; B0 bản đóng băng; Bộ chạy truy vấn chẩn đoán.

- **TV3 (Optimization on Dev & Auxiliary A/B/B1/D):**
  - Tinh chỉnh prompt/few-shot cho **A và B** trên tập Dev (giữ đồng nhất mô hình, phiên bản, cấu hình kiểm soát cho cả A, B, C).
  - Nếu tiến độ đúng hạn, cài đặt **thí nghiệm phụ B1** (LLM + CSV thô, ghi nhận số câu vượt context window, tuyệt đối không lọc dòng theo đáp án) và **thí nghiệm phụ D** (LLM sinh SQL trên DuckDB).
  - Đóng gói 4 hệ thống chính (**B0, A, B, C**) + phụ (nếu có) thành các container/script chạy độc lập, hỗ trợ 2 chế độ: (1) lượt đầu không tự sửa, (2) tự sửa với ngân sách lượt gọi cố định; tự động xuất log token, thời gian, chi phí.
  - *Đầu ra:* Bản đóng băng (frozen builds) của B0, A, B, C (và B1/D); Kết quả chạy và log trên tập Dev.

- **TV4 (Blind Test Execution & Diagnostic Set):**
  - Vận hành chạy các bản đóng băng (từ TV2, TV3) trên **tập Test chính đang niêm phong** với nhiều lần chạy độc lập (ví dụ 3 lần chạy cho các phương pháp LLM) mà không tiết lộ câu hỏi cho người phát triển.
  - Thu gom toàn bộ câu trả lời thô, log token/latency và gửi cho TV5 chấm.
  - Quản lý **tập chẩn đoán riêng**: mọi câu hỏi được viết mới sau khi nhóm quan sát lỗi trên tập Dev đều được đưa vào tập chẩn đoán này (tuyệt đối không trộn vào tập Test chính).
  - Phối hợp mã hóa "truy vấn chuẩn của người gán nhãn" cho các câu bị sai ở lượt chạy chính để phục vụ **thí nghiệm chẩn đoán (mục 6.5)**.
  - *Đầu ra:* Kết quả thô đa lần chạy trên tập Test chính; Tập chẩn đoán riêng; Bộ truy vấn chuẩn cho các ca lỗi.

- **TV5 (Scoring, Bootstrap & Error Metrics):**
  - Chạy Bộ chấm v1.1 trên toàn bộ kết quả Test chính của B0, A, B, C (và B1/D).
  - Tính bảng tổng hợp **4 đại lượng bắt buộc** theo từng phương pháp và từng họ câu; tính độ đúng trên **cặp đối lập** (chỉ đúng khi cả 2 câu trong cặp đúng) và độ trung thực diễn giải (**faithfulness**, kiểm tra bằng test đảo giá trị 2 thực thể).
  - Thực hiện thống kê chuẩn mực (mục 7.2):
    - Tính độ dao động giữa các lần chạy (variance).
    - Chạy **Bootstrap theo họ câu** (dùng chung mẫu lấy lại cho mọi phương pháp; **tuyệt đối không gộp 3 lần chạy thành 300 câu để chạy McNemar**).
    - Nếu số họ câu ít, xuất bảng kết quả chi tiết từng họ và liệt kê ca bất đồng.
  - Chấm kết quả **thí nghiệm chẩn đoán (mục 6.5)** để phân tách tỷ lệ lỗi do *hiểu câu hỏi* vs lỗi do *dữ liệu/công thức/bộ thực thi*.
  - *Đầu ra:* Bảng kết quả chính thức B0/A/B/C; Kết quả Bootstrap & phương sai; Ma trận phân loại lỗi chẩn đoán.

### 4.2. Tổng kết cuối Giai đoạn 3 & Điều kiện chuyển Giai đoạn 4

**Nội dung buổi tổng kết:**
1. **Kiểm tra quy tắc cắt giảm (nếu trễ hạn, Mục 9):**
   - Áp dụng đúng thứ tự ưu tiên nếu thiếu thời gian cho GĐ4: bỏ D → bỏ B1 → đưa ngân hàng sang tập mở rộng → giảm số chỉ số (không cắt Benchmark, Bộ chấm, và Phân tích lỗi).
2. **Giải mã & Công bố bảng kết quả chính thức:**
   - Lần đầu tiên mở niêm phong để cả nhóm xem bảng kết quả 4 đại lượng (N, A, W, Silent-wrong), kết quả theo cặp đối lập, và kết quả thí nghiệm chẩn đoán.
   - Đọc kết quả theo đúng giới hạn phép so sánh (mục 6.2): A vs B (tác dụng semantic layer), B vs C (tác dụng tổng hợp JSON + bộ thực thi giới hạn, có tính cả câu C không biểu đạt được), B0 vs LLM (họ câu nào quy tắc đã đủ).
3. **Gói bàn giao sang Giai đoạn 4:**
   - Bộ bảng số liệu thống kê đã khóa; Toàn bộ log ca lỗi đã phân tách nguyên nhân (hiểu câu vs thực thi/dữ liệu).

---

## 5. Giai đoạn 4: Phân tích lỗi sâu, Demo truy vết & Đóng gói công bố (Tuần 11–14)

**Mục tiêu giai đoạn:** Giải thích thấu đáo nguyên nhân từng nhóm lỗi (nhất là lỗi ngữ nghĩa và hành vi khi mơ hồ), hoàn thiện Demo truy vết về ô số gốc, bảo đảm khả năng tái tạo độc lập toàn bộ kết quả và hoàn thành báo cáo.

### 5.1. Công việc độc lập của 5 thành viên

- **TV1 (Data Release & Documentation):**
  - Đóng gói mã nguồn ETL, script tạo Snapshot v1.0, bảng thống kê VN30 giữ/loại, và báo cáo kiểm toán 100 mẫu phân tầng.
  - Chuẩn bị gói dữ liệu công bố tuân thủ bản quyền: nếu nguồn không cho phép chia sẻ dữ liệu thô, xuất bộ mã chuẩn hóa, mô tả cấu trúc snapshot và các ví dụ mẫu được phép chia sẻ (mục 3.4).
  - *Đầu ra:* Gói mã ETL & tài liệu dữ liệu sạch; Hướng dẫn tái tạo Snapshot.

- **TV2 (Semantic Package & Technical Docs):**
  - Đóng gói thư viện hàm chỉ số (Semantic Layer), bộ unit test và tài liệu đặc tả quy tắc số liệu khó (mục 4.3, 4.4) thành module hoàn chỉnh.
  - Viết phần báo cáo kỹ thuật cho **B0** và **C**, phân tích chi tiết các cấu trúc câu hỏi mà C không biểu đạt được (mục 6.2).
  - Cung cấp API/module giải thích công thức và trả về tọa độ `source_ref` để ghép vào Demo của TV3.
  - *Đầu ra:* Gói thư viện Semantic Layer + Docs; Báo cáo kỹ thuật B0 & C.

- **TV3 (Traceable Demo & Reproducibility Pipeline):**
  - Xây dựng **Demo giao diện (Mục tiêu M5)** cho phép người dùng nhập câu hỏi tiếng Việt và hiển thị đầy đủ:
    1. Câu hiểu lại của hệ thống (diễn giải kỳ, mã, chỉ số, phạm vi),
    2. Kết quả số (kèm kỳ ngay cạnh con số),
    3. Công thức áp dụng,
    4. Cảnh báo cụ thể (nếu có) và *Disclaimer* miễn trừ đầu tư,
    5. **Truy vết về tận ô số gốc / mã báo cáo nguồn (`source_report_id`, `source_ref`)**.
  - Viết script chạy tự động toàn trình (one-command reproduction) cho A, B, C (và B1/D nếu có).
  - *Đầu ra:* Ứng dụng Demo hoàn chỉnh; Repository mã nguồn & script tái lập kết quả.

- **TV4 (Error Analysis & Benchmark Paper):**
  - Thực hiện **Phân tích lỗi định tính chuyên sâu** trên các ca lỗi của B0, A, B, C và tập chẩn đoán:
    - Phân loại lỗi ngữ nghĩa trên cặp đối lập (nhầm quý/YTD, YoY/QoQ, % vs điểm phần trăm, quên kiểm tra vốn chủ âm).
    - Phân tích **hành vi với câu mơ hồ (RQ3 điều chỉnh)**: tỷ lệ phát hiện mơ hồ, tỷ lệ hỏi thừa trên câu rõ, so sánh mô tả chính sách mặc định công khai vs hỏi lại 1 lượt (nêu rõ giới hạn không có ý định xác nhận từ khảo sát).
  - Hoàn thiện chương Benchmark & đối chiếu công trình liên quan (ViNumQA, ViFinQA, VCBS AI).
  - *Đầu ra:* Báo cáo Phân tích lỗi & Benchmark (kèm ví dụ minh họa từng nhóm lỗi).

- **TV5 (Final Audit & Independent Reproduction):**
  - Đóng vai trò người kiểm thử độc lập, chạy lại toàn bộ script tái lập kết quả của TV3 trên môi trường sạch để bảo đảm **tái tạo chính xác bảng số liệu chính**.
  - Kiểm thử chéo Demo của TV3: chọn ngẫu nhiên các truy vấn từ giao diện Demo để kiểm chứng khả năng truy ngược đúng tới ô số trên báo cáo tài chính gốc.
  - Tổng hợp các bảng biểu cuối cùng (4 đại lượng, Bootstrap CI, kết quả theo từng họ câu, chi phí/độ trễ, kiểm toán bảo mật Sandbox) và rà soát toàn bộ giới hạn nghiên cứu / rủi ro (mục 12).
  - *Đầu ra:* Biên bản xác nhận tái lập kết quả (Reproducibility Report); Báo cáo kiểm thử Demo; Chương Đánh giá & Thống kê hoàn chỉnh.

### 5.2. Tổng kết cuối Giai đoạn 4 (Nghiệm thu toàn dự án)

**Danh mục kiểm tra nghiệm thu theo 5 Mục tiêu (M1–M5):**
- [ ] **M1:** Có kho dữ liệu VN30 đủ điều kiện ≥5 năm và báo cáo kiểm tra ≥100 giá trị phân tầng theo từng tầng.
- [ ] **M2:** Có 10–15 chỉ số chuẩn hóa kèm unit test cho công thức, kỳ và điều kiện "không xác định".
- [ ] **M3:** Có Benchmark ≥100 câu (gồm cặp đối lập, tập Test khóa từ GĐ2, Gold độc lập, có chỉ số Cohen's kappa và ghi rõ giới hạn không khảo sát).
- [ ] **M4:** Có bảng so sánh có kiểm soát B0, A, B, C với đủ 4 đại lượng (N, A, W, Silent-wrong), Bootstrap theo họ câu và phân tích lỗi chẩn đoán.
- [ ] **M5:** Demo chạy ổn định, hiển thị câu hiểu lại, kỳ, công thức, cảnh báo và truy vết chính xác về ô số gốc; người thứ hai (TV5) tái tạo lại được bảng kết quả chính.

---

## 6. Tóm tắt ma trận điều phối theo giai đoạn

| Giai đoạn | TV1 (Data) | TV2 (Semantic & B0/C) | TV3 (LLM, Sandbox & Demo) | TV4 (Benchmark & Test Keeper) | TV5 (Eval, QA & Stats) | Cổng tổng kết (Phase Gate) |
|---|---|---|---|---|---|---|
| **GĐ 1 (T1–3)** | VN30 list + ETL 5 mã pilot + PDF gốc | Quy tắc 4.3–4.4 + 3 hàm pilot + DS 10–15 chỉ số | Cấu hình LLM + Sandbox v0.1 + Output Contract | Đối chiếu 3 tài liệu + 30 câu Pilot + Gold độc lập | Bộ chấm 4 đại lượng + Kịch bản tấn công | Đạt 3 ĐK Pilot + Pass **"Tấn công bộ chấm"** |
| **GĐ 2 (T4–6)** | ETL full VN30 + YTD→Q + Snapshot v1.0 | 10–15 chỉ số + unit test + B0 hoàn chỉnh | Sandbox v1.0 + Hệ thống A & B | Benchmark ≥100 câu + **Khóa Test** + Gold | Kiểm tra **100 mẫu phân tầng** + Kappa + Test Sandbox | Khóa cứng Snapshot v1.0 + **Niêm phong Test** |
| **GĐ 3 (T7–10)** | CSV thô (B1) + DuckDB (D) + Hỗ trợ đối chiếu | Hệ thống C + Tinh chỉnh B0 + Tool truy vấn chẩn đoán | Tối ưu A/B trên Dev + (B1/D) + Đóng gói chạy | Chạy mù Test chính nhiều lần + Tập chẩn đoán riêng | Chấm Test + **Bootstrap theo họ câu** + Chẩn đoán lỗi | Công bố bảng kết quả + Áp dụng cắt giảm (nếu trễ) |
| **GĐ 4 (T11–14)** | Đóng gói ETL + Xử lý quyền chia sẻ | Đóng gói Semantic + Docs B0/C + API nguồn | **Demo truy vết (M5)** + Script tái lập | **Phân tích lỗi ngữ nghĩa & mơ hồ** + Báo cáo Benchmark | **Tái chạy độc lập** bảng kết quả + Test Demo | Nghiệm thu đủ **M1–M5** |

