"""B0 dùng chung bộ dữ liệu giả lập với semantic layer."""

import pytest

from fin_assistant.b0 import B0System
from tests.semantic.conftest import facts_df, store  # noqa: F401  (re-export fixture)

QDATE = "2025-02-15"  # ngày hỏi mặc định: AAA đã có Q4/2024, NHA mới có Q3/2024


@pytest.fixture(scope="session")
def b0(store):  # noqa: F811
    return B0System(store)


@pytest.fixture(scope="session")
def b0_clarify(store):  # noqa: F811
    return B0System(store, policy="clarify")
