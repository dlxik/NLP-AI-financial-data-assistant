# data/ (TV1)

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `raw/` | BCTC gốc (PDF), dữ liệu tải từ nguồn cấu trúc | ❌ (bản quyền, dung lượng) |
| `pilot/` | Snapshot pilot 5 mã (GĐ1) | ❌ |
| `snapshots/` | Snapshot v1.0 đã khóa: `fact_financials` (long) + bảng wide + metadata + hash | ❌ chỉ commit **manifest/hash** nếu cần |

- Hợp đồng dữ liệu của `fact_financials`: [docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md](../docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md), mục 2.
- Kiểm tra trước khi bàn giao: `fin_assistant.semantic.validate_facts(facts, companies)` phải trả về danh sách rỗng.
