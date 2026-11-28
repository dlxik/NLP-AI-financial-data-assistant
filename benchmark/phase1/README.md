# Giai đoạn 1 của Hiền — TV4

**Trạng thái mới nhất:** [Hiền đã duyệt kết quả kiểm chứng qua trợ lý ngày 28/11/2026](HIEN_APPROVAL.md) cho 30 câu. Phần kiểm tra tự tay của Hiền và kiểm tra độc lập TV5 không được ghi nhận thay bằng việc duyệt này.

Ngày chuẩn bị: 22–23/11/2026. Vai trò và 5 mã đã được Hiền xác nhận trong phiên làm việc.

**Đã có bộ hồ sơ pilot để kiểm tra/bàn giao. Chưa phải Gold do con người tính độc lập và chưa nghiệm thu cổng giai đoạn 1.** Trợ lý chép ô số từ ảnh báo cáo và tính số học trong chương trình riêng; không dùng code TV2. Theo kế hoạch, Hiền vẫn cần tự tính lại, TV5 lấy mẫu kiểm tra độc lập. Không ký thay hai bước này.

## Mở theo thứ tự

**Mới:** [Kết quả kiểm chứng ngày 23/11/2026](VERIFICATION.md) — đã đọc lại ô nguồn và tính lại bằng số học chính xác, không phát hiện lỗi số.

1. [Bộ 30 câu và lời giải](PILOT_VA_GOLD.md): bản dễ đọc để Hiền kiểm tra.
2. [Đối chiếu công trình](RELATED_WORK.md) và [30 mẫu có nhãn](related_work_samples.json).
3. [Khung họ câu cho 120 câu giai đoạn 2](QUESTION_FAMILIES.md).
4. [Quy ước Gold và schema](ANNOTATION_GUIDE.md).
5. [Việc còn lại và bàn giao](HANDOFF.md).

## Các tệp máy đọc

| Tệp | Nội dung |
|---|---|
| `pilot_questions.json` | 30 câu, họ câu, mã, kỳ, fixture; công khai pilot |
| `pilot_gold.json` | Hành động, kết quả, công thức, toán hạng, cảnh báo cụ thể |
| `source_cells.json` | 27 ô chép trực tiếp, trang PDF/trang in, hàng, cột, đơn vị |
| `sources/manifest.json` | 5 báo cáo thực dùng, URL, SHA256, phiên bản |
| `contrast_pairs.json` | 6 cặp đối lập, không tách hai vế qua Dev/Test |
| `input_fixtures.json` | Allowlist đầu vào thường và ca che vốn đầu kỳ |
| `review_register.json` | Phiếu kiểm tra 30 câu, chưa đánh dấu hoàn tất |

5 mã: FPT (công nghệ), HPG (thép), VNM (sữa), VCB và CTG (ngân hàng). Chưa xác nhận tư cách VN30 tại ngày danh mục do TV1 chốt. Bộ này dùng BCTC 2024 để kiểm tra phương pháp; **không phải kho dữ liệu 5 năm**, cũng không phải số liệu kỳ gần nhất năm 2026.

Snapshot bằng chứng v0.1 cố định bản quý IV của HPG/FPT/VNM/CTG và bản năm kiểm toán VCB có trình bày lại số 2023. Không tự cập nhật sang phiên bản mới hơn. Cả 5 dùng báo cáo hợp nhất theo VAS. File `VNM_2024_VAS.pdf` thực tế là BCTC quý IV, không phải bản kiểm toán năm; đã ghi đúng trong manifest. Các bản FPT năm kiểm toán/VNM thường niên tải để đối chiếu không thuộc snapshot tính Gold.

## Kiểm tra

Yêu cầu Node.js 18+; không cần cài thư viện để chạy kiểm tra:

```powershell
node benchmark/phase1/validate.mjs --require-pdfs
node benchmark/phase1/validate.mjs --gate
```

Lệnh đầu kiểm tra cấu trúc, công thức, tham chiếu, thứ hạng, cặp đối lập và hash PDF. Lệnh thứ hai cố ý trả mã thoát 2 khi chưa có kiểm tra của Hiền/TV5. Cả hai không thay Bộ chấm TV5.

`node benchmark/phase1/build.mjs` tái sinh dữ liệu và bản đọc từ các ô số chép trong script. Lệnh này ghi đè bộ câu/Gold; chỉ chạy khi cập nhật nháp, không chạy trên bản đã nghiệm thu. Phiếu review hiện có được giữ nguyên, nhưng cần hủy hiệu lực review liên quan nếu thay câu/số. Giữ PDF đã tải để manifest tái sinh có hash.

PDF và ảnh kiểm tra được giữ cục bộ ở `sources/`, loại khỏi Git. URL và hash nằm trong manifest để TV5 tải đúng bản. Kiểm tra quyền chia sẻ trước khi đưa toàn văn lên kho chung; đây không phải tuyên bố giấy phép phân phối lại. Không tạo hoặc công khai Test chính trong giai đoạn này.
