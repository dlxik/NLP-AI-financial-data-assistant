"""AI Financial Data Assistant — gói mã nguồn chung của nhóm.

Phân hệ theo vai trò (xem kehoach.md, mục 1):
    etl/         TV1 — nạp dữ liệu, chuẩn hóa fact_financials, Snapshot
    semantic/    TV2 — thư viện chỉ số (semantic layer), B0, C
    pipelines/   TV3 — pipeline LLM (A, B, B1, D), sandbox, demo
    evaluation/  TV5 — bộ chấm 4 đại lượng, thống kê
"""

__version__ = "0.1.0"
