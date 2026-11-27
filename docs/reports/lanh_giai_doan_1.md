# Tổng kết tiến độ Giai đoạn 1 — Thành viên TV3 (Lanh)

- **Vai trò:** TV3 — LLM Pipeline, Sandbox & Demo Engineer ([`kehoach.md`](../../kehoach.md))
- **Nhánh Git:** `lanh` (tách từ `main`)
- **Phạm vi:** Giai đoạn 1 — Khởi tạo, Pilot & Khóa bộ chấm (Tuần 1–3)

---

## 1. Các đầu việc đã làm xong (độc lập trong Giai đoạn 1)

1. **Khung cấu hình LLM thử nghiệm (đóng băng tham số tái lập):**
   - Tạo [`configs/llm.pilot.json`](../../configs/llm.pilot.json) với các tham số chuẩn (`temperature = 0.0`, `seed = 42`, `max_tokens = 1024`, `timeout_sec = 30.0`, `max_retries = 2`, `log_format = "jsonl"`).
   - Tạo [`src/fin_assistant/pipelines/config.py`](../../src/fin_assistant/pipelines/config.py) (`LLMConfig`, `load_llm_config`) kiểm tra tham số hợp lệ và chặn lưu trực tiếp API key/secret trong file config (đọc qua `.env` / biến môi trường).

2. **Đặc tả Output Contract v0.1 & Bộ kiểm tra hợp lệ:**
   - Viết tài liệu đặc tả [`docs/specs/output-contract.md`](../specs/output-contract.md).
   - Cài đặt [`src/fin_assistant/pipelines/contract.py`](../../src/fin_assistant/pipelines/contract.py) với 6 trạng thái (`ok`, `empty_valid`, `missing_data`, `not_meaningful`, `needs_clarification`, `not_applicable`) và 16 mã `WarnCode` đồng bộ với `src/fin_assistant/semantic/result.py` của TV2 (trên `origin/cuc`).
   - Cài đặt `validate_output_contract` kiểm tra ràng buộc `status`–`value`–`rows`–`candidates` và từ chối cảnh báo chung chung thiếu `ticker`, `period`, hoặc `item_code`.
   - Bổ sung `PipelineOutput.from_metric_dict` và `PipelineOutput.from_multi_dict` để chuyển đổi trực tiếp kết quả từ thư viện của TV2.

3. **Sandbox v0.1 thực thi cô lập mức cơ bản:**
   - Cài đặt [`src/fin_assistant/pipelines/sandbox.py`](../../src/fin_assistant/pipelines/sandbox.py) (`SandboxExecutor`, `SandboxConfig`, `SandboxResult`) gồm các lớp bảo vệ:
     - Kiểm tra tĩnh AST (`validate_code_ast`): allowlist module cho phép (`pandas`, `numpy`, `math`, ...), chặn import/built-in/dunder nguy hiểm (`os`, `subprocess`, `socket`, `eval`, `exec`, `open`, `__subclasses__`...).
     - Tách tiến trình con (`python -I`), thư mục làm việc tạm tự dọn, biến môi trường tối giản (loại bỏ API key và giới hạn luồng OpenBLAS/OMP).
     - Khóa mạng (`socket`, `urllib.request`) và khóa ghi tập tin; chỉ cho phép đọc trong `allowed_read_dirs`.
     - Giới hạn timeout (dừng cả cây tiến trình khi quá hạn), giới hạn RAM/CPU (Windows Job Object trên Windows / `resource.setrlimit` trên POSIX).

4. **Pipeline Runner & Chuẩn hóa Logging JSONL:**
   - Tạo [`src/fin_assistant/pipelines/logging.py`](../../src/fin_assistant/pipelines/logging.py) (`RunLogger`, `RunLogRecord`) ghi log JSONL (`run_id`, `question_id`, `question_date`, `model`, `model_version`, `temperature`, `seed`, `num_llm_calls`, `latency_ms`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `parse_status`, `contract_valid`, `sandbox_status`).
   - Tạo [`src/fin_assistant/pipelines/llm_client.py`](../../src/fin_assistant/pipelines/llm_client.py) (`MockLLMClient` chạy offline xác định và `OpenAICompatibleClient` gọi HTTP API thật qua biến môi trường).
   - Tạo [`src/fin_assistant/pipelines/runner.py`](../../src/fin_assistant/pipelines/runner.py) (`PilotPipelineRunner`) và script [`scripts/run_tv3_pilot_check.py`](../../scripts/run_tv3_pilot_check.py) để chạy batch nhiều lần đo độ ổn định định dạng.

5. **Kiểm thử tự động & Chạy thử nghiệm trên tập ví dụ tự tạo:**
   - Viết 4 tệp unit test trong [`tests/pipelines/`](../../tests/pipelines/): `test_config_and_logging.py` (4 tests), `test_contract.py` (6 tests), `test_sandbox.py` (8 tests), `test_pilot_runner.py` (1 test batch 15 lượt).
   - Kết quả chạy thực tế sau chỉnh sửa cuối:
     - `python -m pytest -v`: **19/19 passed** (1 warning từ plugin `anyio` của môi trường).
     - `python scripts/run_tv3_pilot_check.py --log runs/tv3_pilot_check.jsonl` (với `MockLLMClient`, 5 ví dụ × 3 lần lặp): **15/15 lượt hợp lệ** (`format_stability_rate = 1.0`, `consistent_across_repeats = true`, `parse_ok_rate = 1.0`, `contract_valid_rate = 1.0`).

---

## 2. Các phần chưa làm xong (cần tài liệu / quyết định từ các thành viên khác)

| Hạng mục còn thiếu / chờ | Phụ thuộc vào ai | Chi tiết cần chốt |
|---|---|---|
| **Chốt model/provider LLM thật & chạy đo ổn định với API thật** | **Cả nhóm** (đặc biệt TV2, TV4, TV5) | [`configs/llm.pilot.json`](../../configs/llm.pilot.json) hiện mới để `provider = "mock"`, `model = "TBD_TEAM_LOCK"`, `api_version = "TBD_TEAM_LOCK"`. Cần nhóm thống nhất provider/model, phiên bản API và API key (`.env`) để chạy `scripts/run_tv3_pilot_check.py --live` đo độ ổn định định dạng thực tế trên LLM thật thay vì `MockLLMClient`. |
| **Chốt chính thức Output Contract với Bộ chấm v1** | **TV5** (Evaluation & QA) | Repo hiện chưa có mã nguồn Bộ chấm v1 của TV5. Cần TV5 đối chiếu [`docs/specs/output-contract.md`](../specs/output-contract.md) (đặc biệt mục 5: cách chấm bảng nhiều mã, đơn vị `ratio` vs `%`, và quy ước lỗi parse/sandbox) để khớp 100% trước buổi kiểm duyệt & "Tấn công bộ chấm" cuối GĐ1. |
| **Đồng bộ cấu trúc nhánh với TV2 & đối chiếu Đề cương v3** | **TV2** (`origin/cuc`) & **Cả nhóm** | Nhánh `lanh` tách từ `main` nên chưa merge code của TV2 (`src/fin_assistant/semantic/`, đặc tả 4.3–4.4, danh mục chỉ số đề xuất). Ngoài ra repo chưa có file `AI_Financial_Data_Assistant_Proposal_v3.md` để đối chiếu chi tiết các mục tham chiếu trong `kehoach.md`. |
| **Chuẩn bị đầu vào chuyển tiếp sang GĐ2 (chưa chặn GĐ1)** | **TV1** & **TV2** | GĐ1 TV3 chỉ dùng ví dụ tự tạo nên không bị chặn; tuy nhiên ngay sau Cổng GĐ1 (để làm Phương pháp A & B ở GĐ2) sẽ cần **schema bảng wide & Snapshot dữ liệu từ TV1** cùng **bộ chỉ số 10–15 hàm + `RuleConfig` đã đóng băng từ TV2**. |
