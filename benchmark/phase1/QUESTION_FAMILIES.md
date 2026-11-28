# Khung họ câu v1 — mục tiêu 120 câu ở giai đoạn 2

Đây là thiết kế, chưa tạo Test chính. Số lượng là hạn mức đề xuất, chốt sau khi đóng băng chỉ số và dữ liệu.

| Họ | Số câu | Kỹ năng cần kiểm tra | Ràng buộc bắt buộc |
|---|---:|---|---|
| F01 Tra cứu quý | 10 | Mã, kỳ, đơn vị, chỉ tiêu | Ba ngành phi tài chính |
| F02 Quý và YTD | 12 | Quý đơn lẻ vs lũy kế | Cặp Q3/9M có hai số khác nhau |
| F03 Tăng trưởng thời gian | 12 | YoY vs QoQ, gốc so sánh | Đủ các ô số, phiên bản tương thích |
| F04 Phần trăm và điểm phần trăm | 8 | Mức tăng tương đối vs chênh tỷ lệ | Cặp kết quả khác nhau thực chất |
| F05 ROE TTM | 12 | Cửa sổ 4 quý, bình quân vốn | Cả ngân hàng và phi tài chính; đầu/cuối kỳ |
| F06 ROE biên | 8 | Vốn âm, gần 0, thiếu đầu kỳ | Số thật nếu có; dữ liệu giả phải gắn nhãn |
| F07 Ngữ nghĩa ngân hàng | 8 | Không tự đổi doanh thu thành lãi thuần | Phân biệt câu rõ và cần hỏi |
| F08 Bảng và xếp hạng | 12 | Đúng từng mã, top tuyệt đối vs tốc độ | Cặp đổi mã thắng trên dữ liệu thật |
| F09 Lọc và thiếu dữ liệu | 10 | 0 dòng hợp lệ vs thiếu mẫu số | Không biến thiếu thành 0 |
| F10 Mơ hồ và hỏi thừa | 10 | Thiếu kỳ, phạm vi, cách đo | Có câu rõ đối chứng; nhãn loại mơ hồ |
| F11 Thời điểm và phiên bản | 10 | Kỳ mới nhất đơn/đa mã, restatement | `question_date`, `as_of_date`, bản báo cáo |
| F12 Ngoài phạm vi | 8 | Từ chối đúng, giải thích giới hạn | Không được lẫn với 0 dòng/thiếu dữ liệu |
| **Tổng** | **120** | | |

## Quy tắc chia Dev/Test

1. Chốt `family_id`, `template_group_id`, `pair_id` và `source_scenario_id` trước khi chia. Mọi paraphrase, thay ticker/kỳ từ cùng template, hai vế đối lập và biến thể của cùng tình huống nguồn đi cùng một nhóm.
2. Phân chia theo nhóm/họ độc lập, không chia ngẫu nhiên từng câu. Có thể bắt đầu đề xuất Dev 40/Test 80 nhưng ưu tiên không rò rỉ hơn đúng tỷ lệ. Chỉ báo cáo con số cuối khi thực hiện xong.
3. 30 câu pilot đã công khai: không đưa chúng hoặc biến thể gần vào Test chính. Ghi nhóm nào đã lộ qua pilot để loại trừ. Nếu toàn bộ mẫu của một họ đã dùng để phát triển, dùng họ đó ở Dev/chẩn đoán, không gọi là Test mù của họ mới.
4. TV4 lập danh sách Test ở kho riêng có quyền truy cập. Chỉ gửi Dev cho TV2/TV3. Hash và số lượng không thay thế phân quyền. Không lưu Test trong repo công khai, kể cả nhờ `.gitignore`.
5. TV5 gán nhãn hành động độc lập trước khi xem nhãn TV4; thống nhất ngưỡng Cohen's kappa và cách giải quyết bất đồng trước nghiệm thu. Không tự điền một ngưỡng chưa được nhóm duyệt.
6. Câu phát sinh sau khi đã nhìn lỗi Dev vào tập chẩn đoán. Không thêm chúng vào Test chính đã khóa.

## Các trục nhãn

- Đầu vào: bảng chuẩn hóa, bảng giả có đánh dấu, tài liệu gốc; không gộp thành cùng điều kiện thí nghiệm.
- Kỳ: một quý, YTD, năm, TTM, nhiều mốc; số doanh nghiệp và số ô nguồn riêng biệt.
- Phép toán: lookup, hiệu, tỷ lệ, tăng trưởng, tổng, bình quân, lọc, rank, nhiều bước.
- Hành động: trả số, hỏi làm rõ, trả kèm cảnh báo, báo thiếu, rỗng hợp lệ, từ chối.
- Ngữ nghĩa: ngành, scope, basis, unit, phiên bản, độ sẵn có tại ngày hỏi.
- Nguồn: `real`, `synthetic`, `real_data_withheld`; tuyệt đối không gắn bảng giả thành số thật.

## Kiểm tra cặp đối lập trước đưa vào benchmark

Ghi cả hai câu, công thức, đầu vào, kết quả, đơn vị và ô nguồn. Hai kết quả phải phân biệt sau làm tròn và dung sai. Với top/rank, hai cách hỏi cần cho mã thắng khác nhau; thay đổi nhãn metric nhưng cùng mã thắng không đủ. Với % vs điểm %, không chỉ thay tên đơn vị. Với rỗng/thiếu, phải chứng minh đầy đủ đầu vào ở ca rỗng và chỉ ra ô bị thiếu ở ca thiếu.

Pilot hiện có 5 cặp đối lập ngữ nghĩa và 1 cặp đủ/che đầu vào. Chưa có các ca vốn âm, mẫu số gần 0, TTM giữa năm hay %/điểm %; không ghi nhận chúng là đã kiểm chứng.
