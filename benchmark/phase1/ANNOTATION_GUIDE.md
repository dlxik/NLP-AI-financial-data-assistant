# Quy ước gán nhãn và tính Gold v0.1

## Ranh giới độc lập

Hiền tra ô báo cáo và tính lại bằng máy tính/giấy; ghi kết quả vào phiếu review. Không gọi `get_metric`, không dùng đầu ra A/B/C làm Gold. `build.mjs` chỉ là bảng tính phụ của TV4 từ ô chép thủ công bởi trợ lý, **không được ghi nhận như Hiền đã tự tính tay**. TV5 kiểm tra độc lập; trợ lý này không đóng vai người kiểm tra thứ hai.

## Định nghĩa dùng cho pilot

- Doanh thu = doanh thu thuần mã 10, không dùng doanh thu bán hàng mã 01 hoặc doanh thu tài chính.
- Quý IV dùng trực tiếp cột ba tháng cuối năm; FY dùng cột lũy kế 12 tháng. Không lấy FY làm quý IV.
- YoY (%) = `(kỳ hiện tại / cùng kỳ năm trước - 1) × 100`; kiểm tra mẫu số dương và khác 0. Pilot số thật hiện không có mẫu số 0/âm.
- ROE TTM (%) ở 31/12/2024 = `tổng LNST năm 2024 / ((tổng VCSH đầu năm + tổng VCSH cuối năm)/2) × 100`. Tử/mẫu cùng gồm lợi ích không kiểm soát. FPT dùng mã 400 gồm nguồn kinh phí/quỹ khác; đây là định nghĩa **được ghi rõ trong câu**, không mặc nhiên coi là chỉ số ROE công ty công bố.
- TTM trùng năm tài chính tại 31/12. Bộ này chưa chứng minh xử lý cửa sổ TTM giữa năm hay ghép bốn quý qua niên độ.
- Giữ VND nguyên cho 3 doanh nghiệp; ngân hàng dùng triệu VND cả tử và mẫu, triệt tiêu trong ROE. Không nhân thêm một triệu cho tỷ số.
- Tiền xuất VND, sai số tuyệt đối 1 VND; phần trăm lưu 8 chữ số thập phân, hiển thị 4, dung sai 0,0001 **điểm phần trăm**. Không so phần trăm với tỷ lệ 0–1.

Các quy tắc mẫu số gần 0, vốn âm, kỳ mới nhất và thiếu đầu kỳ toàn hệ thống thuộc TV2 chốt; bản này không tuyên bố thay thế đặc tả 4.3–4.4. Đề cương v3 chưa có trong repository.

## Hành động kỳ vọng

| Giá trị | Khi nào | Kết quả |
|---|---|---|
| `answer` | Đủ số, câu rõ | Dòng có mã, kỳ, chỉ tiêu, giá trị và đơn vị |
| `clarify` | Thiếu kỳ/cách đo hoặc doanh thu ngân hàng chưa ánh xạ | Không trả một con số mặc định; nêu đúng nội dung cần hỏi |
| `missing_data` | Đầu vào thực cấp thiếu ô thiết yếu | Nêu mã, mốc thiếu và trường thiếu, không gán 0 |
| `empty` | Đủ dữ liệu và không dòng nào thỏa lọc | Bảng `[]`, giải thích điều kiện; không báo thiếu |

Pilot chọn chính sách hỏi lại. So sánh với chính sách mặc định công khai phải tạo nhãn riêng cho chính sách, không chấm nó sai chỉ vì không hỏi lại. Không có câu từ chối ngoài miền trong 30 câu này; mở rộng ở giai đoạn 2. Cảnh báo chung kiểu “chỉ tham khảo” không thay cảnh báo đúng mã/kỳ/đầu vào.

## Truy vết

`source_cell_ids` nối tới `source_cells.json`; mỗi ô nối `report_id` tới manifest. `pdf_page` bắt đầu từ 1, khác số trang in `printed_page`. `operands` giữ số gốc dạng chuỗi, theo thứ tự a, b, c trong công thức. Trước tính phải kiểm tra hash, scope, basis, đơn vị, bản báo cáo và nhãn cột.

Ngày hỏi 22/11/2026 được ghi để tránh tuyên bố biết trước báo cáo; câu đều chỉ rõ snapshot 2024. Ngày công bố lịch sử còn null, nên **không dùng bộ này để đánh giá point-in-time/hindsight**. TV1 phải bổ sung `as_of_date`, `report_version` và bằng chứng ngày công bố trước khi sinh câu “kỳ gần nhất”.

## Ca che dữ liệu P28

Chỉ cấp allowlist của fixture `withhold_vnm_opening_equity`. Không gửi Gold, PDF, Internet hoặc file đầy đủ vào pipeline trong ca này. Đây là dữ liệu thật bị che có chủ đích, không phải báo cáo doanh nghiệp thực sự thiếu. P15/P28 là đối lập về **đầu vào**, không phải hai cách hiểu ngôn ngữ. CP01–CP05 mới là các đối lập kỳ/phép toán/xếp hạng.

## Bàn giao cho bộ chấm

Đây là schema nội bộ TV4, chưa phải Output Contract đã chốt với TV3/TV5. Adapter phải giữ khóa `(ticker, period, metric, unit)` và phân biệt bốn hành động. Bảng P24/P29 chấm từng dòng và toàn câu. Điểm toàn câu chỉ đúng nếu đủ dòng đúng, không thừa mã; xếp hạng phải so đủ ứng viên. Không dùng script kiểm tra hồ sơ này làm Bộ chấm 4 đại lượng.
