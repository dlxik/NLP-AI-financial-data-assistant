# NLP-AI-financial-data-assistant

Trợ lý hỏi đáp dữ liệu tài chính tiếng Việt.

- [Kế hoạch và phân công](kehoach.md)
- [Gói giai đoạn 1 của Hiền (TV4)](benchmark/phase1/README.md)
- [30 câu pilot và Gold nháp có truy vết](benchmark/phase1/PILOT_VA_GOLD.md)

Kiểm tra gói pilot (Node.js 18+):

```powershell
node benchmark/phase1/validate.mjs --require-pdfs
```

Gold hiện do trợ lý hỗ trợ chép/tính từ báo cáo gốc, chờ Hiền tính lại và TV5 kiểm tra độc lập theo kế hoạch. Các PDF tải cục bộ không được commit; URL và SHA256 nằm trong manifest nguồn.
