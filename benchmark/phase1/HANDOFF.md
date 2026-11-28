# Bàn giao giai đoạn 1 — Hiền (TV4)

**Rà soát branch ngày 28/11/2026:** Bộ hồ sơ sẵn sàng đưa lên `main` để bàn giao, nhưng chưa hoàn thành nghiệm thu giai đoạn 1. Chạy lại `audit.mjs` và `validate.mjs --require-pdfs` đều đạt; `validate.mjs --gate` vẫn báo 30 phiếu Hiền chưa xác nhận và 0 mẫu TV5. Việc đưa lên `main` không đồng nghĩa đóng cổng giai đoạn. Các tài liệu tham chiếu vẫn chỉ có mẫu câu ViFinQA; cần bổ sung bằng chứng từ hai nguồn còn lại theo phạm vi nhóm thống nhất.

**Cập nhật 23/11/2026:** Đã kiểm chứng lại bằng trợ lý theo yêu cầu Hiền: 27/27 ô nguồn và 26 dòng số khớp, 30 hành động/kết quả phù hợp quy ước. Xem [biên bản kiểm chứng](VERIFICATION.md) và `assistant_audit.json`. Không thay chữ ký kiểm tra độc lập của TV5.

## Hồ sơ đã chuẩn bị

| Yêu cầu của kế hoạch | Đã làm | Trạng thái nghiệm thu |
|---|---|---|
| Đối chiếu ViNumQA, ViFinQA, VCBS AI | Báo cáo nguồn công khai, điểm so sánh và giới hạn | Có bản nháp có nguồn |
| Khoảng 30 câu tham chiếu có nhãn | 30 ID câu thật ViFinQA, đủ 4 trục nhãn | Chưa cân bằng giữa 3 nguồn; chưa có câu ViNumQA/phiên VCBS để gắn nhãn riêng |
| 30 câu pilot | Đủ 30, 5 mã đã được Hiền đồng ý | Cần đồng bộ snapshot TV1 |
| Gold độc lập với thư viện TV2 | 30 Gold hành động/số, 27 ô nguồn, công thức và 5 PDF có hash | Trợ lý tính hỗ trợ; Hiền chưa tự tính lại, TV5 chưa kiểm tra |
| Cặp đối lập có số thật | 5 cặp ngữ nghĩa + 1 cặp dữ liệu bị che | Kiểm tra tự động khác kết quả đã đạt; chờ xác nhận con người |
| Khung họ câu | 12 họ, dự kiến 120 câu, quy tắc tránh rò rỉ | Bản thiết kế v1 |

## Hiền làm tiếp theo thứ tự

1. Mở `PILOT_VA_GOLD.md`, tra từng `source_cell_id` trong `source_cells.json` và mở đúng trang PDF. Kiểm tra toàn bộ ô dùng lại một lần rồi ghi rõ chúng áp dụng cho các câu nào.
2. Tự tính lại bằng máy tính độc lập, không nhìn giá trị Gold trước khi tính. Điền `review_register.json`: người kiểm tra, ngày, đã xem nguồn, đã tính lại, sai khác nếu có. Chỉ đánh dấu khi thực sự làm.
3. Bàn giao gói này cho TV5 để người đó lấy mẫu ngẫu nhiên bằng seed đã ghi, tính lại từ PDF và ghi kết quả. Không chọn mẫu chỉ vì dễ/đã biết đúng. Nhóm cần chốt cỡ mẫu; chưa tự đặt thay kế hoạch.
4. Chốt với TV1 snapshot, 5 mã và bản báo cáo. Nếu đổi phiên bản, đổi `snapshot_id`, tính lại tất cả Gold phụ thuộc và mở lại review; không thay số âm thầm.
5. Chốt với TV2 định nghĩa ROE tổng hay phần cổ đông mẹ và quy tắc ca biên. Pilot đã viết công thức ngay trong câu nên không đòi hỏi đoán ngầm.
6. Nếu yêu cầu đối chiếu cân bằng từng nguồn, bổ sung mẫu ViNumQA và phiên VCBS có thể trích dẫn. Giữ số liệu hiện tại đúng với phạm vi đã quan sát.

## Phần cần các bạn khác bàn giao

| Người/vai trò | Đầu vào cần nhận | Mục đích |
|---|---|---|
| TV1 | Danh mục VN30 chốt ngày, snapshot ≥5 năm, PDF gốc, ngày công bố/phiên bản | Khẳng định phạm vi và tái tạo point-in-time |
| TV2 | Đặc tả 4.3–4.4, chỉ số đã thống nhất | Chốt nhãn ca biên trước mở rộng |
| TV3 | Output Contract và cơ chế cấp fixture | Ánh xạ kết quả pipeline vào khóa chấm; P28 không được nhìn ô bị che |
| TV5 | Kiểm tra nguồn, bộ chấm, kết quả tấn công bộ chấm | Nghiệm thu thật, không chỉ kiểm tra cấu trúc tệp |

## Biên bản cổng giai đoạn 1 — chưa ký

- [ ] TV5 truy vết mẫu Gold và tính lại khớp 100%.
- [ ] Bộ chấm phân biệt trả sai, hỏi thừa, báo thiếu đúng, rỗng hợp lệ.
- [ ] Các cặp đối lập được kiểm tra trên snapshot đã thống nhất.
- [ ] Tấn công đảo kỳ, đổi số giữa mã, cảnh báo chung, luôn hỏi lại đều bị phát hiện.
- [ ] Nhóm quyết định giữ ngân hàng trong mẫu chính hay chuyển tập mở rộng.
- [ ] Đóng băng chỉ số, quy tắc và bộ chấm để chuyển giai đoạn.

Kiểm tra tự động của gói TV4 đã đạt 30 câu/27 ô/6 cặp/5 hash; điều đó không đánh dấu bất kỳ ô nghiệm thu nhóm nào ở trên. Chưa có tập Test chính, chưa gửi thông điệp hay chia sẻ dữ liệu cho thành viên khác.
