"""Sandbox v0.1 thực thi cô lập mã Python/Pandas do LLM sinh ra (TV3).

Các lớp bảo vệ mức cơ bản ở Giai đoạn 1:
1. Kiểm tra tĩnh AST trước khi chạy (allowlist module, chặn import/built-in/dunder nguy hiểm).
2. Tách tiến trình con (`subprocess`) với thư mục làm việc tạm cô lập và biến môi trường tối giản.
3. Khóa mạng trong tiến trình thực thi (`socket`, `urllib`).
4. Giới hạn quyền đọc/ghi tập tin: chặn mọi thao tác ghi; chỉ cho phép đọc trong `allowed_read_dirs`.
5. Giới hạn thời gian (kill cả cây tiến trình khi quá hạn), CPU và RAM (Job Object trên Windows /
   `resource.setrlimit` trên POSIX).
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_ALLOWED_MODULES: frozenset[str] = frozenset(
    {
        "pandas",
        "numpy",
        "math",
        "statistics",
        "decimal",
        "datetime",
        "re",
        "json",
        "collections",
        "itertools",
        "functools",
        "operator",
        "typing",
    }
)

DEFAULT_BLOCKED_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "telnetlib",
        "ssl",
        "shutil",
        "pathlib",
        "glob",
        "tempfile",
        "ctypes",
        "cffi",
        "importlib",
        "builtins",
        "multiprocessing",
        "threading",
        "concurrent",
        "asyncio",
        "signal",
        "pty",
        "fcntl",
        "resource",
        "winreg",
        "msvcrt",
        "pickle",
        "marshal",
        "shelve",
        "sqlite3",
        "code",
        "codeop",
        "inspect",
        "gc",
        "traceback",
        "types",
    }
)

DEFAULT_BLOCKED_CALLS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "input",
        "breakpoint",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "memoryview",
    }
)

DEFAULT_BLOCKED_ATTRS: frozenset[str] = frozenset(
    {
        "__subclasses__",
        "__globals__",
        "__builtins__",
        "__code__",
        "__closure__",
        "__mro__",
        "__bases__",
        "__base__",
        "__class__",
        "__dict__",
        "__getattribute__",
        "__import__",
        "__loader__",
        "__spec__",
    }
)


@dataclass(frozen=True)
class SandboxConfig:
    """Cấu hình giới hạn cho Sandbox v0.1."""

    timeout_sec: float = 5.0
    max_memory_mb: int = 1024
    max_cpu_sec: int = 5
    allowed_read_dirs: tuple[str, ...] = ()
    allowed_modules: frozenset[str] = DEFAULT_ALLOWED_MODULES
    blocked_modules: frozenset[str] = DEFAULT_BLOCKED_MODULES
    blocked_calls: frozenset[str] = DEFAULT_BLOCKED_CALLS
    blocked_attrs: frozenset[str] = DEFAULT_BLOCKED_ATTRS
    max_output_bytes: int = 65_536
    result_var: str = "result"


@dataclass(frozen=True)
class SandboxResult:
    """Kết quả thực thi từ Sandbox v0.1."""

    ok: bool
    result: Any = None
    stdout: str = ""
    stderr: str = ""
    error_type: str | None = None
    error_message: str = ""
    elapsed_ms: float = 0.0
    timed_out: bool = False


def validate_code_ast(code: str, config: SandboxConfig) -> str | None:
    """Kiểm tra tĩnh AST của mã người dùng. Trả về lý do lỗi nếu vi phạm, None nếu an toàn."""
    if not isinstance(code, str) or not code.strip():
        return "Empty code snippet"
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod in config.blocked_modules or root_mod not in config.allowed_modules:
                    return f"Import of module '{alias.name}' is not allowed in sandbox"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root_mod = mod.split(".")[0]
            if node.level > 0 or not root_mod:
                return "Relative imports are not allowed in sandbox"
            if root_mod in config.blocked_modules or root_mod not in config.allowed_modules:
                return f"Import from '{mod}' is not allowed in sandbox"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in config.blocked_calls:
                return f"Call to '{node.func.id}()' is not allowed in sandbox"
        elif isinstance(node, ast.Attribute):
            if node.attr in config.blocked_attrs:
                return f"Access to attribute '{node.attr}' is not allowed in sandbox"
        elif isinstance(node, ast.Name):
            if node.id in config.blocked_attrs or node.id == "__builtins__":
                return f"Access to '{node.id}' is not allowed in sandbox"
    return None


def _build_worker_script() -> str:
    """Sinh mã worker chạy trong tiến trình con cô lập."""
    return textwrap.dedent(
        """
        import builtins
        import io
        import json
        import os
        import socket
        import sys
        import urllib.request

        payload_path = sys.argv[1]
        output_path = sys.argv[2]

        with builtins.open(payload_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        for sp in payload.get("site_dirs", []):
            if sp and sp not in sys.path:
                sys.path.append(sp)

        # Nạp trước thư viện được phép trước khi siết open/socket.
        import pandas as pd  # noqa: F401
        import numpy as np  # noqa: F401

        user_code = payload["code"]
        context = payload.get("context", {})
        allowed_dirs = [os.path.realpath(p) for p in payload.get("allowed_read_dirs", [])]
        result_var = payload.get("result_var", "result")
        max_memory_mb = int(payload.get("max_memory_mb", 512))
        max_cpu_sec = int(payload.get("max_cpu_sec", 5))

        # Mở sẵn kênh ghi kết quả trước khi khóa builtins.open.
        result_writer = builtins.open(output_path, "w", encoding="utf-8")

        # Áp giới hạn tài nguyên POSIX nếu khả dụng.
        try:
            import resource
            mem_bytes = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_sec, max_cpu_sec))
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass

        # Khóa mạng ở tầng socket và urllib.
        def _deny_network(*_args, **_kwargs):
            raise PermissionError("Network access is disabled in sandbox")

        socket.socket = _deny_network
        socket.create_connection = _deny_network
        socket.getaddrinfo = _deny_network
        socket.gethostbyname = _deny_network
        urllib.request.urlopen = _deny_network

        # Chỉ cho phép đọc trong allowed_read_dirs; chặn toàn bộ thao tác ghi.
        _orig_open = builtins.open

        def _is_within_allowed(path_obj):
            if isinstance(path_obj, int):
                return False
            try:
                resolved = os.path.realpath(os.fspath(path_obj))
            except Exception:
                return False
            for base in allowed_dirs:
                try:
                    if os.path.commonpath([resolved, base]) == base:
                        return True
                except ValueError:
                    continue
            return False

        def _guarded_open(file, mode="r", *args, **kwargs):
            mode_str = str(mode)
            if any(flag in mode_str for flag in ("w", "a", "x", "+")):
                raise PermissionError(f"Write file access '{mode_str}' is disabled in sandbox")
            if not _is_within_allowed(file):
                raise PermissionError("File access outside allowed_read_dirs is disabled in sandbox")
            return _orig_open(file, mode, *args, **kwargs)

        builtins.open = _guarded_open
        io.open = _guarded_open

        safe_builtins = {
            "abs": builtins.abs,
            "all": builtins.all,
            "any": builtins.any,
            "bool": builtins.bool,
            "dict": builtins.dict,
            "enumerate": builtins.enumerate,
            "filter": builtins.filter,
            "float": builtins.float,
            "frozenset": builtins.frozenset,
            "int": builtins.int,
            "isinstance": builtins.isinstance,
            "len": builtins.len,
            "list": builtins.list,
            "map": builtins.map,
            "max": builtins.max,
            "min": builtins.min,
            "pow": builtins.pow,
            "print": builtins.print,
            "range": builtins.range,
            "reversed": builtins.reversed,
            "round": builtins.round,
            "set": builtins.set,
            "slice": builtins.slice,
            "sorted": builtins.sorted,
            "str": builtins.str,
            "sum": builtins.sum,
            "tuple": builtins.tuple,
            "zip": builtins.zip,
            "Exception": builtins.Exception,
            "ValueError": builtins.ValueError,
            "KeyError": builtins.KeyError,
            "ZeroDivisionError": builtins.ZeroDivisionError,
            "__import__": builtins.__import__,
        }

        exec_globals = {"__builtins__": safe_builtins, "pd": pd, "np": np}
        for k, v in context.items():
            exec_globals[k] = v

        def _to_json_safe(obj):
            if obj is None or isinstance(obj, (bool, int, float, str)):
                return obj
            if isinstance(obj, dict):
                return {str(k): _to_json_safe(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_to_json_safe(v) for v in obj]
            if hasattr(obj, "to_dict"):
                try:
                    return _to_json_safe(obj.to_dict(orient="records"))
                except TypeError:
                    return _to_json_safe(obj.to_dict())
            if hasattr(obj, "item"):
                return obj.item()
            return str(obj)

        out = {"ok": False, "result": None, "error_type": None, "error_message": ""}
        try:
            exec(compile(user_code, "<sandbox>", "exec"), exec_globals, exec_globals)
            raw_res = exec_globals.get(result_var)
            out["ok"] = True
            out["result"] = _to_json_safe(raw_res)
        except MemoryError as exc:
            out["error_type"] = "memory_limit"
            out["error_message"] = str(exc) or "MemoryError"
        except PermissionError as exc:
            out["error_type"] = "security_violation"
            out["error_message"] = str(exc)
        except Exception as exc:
            out["error_type"] = "runtime_error"
            out["error_message"] = f"{type(exc).__name__}: {exc}"

        json.dump(out, result_writer, ensure_ascii=False)
        result_writer.flush()
        result_writer.close()
        """
    ).lstrip()


def _attach_windows_job_object(proc: subprocess.Popen[str], max_memory_mb: int, max_cpu_sec: int) -> Any:
    """Gán Windows Job Object giới hạn RAM/CPU và tự hủy cây tiến trình khi đóng handle."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002
        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
        JobObjectExtendedLimitInformation = 9

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_PROCESS_MEMORY
        if max_cpu_sec > 0:
            flags |= JOB_OBJECT_LIMIT_PROCESS_TIME
            # Đơn vị 100 nanoseconds.
            info.BasicLimitInformation.PerProcessUserTimeLimit = int(max_cpu_sec * 10_000_000)
        info.BasicLimitInformation.LimitFlags = flags
        info.ProcessMemoryLimit = int(max_memory_mb * 1024 * 1024)

        ok_set = kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok_set:
            kernel32.CloseHandle(job)
            return None

        ok_assign = kernel32.AssignProcessToJobObject(job, int(proc._handle))  # type: ignore[attr-defined]
        if not ok_assign:
            kernel32.CloseHandle(job)
            return None
        return (kernel32, job)
    except Exception:
        return None


def _close_windows_job_object(handle_pair: Any) -> None:
    if handle_pair is None:
        return
    try:
        kernel32, job = handle_pair
        kernel32.CloseHandle(job)
    except Exception:
        pass


def _kill_process_tree(proc: subprocess.Popen[str]) -> None:
    """Dừng cưỡng bức tiến trình con và mọi tiến trình cháu."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
            )
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _minimal_env(workdir: str) -> dict[str, str]:
    """Tạo biến môi trường tối giản, loại bỏ toàn bộ API key và bí mật của tiến trình cha."""
    keep_keys = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "LANG", "LC_ALL")
    env = {k: os.environ[k] for k in keep_keys if k in os.environ}
    env["TEMP"] = workdir
    env["TMP"] = workdir
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Hạn chế OpenBLAS/OMP cấp phát quá nhiều buffer đa luồng trong sandbox.
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    return env


class SandboxExecutor:
    """Trình thực thi cô lập cho code Python/Pandas do LLM sinh ra."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()

    def execute(
        self,
        code: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> SandboxResult:
        """Kiểm tra tĩnh và thực thi ``code`` trong tiến trình cô lập."""
        t0 = time.perf_counter()
        ast_err = validate_code_ast(code, self.config)
        if ast_err is not None:
            return SandboxResult(
                ok=False,
                error_type="security_violation",
                error_message=ast_err,
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        with tempfile.TemporaryDirectory(prefix="fin_sandbox_") as tmpdir:
            tmp_path = Path(tmpdir)
            worker_path = tmp_path / "worker.py"
            payload_path = tmp_path / "payload.json"
            output_path = tmp_path / "output.json"

            site_dirs = [
                p for p in sys.path if "site-packages" in p.lower() or "dist-packages" in p.lower()
            ]
            worker_path.write_text(_build_worker_script(), encoding="utf-8")
            payload_obj = {
                "code": code,
                "context": context or {},
                "allowed_read_dirs": [str(Path(p).resolve()) for p in self.config.allowed_read_dirs],
                "site_dirs": site_dirs,
                "result_var": self.config.result_var,
                "max_memory_mb": self.config.max_memory_mb,
                "max_cpu_sec": self.config.max_cpu_sec,
            }
            payload_path.write_text(json.dumps(payload_obj, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, "-I", str(worker_path), str(payload_path), str(output_path)],
                cwd=tmpdir,
                env=_minimal_env(tmpdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            job_handle = _attach_windows_job_object(
                proc, self.config.max_memory_mb, self.config.max_cpu_sec
            )
            try:
                stdout, stderr = proc.communicate(timeout=self.config.timeout_sec)
            except subprocess.TimeoutExpired:
                _kill_process_tree(proc)
                try:
                    stdout, stderr = proc.communicate(timeout=2.0)
                except Exception:
                    stdout, stderr = "", ""
                _close_windows_job_object(job_handle)
                return SandboxResult(
                    ok=False,
                    stdout=stdout[: self.config.max_output_bytes],
                    stderr=stderr[: self.config.max_output_bytes],
                    error_type="timeout",
                    error_message=f"Execution exceeded timeout ({self.config.timeout_sec}s)",
                    elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    timed_out=True,
                )
            finally:
                _close_windows_job_object(job_handle)

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            stdout_trimmed = (stdout or "")[: self.config.max_output_bytes]
            stderr_trimmed = (stderr or "")[: self.config.max_output_bytes]

            if not output_path.exists():
                err_type = "memory_limit" if "MemoryError" in stderr_trimmed else "runtime_error"
                return SandboxResult(
                    ok=False,
                    stdout=stdout_trimmed,
                    stderr=stderr_trimmed,
                    error_type=err_type,
                    error_message=stderr_trimmed.strip() or f"Worker exited with code {proc.returncode}",
                    elapsed_ms=elapsed_ms,
                )

            try:
                raw = json.loads(output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return SandboxResult(
                    ok=False,
                    stdout=stdout_trimmed,
                    stderr=stderr_trimmed,
                    error_type="runtime_error",
                    error_message=f"Malformed sandbox output: {exc}",
                    elapsed_ms=elapsed_ms,
                )

            return SandboxResult(
                ok=bool(raw.get("ok")),
                result=raw.get("result"),
                stdout=stdout_trimmed,
                stderr=stderr_trimmed,
                error_type=raw.get("error_type"),
                error_message=str(raw.get("error_message", "")),
                elapsed_ms=elapsed_ms,
            )
