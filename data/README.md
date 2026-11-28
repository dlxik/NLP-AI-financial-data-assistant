# data/ (TV1)

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `raw/` | BCTC gốc (PDF), dữ liệu tải từ nguồn cấu trúc | ❌ (bản quyền, dung lượng) |
| `pilot/` | Snapshot pilot 5 mã (GĐ1) | ❌ |
| `snapshots/` | Snapshot v1.0 đã khóa: `fact_financials` (long) + bảng wide + metadata + hash | ❌ chỉ commit **manifest/hash** nếu cần |

- Schema ETL pilot của TV1: [đặc tả `fact_financials`](../docs/data/tv1_fact_financials_schema.md).
- Hợp đồng đầu vào Semantic Layer của TV2: [đặc tả số liệu và thời gian](../docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md), mục 2.
- Hai schema hiện chưa khớp; xem [báo cáo tích hợp](../docs/reports/integration-review.md) trước khi đưa Snapshot vào `FactStore`.
