"""Unprivileged network-denied audit subprocess with a bounded public GET broker.

This is process-level isolation, NOT a Render container-wide egress firewall.
The parent still connects to Neon and to vetted public addresses. Public scans
are allowed only through this OS-enforced worker/broker path.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from pagecheck.common.security.public_fetch_broker import public_fetch_broker


class AuditIsolationUnavailable(RuntimeError):
    """Scanner must remain disabled if the kernel guard cannot be proved."""


@lru_cache(maxsize=4)
def verify_worker_launcher(executable: str) -> None:
    path = Path(executable)
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        raise AuditIsolationUnavailable("Network syscall guard executable is unavailable")
    try:
        check = subprocess.run([executable, "--self-test"], text=True,
                               capture_output=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditIsolationUnavailable("Network syscall guard self-test failed") from exc
    required = ("SECCOMP_IPV4_BLOCKED", "SECCOMP_IPV6_BLOCKED",
                "SECCOMP_UNIX_IPC_ALLOWED", "STAGE36_SYSCALL_GUARD_SELFTEST_PASSED")
    if check.returncode != 0 or any(value not in check.stdout for value in required):
        raise AuditIsolationUnavailable("Network syscall guard could not be verified")


@lru_cache(maxsize=4)
def verify_worker_python_exec(launcher: str) -> None:
    """Verify that seccomp restrictions survive execve into the Python worker."""
    verify_worker_launcher(launcher)
    script = "\n".join((
        "import socket",
        "blocked = []",
        "for family in (socket.AF_INET, socket.AF_INET6):",
        "    try:",
        "        sock = socket.socket(family, socket.SOCK_STREAM)",
        "    except PermissionError:",
        "        blocked.append(True)",
        "    else:",
        "        sock.close()",
        "print('PYTHON_WORKER_SOCKET_BLOCKED' if len(blocked) == 2 else 'FAILED')",
    ))
    # The command is fixed, without any attacker-controlled strings.
    env = {"PATH": "/usr/bin:/bin", "PAGECHECK_BROWSER_REAL_EXECUTABLE": sys.executable}
    try:
        result = subprocess.run([launcher, "-c", script], env=env, text=True,
                                capture_output=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditIsolationUnavailable("Isolated Python guard test failed") from exc
    if result.returncode != 0 or "PYTHON_WORKER_SOCKET_BLOCKED" not in result.stdout:
        raise AuditIsolationUnavailable("Python worker still has direct network access")


def run_isolated_audit(payload: Any, *, timeout_seconds: int = 110) -> dict:
    launcher = os.environ.get("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", "").strip()
    verify_worker_python_exec(launcher)
    with tempfile.TemporaryDirectory(prefix="pc-audit-") as folder:
        socket_path = Path(folder) / "broker.sock"
        with public_fetch_broker(socket_path):
            # Never give user-controlled page processing the API/Neon secrets.
            env = {
                "HOME": "/tmp", "TMPDIR": "/tmp", "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8", "PYTHONUNBUFFERED": "1",
                "PAGECHECK_ENV": "production",
                "PAGECHECK_PUBLIC_FETCH_BROKER_SOCKET": str(socket_path),
                "PAGECHECK_BROWSER_SECCOMP_LAUNCHER": launcher,
                "PAGECHECK_BROWSER_REAL_EXECUTABLE": sys.executable,
                "PLAYWRIGHT_BROWSERS_PATH": os.getenv("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright"),
            }
            # Support installed package and source-tree integration tests.
            if os.getenv("PYTHONPATH"):
                env["PYTHONPATH"] = os.environ["PYTHONPATH"]
            proc = subprocess.Popen(
                [launcher, "-m", "pagecheck.common.security.isolated_audit_worker"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env, cwd="/tmp", start_new_session=True,
            )
            try:
                out, err = proc.communicate(input=json.dumps(payload.model_dump()),
                                            timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                raise AuditIsolationUnavailable("Audit exceeded the execution time limit") from exc
            if proc.returncode != 0:
                # Avoid reflecting secret paths, stack traces or fetched HTML.
                raise AuditIsolationUnavailable(f"Isolated audit failed (exit={proc.returncode})")
            try:
                report = json.loads(out)
                if not isinstance(report, dict):
                    raise ValueError("Non-object report")
            except ValueError as exc:
                raise AuditIsolationUnavailable("Isolated audit result is invalid") from exc
            return report
