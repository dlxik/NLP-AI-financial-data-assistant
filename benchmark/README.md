# benchmark/ (TV4 — Benchmark Lead & Test Keeper)

| Thư mục | Nội dung | Ai được xem |
|---|---|---|
| `dev/` | Tập Dev: câu hỏi, `question_date`, nhãn hành động kỳ vọng, họ câu | Cả nhóm |
| *(ngoài repo)* | **Tập Test chính + Gold Test** | **Chỉ TV4/TV5**. Bị chặn trong `.gitignore`, không được đẩy lên repo |

## Nguyên tắc độc lập (kehoach.md, mục 1)
- Gold được tính **tay từ BCTC gốc**, ghi nguồn ô số và công thức. **Không chạy code của `src/fin_assistant/semantic/`.**
- Tách Dev và Test theo **họ câu**, để không rò rỉ biến thể diễn đạt.
- Quy ước tính (ROE, kỳ gần nhất, 0 dòng…) lấy từ [đặc tả 4.3–4.4](../docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md), không lấy từ code.

## Trạng thái pilot Giai đoạn 1

[Bộ 30 câu pilot](phase1/README.md) đang công khai để nhóm kiểm tra. Gold do trợ lý hỗ trợ chép/tính và Hiền duyệt kết quả kiểm chứng của trợ lý; chưa ghi nhận Hiền tự tính lại hoặc TV5 kiểm tra độc lập. Quy ước ROE và bộ 5 mã pilot chưa thống nhất với TV1/TV2; xem [báo cáo tích hợp](../docs/reports/integration-review.md).
