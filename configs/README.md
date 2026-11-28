# configs/

Cấu hình được **đóng băng** cùng Snapshot và các bản build chạy thí nghiệm:

- `rules.*.json`: giá trị `RuleConfig` của semantic layer (ngưỡng mẫu số gần 0, cách tính VCSH bình quân, chính sách kỳ gần nhất đa mã). Bản đề xuất xem mục 8 của [đặc tả 4.3–4.4](../docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md). Nhóm chốt tại Cổng GĐ1.
- `llm.*.json` (TV3): mô hình, phiên bản API, `temperature`, `seed`, định dạng log.

Không đặt khóa API ở đây. Khóa để trong `.env`, file này đã bị chặn commit.
