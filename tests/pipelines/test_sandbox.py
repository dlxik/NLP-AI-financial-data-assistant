"""Kiểm thử khả năng cô lập và bảo mật của Sandbox v0.1."""

from __future__ import annotations

from pathlib import Path

from fin_assistant.pipelines.sandbox import SandboxConfig, SandboxExecutor


def test_sandbox_executes_valid_pandas_computation() -> None:
    executor = SandboxExecutor(SandboxConfig(timeout_sec=10.0))
    code = """
import pandas as pd
df = pd.DataFrame([
    {"ticker": "VNM", "period": "2023Q4", "rev": 100.0},
    {"ticker": "VNM", "period": "2024Q4", "rev": 125.0},
])
r23 = df.loc[df["period"] == "2023Q4", "rev"].iloc[0]
r24 = df.loc[df["period"] == "2024Q4", "rev"].iloc[0]
result = {"value": (r24 - r23) / r23, "unit": "ratio"}
"""
    res = executor.execute(code)
    assert res.ok is True
    assert res.result == {"value": 0.25, "unit": "ratio"}


def test_sandbox_allows_reading_inside_allowed_dir(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    csv_path = allowed_dir / "sample.csv"
    csv_path.write_text("ticker,value\nFPT,150\nVNM,200\n", encoding="utf-8")

    executor = SandboxExecutor(
        SandboxConfig(timeout_sec=10.0, allowed_read_dirs=(str(allowed_dir),))
    )
    code = """
import pandas as pd
df = pd.read_csv(csv_file)
result = float(df["value"].sum())
"""
    res = executor.execute(code, context={"csv_file": str(csv_path)})
    assert res.ok is True
    assert res.result == 350.0


def test_sandbox_blocks_reading_outside_allowed_dir(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    secret_file = tmp_path / "secret.csv"
    secret_file.write_text("secret\n123\n", encoding="utf-8")

    executor = SandboxExecutor(
        SandboxConfig(timeout_sec=10.0, allowed_read_dirs=(str(allowed_dir),))
    )
    code = """
import pandas as pd
df = pd.read_csv(secret_path)
result = len(df)
"""
    res = executor.execute(code, context={"secret_path": str(secret_file)})
    assert res.ok is False
    assert res.error_type == "security_violation"


def test_sandbox_blocks_file_write_via_pandas(tmp_path: Path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    target_write = allowed_dir / "pwned.csv"

    executor = SandboxExecutor(
        SandboxConfig(timeout_sec=10.0, allowed_read_dirs=(str(allowed_dir),))
    )
    code = """
import pandas as pd
df = pd.DataFrame([{"a": 1}])
df.to_csv(out_path, index=False)
result = 1
"""
    res = executor.execute(code, context={"out_path": str(target_write)})
    assert res.ok is False
    assert res.error_type == "security_violation"
    assert not target_write.exists()


def test_sandbox_blocks_forbidden_imports_and_builtins() -> None:
    executor = SandboxExecutor()
    for bad_code in (
        "import os\nresult = os.listdir('.')",
        "import subprocess\nresult = 1",
        "import socket\nresult = 1",
        "result = eval('1 + 1')",
        "result = open('secret.txt').read()",
        "result = ().__class__.__base__.__subclasses__()",
    ):
        res = executor.execute(bad_code)
        assert res.ok is False
        assert res.error_type == "security_violation"


def test_sandbox_blocks_runtime_network_access() -> None:
    executor = SandboxExecutor(SandboxConfig(timeout_sec=10.0))
    code = """
import pandas as pd
df = pd.read_csv("https://example.com/data.csv")
result = len(df)
"""
    res = executor.execute(code)
    assert res.ok is False
    assert res.error_type in ("security_violation", "runtime_error")


def test_sandbox_enforces_timeout_on_infinite_loop() -> None:
    executor = SandboxExecutor(SandboxConfig(timeout_sec=1.0, max_cpu_sec=2))
    code = """
x = 0
while True:
    x += 1
result = x
"""
    res = executor.execute(code)
    assert res.ok is False
    assert res.timed_out is True
    assert res.error_type == "timeout"


def test_sandbox_enforces_memory_limit() -> None:
    executor = SandboxExecutor(SandboxConfig(timeout_sec=10.0, max_memory_mb=256))
    code = """
buf = bytearray(350 * 1024 * 1024)
result = len(buf)
"""
    res = executor.execute(code)
    assert res.ok is False
    assert res.error_type in ("memory_limit", "runtime_error")
