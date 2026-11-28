# Đối chiếu công trình và 30 mẫu câu

Phạm vi: nguồn công khai truy cập ngày 22/11/2026; phần nhận định khoảng trống bên dưới là suy luận thiết kế của TV4, không phải kết quả thực nghiệm đối đầu.

| Nguồn | Điều quan sát được | Liên hệ với đề tài |
|---|---|---|
| [ViNumQA — bài tổng kết VLSP 2025](https://aclanthology.org/2025.vlsp-1.25.pdf) | Kết hợp dữ liệu tiếng Việt với FinQA dịch; 4.074 bộ câu/chương trình/đáp án; có đầu vào bảng, văn bản hoặc kết hợp. Đánh giá kết quả thực thi và chương trình suy luận. | Làm rõ chương trình tính là điểm tham chiếu tốt; thử nghiệm của nhóm bổ sung quản trị kỳ/phiên bản, cảnh báo và hành động hỏi lại trên snapshot nhiều mã. |
| [ViFinQA — dataset card và viewer](https://huggingface.co/datasets/HuuDong03uet/ViFinQA) | Card mô tả 1.012 câu và 1.973 báo cáo của 100 doanh nghiệp, giai đoạn 2015–2025. Viewer công khai câu và ID. | Gần bài toán truy vấn cả kho tài liệu. Cần phân biệt lỗi tìm đúng báo cáo với lỗi phép tính trên bảng đã chuẩn hóa. |
| [VCBS AI — trang sản phẩm](https://ai.vcbs.com.vn/) | Công bố khả năng tra cứu thị trường, đọc báo cáo, so sánh doanh nghiệp và lọc cổ phiếu; sử dụng yêu cầu tài khoản. | Là tham chiếu sản phẩm, chưa có bộ Gold/cấu hình/bộ chấm công khai được kiểm chứng trong phiên này. Không xếp ngang một benchmark nghiên cứu có thể tái lập. |

Nguồn bổ sung của ViNumQA: [trang ban tổ chức](https://vlsp.org.vn/vlsp2025/eval/numqa). Bài gốc phân biệt public/private test và chấm chương trình; không suy ra rằng bộ dữ liệu đã hoặc chưa bao phủ toàn bộ tình huống đặc thù của nhóm.

## Bộ 30 mẫu đã gắn nhãn

`related_work_samples.json` định danh chính xác **30 câu có thật, ID 1–30 của viewer ViFinQA**. Không chép toàn bộ câu của bên thứ ba vào repo. Mở URL nguồn và tra `source_question_id` để đọc nguyên văn. Mỗi dòng có kiểu đầu vào, số kỳ, số doanh nghiệp, phép toán và phạm vi bằng chứng đã xem.

Đây là mẫu thuận tiện lấy từ phần công khai, thiên về truy xuất một giá trị của một doanh nghiệp/một kỳ: cả 30 được gắn `lookup`. Quy đổi đơn vị cần kiểm tra báo cáo, chưa gán là phép tính đã xác nhận. Số kỳ/số doanh nghiệp đếm theo đích hỏi, không đếm các thực thể hay cột đối chiếu phụ trong tài liệu.

**Giới hạn:** Không phải mẫu ngẫu nhiên hoặc mẫu cân bằng ba nguồn; chưa lấy được tập câu gốc ViNumQA để gắn nhãn riêng và chưa chạy hội thoại VCBS AI. Không gọi 30 mẫu này là “10 câu mỗi công trình”, không suy rộng tần suất họ câu cho toàn bộ ViFinQA. Link GitHub được dataset card nêu trả 404 khi thử, nên không viện dẫn code repo như đã đọc. Đầu vào cần bổ sung nếu nhóm yêu cầu lấy mẫu mỗi nguồn: bản dữ liệu ViNumQA được phép dùng, hội thoại VCBS có nguồn/ngày/cấu hình được phép nghiên cứu.

## Khoảng trống nhóm có thể kiểm tra

1. Cùng mã và năm nhưng hiểu quý đơn lẻ thành lũy kế: dùng cặp hỏi có số thật khác nhau.
2. Đúng công thức nhưng sai mã, đơn vị, phiên bản hay phạm vi hợp nhất: cần nhận diện đầy đủ khóa kết quả và ô nguồn.
3. Ngân hàng không có ánh xạ “doanh thu thuần” đã thống nhất: phải hỏi rõ thay vì đổi chỉ tiêu ngầm.
4. Số đúng không đủ để đánh giá hành vi: tách hỏi thừa, báo thiếu đúng, bảng rỗng hợp lệ và trả số sai không cảnh báo.

Đây là hướng nghiên cứu đề xuất, không phải tuyên bố “chưa ai làm”. Nhóm không khảo sát ý định người dùng thật nên chỉ đánh giá phát hiện mơ hồ, hỏi thừa và tính minh bạch của giả định; không kết luận chính sách nào hiểu người dùng hơn.
