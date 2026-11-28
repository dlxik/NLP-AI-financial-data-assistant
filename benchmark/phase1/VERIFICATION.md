# Biên bản kiểm chứng — 23/11/2026

**Kết quả: không phát hiện lỗi chép số hoặc phép tính trong Gold pilot hiện tại.** Kiểm tra do Codex thực hiện theo yêu cầu Hiền, không phải xác nhận Hiền đã tự tính hoặc TV5 đã nghiệm thu độc lập.

## Đã kiểm tra

| Nội dung | Kết quả |
|---|---|
| Đọc lại 27 ô nguồn trên 11 trang ảnh PDF của 5 báo cáo | Khớp 27/27: hàng, kỳ, giá trị và đơn vị |
| Tính lại 26 dòng số của 23 câu trả số | Khớp; dùng phân số BigInt chính xác, không gọi `build.mjs` hoặc thư viện TV2 |
| 7 câu hành động: P18–P22, P27–P28 | Phù hợp chính sách hỏi lại và fixture đã mô tả |
| P20/P21: hai cách hiểu mơ hồ | Các giá trị giải nghĩa khớp; không xem chúng là ý định thật đã xác nhận |
| Xếp hạng P25/P26 | HPG đứng đầu doanh thu quý; FPT đứng đầu YoY, hai mã thắng khác nhau |
| Lọc P27 | Cả 3 mã đủ dữ liệu, không mã nào có YoY > 100% |
| P28 | Allowlist loại đúng `VNM_eq0`; chỉ đúng nếu runner thực sự áp dụng fixture |
| CP01–CP06 | 5 cặp ngữ nghĩa khác kết quả, 1 cặp đủ/thiếu đầu vào khác hành động |
| 5 tệp PDF | SHA256 khớp manifest |

## Đường dẫn kiểm chứng số nguồn

Trang dưới đây là **số trang trong PDF, bắt đầu từ 1**; số trang in cũng có trong `source_cells.json`.

| Báo cáo | Trang PDF đã đọc lại | Ô số |
|---|---|---|
| [HPG quý IV](sources/HPG_2024Q4.pdf) | 5, 6 | 4 doanh thu, LNST năm, vốn đầu/cuối |
| [FPT quý IV](sources/FPT_2024Q4.pdf) | 7, 8 | 4 doanh thu, LNST năm, vốn đầu/cuối |
| [VNM quý IV VAS](sources/VNM_2024_VAS.pdf) | 7, 8, 9 | 4 doanh thu, LNST năm, vốn đầu/cuối |
| [VCB năm](sources/VCB_2024.pdf) | 66, 67 | LNST năm, vốn đầu/cuối; số đầu kỳ là bản trình bày lại |
| [CTG quý IV](sources/CTG_2024Q4.pdf) | 4, 7 | LNST năm, vốn đầu/cuối, đơn vị triệu VND |

## Những điểm cần giữ nguyên khi sử dụng

1. **FPT dùng bản quý IV chưa kiểm toán.** Bản năm kiểm toán đã tải có số khác. Không thay một mình tử hoặc mẫu ROE bằng số của bản năm. Gold hiện đúng với bản quý IV được chỉ định trong câu.
2. **ROE trong pilot dùng tổng LNST và tổng vốn chủ gồm NCI.** FPT dùng mã 400 gồm cả nguồn kinh phí/quỹ khác theo quy ước đã ghi. Kết quả không được mô tả là ROE do doanh nghiệp công bố hoặc ROE riêng cổ đông công ty mẹ.
3. **VCB giữ số so sánh 2023 đã trình bày lại.** Không lấy số đầu kỳ của phiên bản cũ để thay vào.
4. **P28 là dữ liệu bị che có chủ đích.** Bản PDF thực sự có vốn đầu kỳ. Chưa có runner của TV3 để chứng minh không rò rỉ ô này lúc chạy.
5. **CP06 không phải cặp mơ hồ ngôn ngữ.** Nó kiểm tra hành vi khi thay đổi đầu vào; chỉ CP01–CP05 là đối lập ngữ nghĩa.

## Kiểm tra tài liệu liên quan

Đã mở lại [ViNumQA](https://aclanthology.org/2025.vlsp-1.25.pdf), [viewer ViFinQA](https://huggingface.co/datasets/HuuDong03uet/ViFinQA) và [VCBS AI](https://ai.vcbs.com.vn/) ngày 23/11/2026. Giới hạn lấy mẫu vẫn giữ nguyên: 30 mẫu là ID ViFinQA, không phải 10 câu mỗi nguồn; các nhãn phép toán dựa trên câu hỏi công khai, chưa kiểm chứng chương trình Gold của tập tham chiếu. Không nâng kết quả kiểm chứng pilot thành tuyên bố đã kiểm chứng toàn bộ benchmark bên ngoài.

## Tái chạy

```powershell
node benchmark/phase1/audit.mjs
node benchmark/phase1/validate.mjs --require-pdfs
```

`assistant_audit.json` ghi kết quả từng câu/ô và hash chính xác của các tệp được kiểm tra. Script tính lại dùng bộ số được chép lại sau khi xem ảnh trong lần kiểm chứng này; chạy lại script **không tự đọc lại PDF**. Nếu sửa câu, Gold, nguồn hoặc fixture, biên bản này không tự có hiệu lực cho phiên bản mới.

Không đánh dấu các trường `hien_checked_source`, `hien_recalculated` hoặc `tv5_result` vì những người đó chưa thực hiện kiểm tra trong phiên này. Cổng giai đoạn còn cần bộ chấm/tấn công bộ chấm, snapshot và xác nhận của nhóm. Phần kiểm chứng hỗ trợ bằng trợ lý đã hoàn thành; 0 số phải sửa.
