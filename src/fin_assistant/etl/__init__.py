"""TV1 — Data & ETL: nạp BCTC, chuẩn hóa ``fact_financials`` (long format), quy đổi YTD→Q,
quản lý ``as_of_date`` / ``report_version``, đóng gói Snapshot.

Hợp đồng dữ liệu đầu ra: docs/specs/dac-ta-quy-tac-so-lieu-va-thoi-gian.md, mục 2
(kiểm tra bằng ``fin_assistant.semantic.validate_facts``).
"""
