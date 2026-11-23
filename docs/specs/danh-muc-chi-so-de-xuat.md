# Danh mục 14 chỉ số chính thức đề xuất cho Giai đoạn 2

| | |
|---|---|
| **Phiên bản** | v0.1 — đề xuất của TV2, chờ chốt tại Cổng Giai đoạn 1 |
| **Căn cứ chọn** | Cấu trúc chuẩn BCTC Việt Nam (phi tài chính và ngân hàng), các cặp đối lập bắt buộc của Benchmark (mục 8.3 Đề cương) và đối chiếu công trình liên quan ([tổng quan tài liệu](../research/tong-quan-tai-lieu.md)). Không dùng khảo sát (kehoach.md, mục 0.1) |
| **Quy tắc tính** | Theo [đặc tả 4.3–4.4](dac-ta-quy-tac-so-lieu-va-thoi-gian.md) |

Chỉ số được tách thành 3 lớp:
- **Lớp 1 — trường gốc:** đọc thẳng từ một dòng trên BCTC (hoặc một phép cộng trừ dòng được ghi `derived_from`).
- **Lớp 2 — chỉ số suy ra:** công thức trên các trường gốc.
- **Lớp 3 — phép biến đổi:** áp lên lớp 1 hoặc lớp 2 (quý, lũy kế, TTM, YoY, QoQ, chênh lệch điểm %, xếp hạng, lọc). Lớp 3 không tính vào 14 chỉ số.

Ký hiệu: **PTC** = phi tài chính, **NH** = ngân hàng, ✅ = đã cài trong bản pilot.

---

## 1. Lớp 1 — Trường gốc (9)

Mã số theo mẫu biểu **thay đổi từ năm tài chính 2026**. TV1 chọn bảng ánh xạ theo năm tài chính và loại báo cáo, thư viện chỉ dùng mã chuẩn hóa nội bộ.

| # | `metric` / `item_code` | Tên | Nhóm | Loại | Doanh nghiệp, FY ≤ 2025 (TT200; hợp nhất TT202) | Doanh nghiệp, FY ≥ 2026 (TT99; hợp nhất TT202 sửa bởi TT43) | Ngân hàng (QĐ16/2007 sửa bởi TT49/2014, TT27/2021) |
|---|---|---|---|---|---|---|---|
| 1 | `net_revenue` / `IS.NET_REVENUE` ✅ | Doanh thu thuần | PTC | flow | B02 mã **10** | mã **10** (không đổi) | **Không có**, xử lý theo R9 |
| 2 | `gross_profit` / `IS.GROSS_PROFIT` | Lợi nhuận gộp | PTC | flow | B02 mã **20** | mã **20** | Không áp dụng |
| 3 | `npat` / `IS.NPAT` | LNST (toàn bộ) | cả 2 | flow | B02 mã **60** | mã **60** | B03 mục **XIII** |
| 4 | `npat_parent` / `IS.NPAT_PARENT` ✅ | LNST cổ đông công ty mẹ | cả 2 | flow | B02-HN mã **61**; BCTC riêng = mã 60 | mã **61** (không đổi) | **XIII − XIV** (suy ra) |
| 5 | `total_assets` / `BS.TOTAL_ASSETS` | Tổng tài sản | cả 2 | stock | B01 mã **270** | mã **280** ⚠ (270 nay là "Tài sản dài hạn khác") | B02/TCTD dòng Tổng tài sản |
| 6 | `total_liabilities` / `BS.TOTAL_LIABILITIES` | Nợ phải trả | PTC | stock | B01 mã **300** | mã **300** | (không dùng ở GĐ2) |
| 7 | `equity_parent` / `BS.EQUITY_PARENT` ✅ | VCSH cổ đông công ty mẹ | cả 2 | stock | mã **400 − 429** (429 chỉ có trên HN) | **400 − 429** | VCSH − lợi ích CĐ không kiểm soát |
| 8 | `bank_nii` / `IS.BANK_NII` ✅ | Thu nhập lãi thuần | NH | flow | — | — | B03 mục **I** |
| 9 | `bank_toi` / `IS.BANK_TOI` ✅ | Tổng thu nhập hoạt động | NH | flow | — | — | **I + II + … + VII** (= IX + VIII). Không có dòng riêng, TV1 tính và ghi `derived_from` |

**Trường hỗ trợ.** Hai trường sau không tính vào 14 chỉ số nhưng được cài để phục vụ công thức và lựa chọn làm rõ:
- `bank_interest_income` ✅: B03 dòng 1, "Thu nhập lãi và các khoản thu nhập tương tự".
- `BS.EQUITY_TOTAL` (mã 400) và `BS.NCI` (mã 429).

## 2. Lớp 2 — Chỉ số suy ra (5)

| # | `metric` | Công thức | Nhóm | Đơn vị | Ghi chú quy ước |
|---|---|---|---|---|---|
| 10 | `gross_margin` | LN gộp / Doanh thu thuần (cùng quý) | PTC | ratio | Doanh thu ≤ 0 hoặc gần 0 → không xác định (R1–R2). NH → không áp dụng (R10) |
| 11 | `net_margin` | LNST **toàn bộ** (60) / Doanh thu thuần | PTC | ratio | Dùng mã 60, không dùng mã 61, vì doanh thu hợp nhất gồm 100% công ty con |
| 12 | `roe_ttm` ✅ | Σ LNST cổ đông mẹ 4 quý / VCSH cổ đông mẹ bình quân | cả 2 | ratio | R4–R7. Mặc định bình quân 2 điểm, tùy chọn 5 điểm |
| 13 | `roa_ttm` | Σ LNST **toàn bộ** 4 quý / Tổng tài sản bình quân | cả 2 | ratio | Tổng tài sản hợp nhất gồm phần của CĐ không kiểm soát nên tử số dùng mã 60. Bình quân theo cùng quy ước R5 |
| 14 | `liabilities_to_equity` | Nợ phải trả (300) / VCSH (400) | PTC | lần | VCSH ≤ 0 → không xác định (R4). **Không** gọi là "nợ vay/VCSH" (xem mục 4) |

**Dự phòng** (chỉ thêm nếu ngân hàng được giữ trong mẫu chính và GĐ2 còn thời gian):
- `bank_cir` = Chi phí hoạt động (B03 mục VIII) / TOI;
- `bank_provision` = Chi phí dự phòng rủi ro tín dụng (mục X);
- `cfo` = Lưu chuyển tiền thuần từ HĐKD (B03-DN mã 20);
- `eps_ttm`.

Theo quy tắc cắt giảm (kehoach.md, mục 4.2), khi thiếu thời gian thì bỏ nhóm dự phòng trước, rồi tới các chỉ số chỉ dành cho ngân hàng.

## 3. Lớp 3 — Phép biến đổi

| Phép | Ký hiệu | Áp dụng cho | Kết quả | Trạng thái |
|---|---|---|---|---|
| Quý đơn lẻ | `Q` | flow, stock (số cuối quý) | giá trị | ✅ |
| Lũy kế từ đầu năm | `ytd` | flow | giá trị | GĐ2 |
| 4 quý gần nhất | `ttm` | flow | giá trị | ✅ (trong ROE) |
| Tăng trưởng cùng kỳ | `yoy` | chỉ số tiền tệ (VND) | **% tương đối** (`ratio`) | ✅ |
| Tăng trưởng quý liền trước | `qoq` | chỉ số tiền tệ | % tương đối | GĐ2 |
| Chênh lệch điểm % | `yoy_pp`, `qoq_pp` | chỉ số tỷ lệ (lớp 2) | **điểm %** (`pp`) | GĐ2 |
| Xếp hạng / top-N | `rank` | mọi chỉ số, nhiều mã, **cùng kỳ** (T5) | danh sách có thứ tự; mã không xác định bị loại và được liệt kê | GĐ2 |
| Lọc ngưỡng | `screen` | mọi chỉ số, nhiều mã | danh sách; phân biệt 0 dòng hợp lệ và thiếu dữ liệu (R8) | ✅ |

Ràng buộc kiểu:
- `yoy` / `qoq` **không** áp dụng cho chỉ số tỷ lệ. "ROE tăng bao nhiêu" phải đi qua `yoy_pp`, hoặc hỏi làm rõ "% hay điểm %". Đây là cặp đối lập "% YoY vs điểm %".
- `ttm` không áp dụng cho stock. Với stock chỉ có số cuối kỳ hoặc bình quân.

## 4. Các cách hiểu mơ hồ thường gặp

Thư viện tính được **mọi** cách hiểu dưới đây. Việc chọn mặc định công khai hay hỏi lại 1 lượt thuộc lớp hiểu câu (B0/LLM) và được đánh giá theo RQ3 điều chỉnh (kehoach.md, mục 0.3). Cột "Đề xuất mặc định" chỉ để TV4 gắn nhãn loại mơ hồ.

| Cụm từ trong câu hỏi | Các cách hiểu (chỉ số trong danh mục) | Đề xuất mặc định |
|---|---|---|
| "doanh thu" (PTC) | `net_revenue` (mã 10) · doanh thu bán hàng gộp (mã 01, ngoài danh mục) | `net_revenue`, kèm hiển thị giả định |
| "doanh thu" (NH) | `bank_nii` · `bank_toi` · `bank_interest_income` | **Luôn hỏi làm rõ** (R9) |
| "lợi nhuận", "lãi" | `npat_parent` · `npat` · LNTT (mã 50) · `gross_profit` | `npat_parent`, kèm hiển thị giả định |
| "biên lợi nhuận" | `gross_margin` · `net_margin` | Hỏi làm rõ |
| "nợ", "đòn bẩy" | `liabilities_to_equity` (nợ phải trả) · nợ vay/VCSH (ngoài danh mục) | Trả nợ phải trả/VCSH và **ghi rõ không phải nợ vay** |
| "ROE" không nêu kỳ | `roe_ttm` tại kỳ gần nhất (T4) | `roe_ttm` |
| "ROE năm 2024" | `roe_ttm` tại Q4/2024 (= ROE năm với bình quân đầu/cuối năm) | `roe_ttm` @ Q4/2024 |
| "quý 3" vs "9 tháng" | `Q` vs `ytd` | Theo từ khóa, không mơ hồ |
| "tăng trưởng" không nêu gốc | `yoy` · `qoq` | `yoy` (thông lệ BCTC quý VN, vì mẫu B02a-DN so với cùng kỳ năm trước) |
| "ROE tăng bao nhiêu %" | `yoy_pp` (điểm %) · % tương đối của ROE | Hỏi làm rõ, hoặc mặc định điểm % kèm ghi chú |

## 5. Lý do chọn 14 chỉ số

1. **Phủ đủ các cặp đối lập bắt buộc** (kehoach.md, mục 3.1, TV4):
   - Q3 vs 9M: `net_revenue` + `ytd`;
   - % YoY vs điểm %: `net_margin` + `yoy` / `yoy_pp`;
   - top tuyệt đối vs tốc độ tăng: `net_revenue` + `rank` trên giá trị hoặc trên `yoy`;
   - rỗng hợp lệ vs thiếu mẫu số: `screen`;
   - ROE vốn chủ âm vs dương: `roe_ttm`.
2. **Mỗi chỉ số đều tính tay được từ thân BCTC** (không cần thuyết minh), để TV4 dựng Gold độc lập và TV5 kiểm toán 100 giá trị theo 4 trục (BS/IS/CF, quý/YTD, gốc/dẫn xuất).
3. **Có cả hai nhóm doanh nghiệp nhưng không cần bộ quy tắc riêng cho ngân hàng**:
   - 4 chỉ số dùng chung (`npat`, `npat_parent`, `total_assets`/`roa_ttm`, `roe_ttm`);
   - 2 trường riêng của ngân hàng (NII, TOI).
   Chỉ số ngân hàng phụ thuộc thuyết minh (NIM, nợ xấu, LDR theo quy định) được **loại** khỏi GĐ2 vì cần dữ liệu ngoài thân báo cáo và quy tắc riêng.
4. **Tránh chỉ số dễ gây tranh cãi về công thức** (EBITDA, FCF, NIM). Không có định nghĩa chuẩn trên mẫu biểu, nên Gold khó độc lập.
