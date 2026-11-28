# Quy trình kiểm toán phân tầng 100 giá trị — TV5

Tài liệu này chuẩn bị đầu ra Giai đoạn 1 để áp dụng khi TV1 bàn giao Snapshot ở Giai đoạn 2.

## Mục tiêu

Lấy đúng 100 giá trị từ Snapshot và đối chiếu độc lập với báo cáo tài chính gốc. Mẫu phải
phủ bốn trục: ngành, loại báo cáo, kỳ và loại giá trị.

## Phân bổ tối thiểu

| Trục | Tầng | Số mẫu tối thiểu |
|---|---|---:|
| Ngành | Phi tài chính | 50 |
| Ngành | Ngân hàng | 30 |
| Dự phòng | Phân bổ theo tỷ trọng Snapshot sau khi chốt | 20 |
| Báo cáo | BS | 25 |
| Báo cáo | IS | 35 |
| Báo cáo | CF | 20 |
| Báo cáo | Phân bổ bổ sung | 20 |
| Kỳ | Quý riêng | 40 |
| Kỳ | YTD/FY | 30 |
| Kỳ | Bán niên/kiểm toán hoặc phiên bản lại | 15 |
| Kỳ | Phân bổ bổ sung | 15 |
| Giá trị | Lấy trực tiếp | 70 |
| Giá trị | Dẫn xuất, gồm YTD→Q | 30 |

Các quota giao nhau, không cộng từng bảng thành tổng riêng. Dùng seed cố định và lưu danh
sách toàn bộ population trước khi lấy mẫu để có thể tái lập.

## Các bước

1. Nhận Snapshot đã gắn `fact_id`, `source_report_id`, `source_ref`, `as_of_date` và
   `derived_from`.
2. Loại các dòng không có tài liệu nguồn; ghi thành lỗi dữ liệu, không âm thầm bỏ qua.
3. Gán mỗi dòng vào các tầng, sau đó lấy mẫu bằng seed được ghi trong biên bản.
4. Người kiểm toán mở PDF gốc, không dùng code ETL/semantic để xác nhận giá trị.
5. Với giá trị dẫn xuất, kiểm tra từng đầu vào và tự tính lại công thức.
6. Ghi sai lệch tuyệt đối, tương đối, loại lỗi và bằng chứng vào biểu mẫu.
7. Nếu phát hiện lỗi hệ thống trong một tầng, mở rộng kiểm tra tầng đó; không thay các mẫu
   lỗi bằng mẫu khác.

## Phân loại lỗi

- `source_mismatch`: sai ô hoặc sai báo cáo nguồn.
- `period_mismatch`: nhầm quý, YTD hoặc năm.
- `unit_mismatch`: sai đơn vị/quy đổi.
- `scope_mismatch`: nhầm hợp nhất và công ty mẹ.
- `version_mismatch`: chọn sai phiên bản báo cáo theo `as_of_date`.
- `derivation_error`: sai phép YTD→Q hoặc công thức dẫn xuất.
- `traceability_missing`: không thể lần ngược nguồn.

Mẫu biểu: `evaluation/templates/audit_100_template.csv`.
