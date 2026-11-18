"""Patch only the Stage 43 public worker broker test for Windows.

The actual isolated Unix socket broker is intentionally unavailable on Windows.
This changes the one existing test to assert that it fails closed there while
retaining its original Linux test body, with no production changes.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

TARGET_FUNCTION = "test_broker_delivers_only_bounded_public_gets"
MARKER = "STAGE43_WINDOWS_FAIL_CLOSED_TEST_V2"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_FILE = PROJECT_ROOT / "tests" / "unit" / "test_stage43_public_worker_broker.py"


def main() -> int:
    if not TARGET_FILE.is_file():
        print(f"STAGE43_PATCH_NOT_APPLIED: Test file not found: {TARGET_FILE}")
        return 1

    data = TARGET_FILE.read_bytes()
    has_bom = data.startswith(b"\xef\xbb\xbf")
    try:
        original = data.decode("utf-8-sig")
        tree = ast.parse(original, filename=str(TARGET_FILE))
    except (UnicodeError, SyntaxError) as exc:
        print(f"STAGE43_PATCH_NOT_APPLIED: Could not parse existing test file: {exc}")
        return 1

    if MARKER in original:
        print("STAGE43_WINDOWS_BROKER_TEST_ALREADY_FIXED")
        return 0

    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == TARGET_FUNCTION
    ]
    if len(matches) != 1:
        print(
            f"STAGE43_PATCH_NOT_APPLIED: Expected exactly one {TARGET_FUNCTION}; "
            f"found {len(matches)}. No changes made."
        )
        return 1

    function = matches[0]
    if not function.body or not isinstance(function, ast.FunctionDef):
        print("STAGE43_PATCH_NOT_APPLIED: Unexpected target function structure. No changes made.")
        return 1

    params = {arg.arg for arg in function.args.args}
    if "tmp_path" not in params:
        print("STAGE43_PATCH_NOT_APPLIED: Test has no tmp_path fixture. No changes made.")
        return 1

    # Insert immediately before the existing first statement. This uses the Python
    # syntax tree rather than an exact text snippet, which broke the first ZIP.
    insert_index = function.body[0].lineno - 1
    indent = " " * function.body[0].col_offset
    newline = "\r\n" if b"\r\n" in data else "\n"
    guard = [
        f"{indent}# {MARKER}: Windows must reject Unix-socket broker startup.",
        f'{indent}if __import__("sys").platform == "win32":',
        f"{indent}    import pytest",
        f"{indent}    from pagecheck.common.security import public_fetch_broker as broker_module",
        f'{indent}    with pytest.raises(RuntimeError, match="isolated Unix-socket broker is unavailable"):',
        f'{indent}        broker_module._BrokerServer(str(tmp_path / "b.sock"))',
        f"{indent}    return",
        "",
    ]
    lines = original.splitlines(keepends=True)
    patch = "".join(lines[:insert_index] + [newline.join(guard) + newline] + lines[insert_index:])

    try:
        ast.parse(patch, filename=str(TARGET_FILE))
    except SyntaxError as exc:
        print(f"STAGE43_PATCH_NOT_APPLIED: Result is invalid Python: {exc}. No changes made.")
        return 1

    encoded = patch.encode("utf-8")
    if has_bom:
        encoded = b"\xef\xbb\xbf" + encoded
    TARGET_FILE.write_bytes(encoded)
    print(f"STAGE43_WINDOWS_BROKER_TEST_FIXED_V2: {TARGET_FILE.relative_to(PROJECT_ROOT)}")
    print("Production code unchanged; the original Linux assertions remain in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
