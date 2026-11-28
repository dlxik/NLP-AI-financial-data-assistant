"""TV1 — Data & ETL: nạp BCTC, chuẩn hóa ``fact_financials`` (long format), quy đổi YTD→Q,
quản lý ``as_of_date`` / ``report_version``, đóng gói Snapshot.

Schema pilot ở ``docs/data/tv1_fact_financials_schema.md``. Bộ chuyển đổi sang
``fin_assistant.semantic.FactStore`` cần được chốt cùng TV2 trước khi chạy tích hợp.
"""
