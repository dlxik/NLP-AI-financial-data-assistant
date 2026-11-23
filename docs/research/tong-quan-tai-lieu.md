# Tổng quan tài liệu liên quan

**Ngày tra cứu:** 23/11/2026 · **Người tổng hợp:** TV2

Mỗi mục có đường dẫn nguồn. Mục ghi **[chưa kiểm chứng]** là mục chưa xác nhận được trên trang gốc: không trích dẫn trong báo cáo khi chưa tự mở nguồn kiểm tra lạidirectory structure. Phần 1–3 phục vụ TV4 khi viết báo cáo đối chiếu. Phần 7–8 phục vụ TV1/TV2 khi ánh xạ mã số.

---

## 1. Ba công trình tiếng Việt cần đối chiếu (kehoach.md, mục 2.1, TV4) và một công trình gần nhất

| Công trình | Đầu vào | Số kỳ | Số DN | Phép toán / đầu ra | Có từ chối / hỏi lại? |
|---|---|---|---|---|---|
| **ViNumQA** (VLSP 2025) | 1 đoạn văn + 1 bảng mỗi câu (kiểu FinQA) | thường 2–3 năm trong bảng; BCTC 2020–2025 | không công bố | chương trình DSL kiểu FinQA (`divide(914, 391)`) + đáp số | Không |
| **ViFinQA** (Hugging Face) | 1.973 BCTC năm đã OCR, truy xuất trên toàn kho | năm, 2015–2025 | 100 | số học, quy đổi đơn vị, tổng hợp; **không có đáp án Gold** | Không rõ |
| **VCBS MCP** (sản phẩm) | dữ liệu đã chuẩn hóa của VCBS, cấp qua 65 công cụ tra cứu cho LLM | không công bố | không công bố | tra cứu; **không công bố đánh giá** | Không rõ |
| **FinStat2SQL** (INLG 2025) — *gần nhất* | CSDL SQL (FiinPro) | quý & năm, 2016–Q3/2024 | 200 (VN30, HNX30…) | Text-to-SQL; có YoY, QoQ, TTM, ROE | Không |

- **ViNumQA.** Le Ngoc Toan, Ha My Linh, Pham Thi Duc, Ngo The Quyen, Nguyen Thi Minh Huyen (2025). *VLSP 2025 challenge: Numerical Reasoning Question and Answer.* Proc. 11th VLSP Workshop, tr. 187–196. https://aclanthology.org/2025.vlsp-1.25 · Bản tạp chí: VNU J. Sci.: Comp. Sci. & Com. Eng. 41(2), DOI 10.25073/2588-1086/vnucsce.6507, https://jcsce.vnu.edu.vn/index.php/jcsce/article/view/6507
  - **Quy mô và nguồn.** 4.074 bộ (câu hỏi, chương trình, đáp án), chia 2.993 train / 584 validation / 497 test. Trong đó 2.005 bộ dịch từ FinQA rồi được người kiểm, 2.069 bộ do LLM sinh từ BCTC Việt Nam rồi được người duyệt.
  - **Thước đo và kết quả.** Execution Accuracy tốt nhất 84,0%, Program Accuracy tốt nhất 76,6%.
  - **Ý nghĩa với dự án:** đây là baseline tiếng Việt chính, nhưng mỗi câu chỉ có **một ngữ cảnh**: không có CSDL, không hỏi nhiều kỳ hay nhiều mã, không có hành vi từ chối.
- **ViFinQA.** Bộ dữ liệu `HuuDong03uet/ViFinQA`: https://huggingface.co/datasets/HuuDong03uet/ViFinQA
  - **Nội dung theo thẻ dữ liệu:** 1.012 câu hỏi, chỉ có id và câu hỏi, **không có đáp án, chương trình hay bằng chứng**. Kho văn bản là TiniX OCR, giấy phép CC BY-NC 4.0.
  - **Bài báo:** thẻ dữ liệu nhắc tới bài "ViFinQA: A Comprehensive and Challenging Benchmark for End-to-End Vietnamese Financial Reasoning", nhưng **không tìm thấy bài đã công bố**, và repo GitHub trả về 404 **[chưa kiểm chứng]**.
  - ⚠ **TV4 lưu ý:** không thể so sánh độ chính xác với ViFinQA. Chỉ đối chiếu được theo **kiểu đầu vào và loại câu hỏi**.
- **VCBS MCP.** VnEconomy (27/10/2026), "VCBS MCP: Kết nối AI và dữ liệu cho nhà đầu tư": https://vneconomy.vn/vcbs-mcp-ket-noi-ai-va-du-lieu-cho-nha-dau-tu.htm
  - **Cách hoạt động:** kết nối ChatGPT, Claude, Gemini, Grok với dữ liệu "đã làm sạch, chuẩn hóa" của VCBS (65 công cụ). VCBS tuyên bố không bảo đảm mọi câu trả lời chính xác.
  - **Chưa xác định:** không rõ có cấp BCTC quý hay không; không tìm thấy một chatbot riêng tên "VCBS AI" **[chưa kiểm chứng]**.
  - **Ý nghĩa:** đây là dạng thương mại của ý tưởng "thư viện công cụ đã tuyển chọn" (phương pháp B/C), nhưng chưa có đánh giá công khai.
- **FinStat2SQL.** Hung Quang Nguyen, Anh Phuong Trinh, Hung Phan Quoc Mai, Phong Tuan Trinh (2025). INLG 2025, tr. 449–464. https://aclanthology.org/2025.inlg-main.27/
  - **Nội dung:** hệ đa tác tử Text-to-SQL trên BCTC theo VAS. Tập đánh giá khoảng 300 câu, chấm bằng LLM. Mô hình 7B sau tinh chỉnh đạt 61,3%.
  - **Ý nghĩa:** là công trình **gần nhất** (CSDL cấu trúc, có VN30), nhưng **không có semantic layer, không có cặp đối lập, không đo lỗi âm thầm**. Đề xuất bổ sung vào chương đối chiếu.

## 2. Benchmark hỏi đáp số liệu tài chính (tiếng Anh)

| Công trình | Nguồn | Điểm liên quan |
|---|---|---|
| FinQA — Chen et al., EMNLP 2021 | https://aclanthology.org/2021.emnlp-main.300/ | 8.281 cặp câu hỏi, mỗi câu có chương trình Gold. ViNumQA kế thừa DSL và thước đo EA/PA |
| TAT-QA — Zhu et al., ACL 2021 | https://aclanthology.org/2021.acl-long.254/ | Bảng + văn bản; có xử lý đơn vị và thang đo |
| ConvFinQA — Chen et al., EMNLP 2022 | https://aclanthology.org/2022.emnlp-main.421/ | Chuỗi hội thoại suy luận số |
| DocFinQA — Reddy et al., ACL 2024 | https://aclanthology.org/2024.acl-short.42/ | Câu hỏi đặt trên toàn bộ hồ sơ SEC; khâu truy xuất là điểm nghẽn |
| FinanceBench — Islam et al., 2023 | https://arxiv.org/abs/2311.11944 | GPT-4-Turbo + truy xuất **sai hoặc từ chối 81%** (mẫu 150 câu). Gần với cách tách "tỷ lệ trả lời / sai trong câu đã trả lời" của dự án |
| BizBench — Krumdick et al., ACL 2024 | https://aclanthology.org/2024.acl-long.452/ | Tổng hợp chương trình Python, tương ứng phương pháp A |
| BIRD — Li et al., NeurIPS 2023 | https://arxiv.org/abs/2305.03111 | Text-to-SQL; ChatGPT đạt 40,08% so với người 92,96% |
| Wretblad et al., 2024 | https://arxiv.org/abs/2402.12243 | BIRD có nhiều Gold SQL sai. Đây là lý do cần **Gold độc lập** (TV4) |
| FinSQL — Zhang et al., 2024 | https://arxiv.org/abs/2401.10506 | Text-to-SQL tài chính tiếng Trung (venue **[chưa kiểm chứng]**) |
| FLINT — Sehanobish et al., 2026 | https://arxiv.org/abs/2610.03524 | Text-to-SQL thông dụng đạt dưới 50% trên CSDL tài chính thực tế |

## 3. Sinh code cho suy luận số

- **Program of Thoughts.** Chen, Ma, Wang, Cohen, TMLR 2023: https://arxiv.org/abs/2211.12588. Tăng khoảng 12% so với CoT trên FinQA, ConvFinQA, TAT-QA. Đây là cơ sở cho phương pháp A/B.
- **PAL.** Gao et al., ICML 2023: https://proceedings.mlr.press/v202/gao23f.html. LLM viết chương trình, bộ thông dịch thực thi.

## 4. Semantic layer cho LLM

- **dbt Semantic Layer / MetricFlow:** https://docs.getdbt.com/docs/build/about-metricflow. Khai báo chỉ số một lần rồi biên dịch ra truy vấn. Đây là khuôn mẫu cho `get_metric(...)`.
- **Sequeda, Allemang, Jacob (2023/2024).** arXiv:2311.07509: https://arxiv.org/abs/2311.07509. GPT-4 zero-shot đạt 16% khi truy vấn SQL trực tiếp, 54% khi có lớp tri thức (knowledge graph).
- **dbt Labs (Ganz, 2023):** https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms. Đạt 83% trên các câu mà semantic layer biểu đạt được.
- **dbt Labs (Ganz & Perigaud, 04/2026):** https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026
  - Semantic layer đạt 98–100%, Text-to-SQL đạt 84–90%.
  - Semantic layer **báo lỗi thay vì trả số sai**, còn Text-to-SQL trả số sai trông hợp lý. Đây là bằng chứng trực tiếp cho thước đo **lỗi âm thầm** của dự án.
  - Cái giá phải trả là độ phủ: câu nằm ngoài lớp đã mô hình hóa thì không trả lời được, tương ứng việc ghi nhận các câu C không biểu đạt được.
- **Khảo sát Text-to-SQL.** Hong et al., arXiv:2406.08426: https://arxiv.org/abs/2406.08426

## 5. Mơ hồ, hỏi làm rõ, từ chối trả lời

| Công trình | Nguồn | Điểm liên quan |
|---|---|---|
| AmbigQA — Min et al., EMNLP 2020 | https://aclanthology.org/2020.emnlp-main.466/ | Khung khái niệm câu hỏi mơ hồ |
| AmbiQT — Bhaskar et al., EMNLP 2023 | https://aclanthology.org/2023.emnlp-main.436/ | Hơn 3.000 câu, mỗi câu có 2 cách viết SQL đều hợp lệ |
| AMBROSIA — Saparina & Lapata, NeurIPS D&B 2024 | https://arxiv.org/abs/2406.19073 | Mơ hồ về phạm vi, gắn kết, độ mơ hồ của từ |
| PRACTIQ — Dong et al., NAACL 2025 | https://aclanthology.org/2025.naacl-long.13 | Phân loại câu rồi hỏi làm rõ. **Gần nhất** với thử nghiệm "mặc định vs hỏi lại" (RQ3) |
| CLAMBER — Zhang et al., ACL 2024 | https://aclanthology.org/2024.acl-long.578 | CoT/few-shot làm LLM tự tin quá mức với câu mơ hồ |
| Selective QA — Kamath, Jia, Liang, ACL 2020 | https://aclanthology.org/2020.acl-main.503/ | Đánh đổi giữa độ phủ và độ chính xác, tương ứng A/N và W/A |
| TrustSQL — Lee et al. | https://arxiv.org/abs/2403.15879 | Hoặc sinh SQL, hoặc từ chối; trả sai bị phạt (venue **[chưa kiểm chứng]**) |

## 6. Phương pháp đánh giá (phục vụ TV5)

- **Dror et al., ACL 2018,** "The Hitchhiker's Guide to Testing Statistical Significance in NLP": https://aclanthology.org/P18-1128/
- **Berg-Kirkpatrick, Burkett, Klein, EMNLP-CoNLL 2012** (bootstrap ghép cặp): https://aclanthology.org/D12-1091/
- **Miller, 2024,** "Adding Error Bars to Evals", arXiv:2411.00640: https://arxiv.org/abs/2411.00640. Khuyến nghị **sai số chuẩn theo cụm** khi các câu hỏi có quan hệ với nhau, và so sánh mô hình bằng **hiệu ghép cặp**. Đây là căn cứ cho **bootstrap theo họ câu**.
- **Cohen, 1960,** "A coefficient of agreement for nominal scales", Educ. Psychol. Meas. 20(1):37–46, DOI 10.1177/001316446002000104.

## 7. Chuẩn mực và mẫu biểu BCTC Việt Nam

### 7.1. Doanh nghiệp phi tài chính

| Văn bản | Phạm vi | Ghi chú cho ánh xạ |
|---|---|---|
| TT200/2014/TT-BTC | BCTC riêng, năm tài chính ≤ 2025 | B02-DN: 10 DTT, 20 LN gộp, 50 LNTT, 60 LNST. B01-DN: 270 tổng TS, 300 nợ phải trả, 400 VCSH, 440 tổng nguồn vốn |
| TT202/2014/TT-BTC | BCTC **hợp nhất**, ≤ 2025 | Thêm **61** (LNST cổ đông mẹ), **62** (LNST CĐ không kiểm soát), **429** (lợi ích CĐ không kiểm soát), 269 lợi thế thương mại. Mã 24 trên B02/HN = lãi/lỗ công ty liên doanh liên kết |
| **TT99/2025/TT-BTC** (27/10/2025) | BCTC riêng, năm tài chính bắt đầu từ 01/01/2026 | Mã 10, 60 **không đổi**. **Tổng tài sản 270 → 280**. Mã 21 mới (lãi/lỗ thanh lý BĐS đầu tư); doanh thu tài chính 21 → 22; chi phí tài chính 22 → 23; chi phí đi vay 23 → 24. Mẫu "Bảng cân đối kế toán" đổi tên thành "Báo cáo tình hình tài chính" |
| **TT43/2026/TT-BTC** (20/04/2026) | Sửa TT202, áp dụng từ năm tài chính 2026 | 61, 62, 429 **không đổi**. Lợi thế thương mại 269 → 279. Lãi/lỗ công ty liên doanh liên kết 24 → **27** |
| VAS 27 | BCTC giữa niên độ | B02a-DN có cột "Quý này (năm nay / năm trước)" và "Lũy kế từ đầu năm". **Không có cột quý liền trước**, nên QoQ phải tự tính |

Nguồn:
- KPMG: https://kpmg.com/vn/vi/insights/2025/11/key-changes-in-vietnamese-accounting-system-for-enterprises.html
- MISA: https://amis.misa.vn/251687/so-sanh-ve-bieu-mau-bao-cao-tai-chinh-giua-thong-tu-99-va-thong-tu-200/
- einvoice: https://einvoice.vn/tin-tuc/bieu-mau-bctc-theo-tt-99
- ketoanthienung: https://ketoanthienung.net/mau-bao-cao-ket-qua-hoat-dong-kinh-doanh-nam-theo-thong-tu-99.htm
- luatvietnam (TT43): https://luatvietnam.vn/tai-chinh/thong-tu-43-2026-tt-btc-sua-doi-bao-cao-tai-chinh-hop-nhat-hieu-luc-20-04-2026-432924-d1.html
- Mẫu TT200: https://luatvietnam.vn/pldn/bieu-mau-cty-cp/bao-cao-ket-qua-hoat-dong-kinh-doanh-trong-cong-ty-co-phan-1744-51368-forms.html

Còn chưa kiểm chứng:
- **[chưa kiểm chứng]** Mã 20 (lưu chuyển tiền thuần từ HĐKD) và mã 21 (chi mua sắm TSCĐ) trên B03-DN có giữ nguyên theo TT99 hay không.
- **[chưa kiểm chứng]** Mã 61/62 trên TT202 mới chỉ xác nhận qua trích đoạn kết quả tìm kiếm.

⚠ **Hệ quả:** quý 1/2026 trở đi dùng mẫu mới, nên ETL phải chọn bảng ánh xạ theo **năm tài chính + loại báo cáo**. Với báo cáo hợp nhất Q1/2026 (công bố quanh thời điểm TT43 ban hành), cần nhận diện mẫu theo nhãn dòng.

### 7.2. Ngân hàng (tổ chức tín dụng)

**Văn bản điều chỉnh:** QĐ16/2007/QĐ-NHNN, sửa đổi bởi TT49/2014, TT22/2017, TT27/2021 (hiệu lực 01/04/2022). Chưa tìm thấy văn bản sửa đổi nào trong 2024–2026 **[chưa kiểm chứng]**.

**Số hiệu mẫu:** B02/TCTD là **bảng cân đối**, **B03/TCTD là báo cáo kết quả hoạt động**, B04 là lưu chuyển tiền tệ. Mẫu không có cột mã số, chỉ đánh số thứ tự.

**Các dòng trên B03/TCTD:**
- 1 Thu nhập lãi và các khoản tương tự; 2 Chi phí lãi; **I Thu nhập lãi thuần**
- **II** dịch vụ; **III** ngoại hối; **IV** chứng khoán kinh doanh; **V** chứng khoán đầu tư; **VI** hoạt động khác; **VII** góp vốn, mua cổ phần
- **VIII** chi phí hoạt động; **IX** LN thuần trước dự phòng; **X** chi phí dự phòng rủi ro tín dụng; **XI** LNTT
- **XII** thuế; **XIII** LNST; **XIV** lợi ích CĐ không kiểm soát; **XV** lãi cơ bản trên cổ phiếu

**Không có** "Doanh thu thuần" và **không có** "Tổng thu nhập hoạt động". TOI = I + … + VII là chỉ tiêu do người phân tích tính. Đây là căn cứ của quy tắc R9.

Nguồn:
- TT49: https://caselaw.vn/van-ban-phap-luat/264126-thong-tu-49-2014-tt-nhnn-sua-doi-che-do-bao-cao-tai-chinh-doi-voi-to-chuc-tin-dung-kem-theo-quyet-dinh-16-2007-qd-nhnn-va-he-thong-tai-khoan-ke-toan-cac-to-chuc-tin-dung-kem-theo-quyet-dinh-479-2004-qd-nhnn-do-thong-doc-ngan-hang-nha-nuoc-ban-hanh
- TT27/2021: https://caselaw.vn/van-ban-phap-luat/401811-thong-tu-so-27-2021-tt-nhnn-ngay-31-12-2021-cua-thong-doc-ngan-hang-nha-nuoc-viet-nam-sua-doi-he-thong-tai-khoan-ke-toan-cac-to-chuc-tin-dung-kem-theo-quyet-dinh-479-2004-qd-nhnn-va-che-do-bao-cao-tai-chinh-doi-voi-cac-to-chuc-tin-dung-kem-theo-quyet-dinh-16-2007-qd-nhnn

### 7.3. Thời hạn công bố thông tin (căn cứ quy tắc `as_of_date`)

Theo TT96/2020/TT-BTC, hợp nhất tại VBHN 10/VBHN-BTC ngày 20/04/2026. Các sửa đổi TT68/2024, TT18/2025, TT08/2026 không đổi thời hạn. Nguồn: https://luatvietnam.vn/chung-khoan/van-ban-hop-nhat-10-vbhn-btc-2026-huong-dan-cong-bo-thong-tin-thi-truong-chung-khoan-432898-d5.html

| Báo cáo | BCTC riêng | Công ty mẹ / hợp nhất |
|---|---|---|
| Quý | ≤ 20 ngày sau cuối quý | ≤ 30 ngày |
| Bán niên (soát xét) | ≤ 45 ngày | ≤ 60 ngày |
| Năm (kiểm toán) | ≤ 90 ngày | ≤ 90 ngày |

Đang có dự thảo thay thế TT96 (tin ngày 22/10/2026, đề xuất hạn 120 ngày cho báo cáo năm), **chưa ban hành**: https://lsvn.vn/huong-dan-cong-bo-thong-tin-tren-thi-truong-chung-khoan-a180456.html

## 8. Quy ước ROE ở các nhà cung cấp dữ liệu

| Nguồn | Tử số | Mẫu số | Ghi chú |
|---|---|---|---|
| Vietstock (Hướng dẫn sử dụng 2025, tr. 58–64) | LNST cổ đông công ty mẹ | bình quân đầu–cuối kỳ của (VCSH − lợi ích CĐ không kiểm soát); ngân hàng: (Vốn và các quỹ − lợi ích CĐ không kiểm soát) | https://static1.vietstock.vn/vietstock/2025/VSTF_Huong_dan_su_dung_2025.pdf |
| Simplize | LNST (không nói rõ có phải của cổ đông mẹ không) | (VCSH đầu + VCSH cuối) / 2 | Nêu rằng một số nơi dùng VCSH cuối kỳ là sai. https://simplize.vn/learn/roe |
| YCharts (quốc tế) | LNST 12 tháng gần nhất | VCSH bình quân 5 quý | https://ycharts.com/glossary/terms/return_on_equity |
| CafeF, FireAnt, SSI iBoard, VNDIRECT | **[chưa kiểm chứng]** | | FireAnt ghi "4 quý gần nhất" nhưng không công bố công thức |

**Kết luận:** các nguồn **dùng quy ước khác nhau**. Dự án chọn quy ước giống Vietstock làm mặc định (R5) và cung cấp tùy chọn bình quân 5 điểm. Vì vậy TV4 tuyệt đối **không lấy ROE của nhà cung cấp làm Gold**.

## 9. Khoảng trống nghiên cứu: vị trí của dự án

1. **Kiểu đầu vào.** Benchmark tiếng Việt hiện có (ViNumQA, ViFinQA) đều dựa trên văn bản hoặc đoạn bảng. Chưa có công trình nào đánh giá hỏi đáp trên **CSDL cấu trúc nhiều kỳ** của BCTC quý VN30. FinStat2SQL gần nhất nhưng chỉ thử một kiến trúc (Text-to-SQL).
2. **So sánh kiến trúc có kiểm soát.** Chưa có benchmark tài chính nào so sánh trên **cùng bộ câu hỏi** các kiến trúc: code tự do (A), thư viện chỉ số (B), JSON DSL giới hạn (C), SQL (D) và baseline quy tắc (B0).
3. **Ngữ nghĩa kỳ và chỉ số.** Các cặp đối lập chưa được kiểm tra một cách hệ thống: Q3 vs 9 tháng, % vs điểm %, ROE khi vốn chủ âm, rỗng hợp lệ vs thiếu dữ liệu. Đây là chính những lỗi dễ thành **sai âm thầm** nhất.
4. **Cách báo cáo kết quả.** Công trình trước báo cáo EA/PA hoặc một con số accuracy duy nhất. Dự án tách 4 đại lượng (A/N, W/A, (A−W)/N, lỗi âm thầm), áp dụng tinh thần selective QA và quan sát "báo lỗi to vs sai hợp lý" của dbt 2026 vào tài chính tiếng Việt.
5. **Mơ hồ và độ chặt chẽ.** Các benchmark về hỏi làm rõ đều là tiếng Anh, miền chung. Dự án bổ sung mơ hồ đặc thù tài chính Việt Nam ("doanh thu ngân hàng", "lợi nhuận", "nợ"), Gold độc lập và bootstrap theo họ câu.

## 10. Hàm ý cho từng thành viên

- **TV1:**
  - chọn bảng ánh xạ theo năm tài chính + loại báo cáo (mục 7.1);
  - tính TOI ngân hàng và ghi `derived_from`;
  - ghi `as_of_date` thực tế, hoặc ước lượng theo mục 7.3 kèm cờ;
  - lưu số Q4 bị BCTC kiểm toán điều chỉnh thành phiên bản mới.
- **TV2:** cập nhật `template_refs` trong `catalog.py` khi TV1 chốt bảng ánh xạ. Giữ R9 cho ngân hàng.
- **TV3:**
  - phương pháp A chỉ nhận mô tả công thức bằng văn bản, lấy từ đặc tả 4.3–4.4;
  - output contract nên dùng chung khóa với `MetricResult.to_dict()`.
- **TV4:**
  - ViFinQA không có Gold, nên chỉ đối chiếu được theo kiểu câu hỏi;
  - bổ sung FinStat2SQL vào báo cáo đối chiếu;
  - không dùng ROE của nhà cung cấp làm Gold.
- **TV5:** bootstrap theo cụm/họ câu (Miller 2024); tham khảo cách FinanceBench và TrustSQL tách "sai" với "từ chối".
