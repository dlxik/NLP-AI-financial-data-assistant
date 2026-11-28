# Tổng kết tiến độ Giai đoạn 1 — TV5

- **Vai trò:** Evaluation, QA & Statistical Auditor
- **Nhánh:** `linh`
- **Phạm vi:** Bộ chấm v1, ca tấn công và quy trình kiểm toán phân tầng

## Đã hoàn thành

1. **Gold schema độc lập**
   - Hỗ trợ câu đơn, bảng nhiều mã và hành động.
   - Khai báo dung sai số, cảnh báo bắt buộc, lựa chọn làm rõ và khóa ghép dòng.
   - Không import code tính chỉ số của TV2 hoặc pipeline của TV3.

2. **Bộ chấm v1**
   - Tính `N`, `A`, `W`, `A/N`, `W/A`, `(A-W)/N` và silent-wrong.
   - Bổ sung `behavior_accuracy`, tỷ lệ đúng cấp dòng và số lần hỏi lại không cần thiết.
   - Câu thiếu prediction vẫn nằm trong mẫu số `N`.
   - Phát hiện prediction trùng ID, dòng thiếu/thừa/trùng và hoán đổi giá trị giữa các mã.

3. **Bộ lọc cảnh báo**
   - Chỉ công nhận cảnh báo có code, message và vị trí mã/kỳ/đầu vào.
   - Không công nhận cảnh báo định vị sai đối tượng Gold.
   - Hỗ trợ ba cảnh báo tổng hợp cấp bảng theo Output Contract v0.1.

4. **Tấn công bộ chấm**
   - Đảo kỳ nhưng giữ nguyên giá trị.
   - Hoán đổi giá trị giữa hai mã.
   - Dùng cảnh báo chung chung che lỗi.
   - Luôn hỏi lại mọi câu.

5. **Chuẩn bị kiểm toán dữ liệu Giai đoạn 2**
   - Quy trình lấy mẫu phân tầng 100 giá trị.
   - Phân loại lỗi và biểu mẫu CSV ghi bằng chứng.

6. **Kiểm thử**
   - `17/17` test pass.
   - `compileall` và `git diff --check` pass.

## Phần chờ đầu vào tại Phase Gate

- Cần TV4 bàn giao 30 câu Pilot và Gold tính độc lập để chạy chấm thật.
- Cần TV3 chốt ba điểm của Output Contract: khóa ghép bảng, đơn vị tỷ lệ và cách ghi lỗi
  parse/sandbox. Bản v1 hiện chọn khóa `(ticker, period)`, tỷ lệ dạng ratio và xem đầu ra
  parse hỏng là prediction không hợp lệ.
- Cần đầu ra pilot của B0/LLM để thực hiện phiên tấn công trực tiếp, ngoài fixture tự động.
- Quy trình 100 mẫu chỉ được thực thi khi TV1 bàn giao Snapshot; Giai đoạn 1 mới hoàn tất
  giao thức và biểu mẫu.
