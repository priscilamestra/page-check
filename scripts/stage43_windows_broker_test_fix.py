"""Make the stage43 Unix-domain-socket broker test platform-correct.

Run from the Page Check repository root. Modifies only the one unit test.
On Windows, it verifies that the existing fail-closed broker raises RuntimeError.
On Linux, the original functional socket test executes unchanged.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / 'src/pagecheck/common/security/public_fetch_broker.py'
TARGET = ROOT / 'tests/unit/test_stage43_public_worker_broker.py'
MARKER = 'STAGE43_WINDOWS_FAIL_CLOSED_TEST'
FUNC = 'test_broker_delivers_only_bound_public_gets'


def main() -> int:
    if not BROKER.is_file() or not TARGET.is_file():
        raise RuntimeError('Stage43 files missing. Run from the Page Check repository with STAGE43 installed.')
    source = BROKER.read_text(encoding='utf-8')
    if '_BrokerServerBase = getattr(socketserver, "UnixStreamServer", None)' not in source:
        raise RuntimeError('Expected Stage43 guarded Unix socket broker patch not found. No changes made.')
    if 'raise RuntimeError("The isolated Unix-socket broker is unavailable on this platform.")' not in source:
        raise RuntimeError('Windows fail-closed behavior not confirmed. No changes made.')

    original_bytes = TARGET.read_bytes()
    old = original_bytes.decode('utf-8')
    if MARKER in old:
        print('STAGE43_WINDOWS_TEST_ALREADY_CORRECTED')
        return 0

    tree = ast.parse(old, filename=str(TARGET))
    matches = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == FUNC]
    if len(matches) != 1 or not matches[0].body:
        raise RuntimeError('Could not uniquely identify the failing Stage43 test. No changes made.')
    func = matches[0]
    body = func.body
    first = body[1] if len(body) > 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, (ast.Constant, ast.Str)) and isinstance(getattr(body[0].value, 'value', None), str) else body[0]
    indent = ' ' * first.col_offset
    newline = '\r\n' if b'\r\n' in original_bytes else '\n'
    injected_lines = [
        '# STAGE43_WINDOWS_FAIL_CLOSED_TEST: Unix sockets exist only on Unix/Linux.',
        'if __import__("os").name == "nt":',
        '    from pagecheck.common.security.public_fetch_broker import _BrokerServer',
        '    try:',
        '        _BrokerServer("unused-on-windows")',
        '    except RuntimeError as exc:',
        '        assert "unavailable on this platform" in str(exc)',
        '    else:',
        '        raise AssertionError("The Unix-only broker must remain disabled on Windows.")',
        '    return',
    ]
    lines = old.splitlines(keepends=True)
    insertion = ''.join(indent + line + newline for line in injected_lines)
    lines.insert(first.lineno - 1, insertion)
    updated = ''.join(lines)
    ast.parse(updated, filename=str(TARGET))
    TARGET.write_bytes(updated.encode('utf-8'))
    print('STAGE43_WINDOWS_BROKER_TEST_FIXED')
    print('Changed only:', TARGET.relative_to(ROOT))
    print('Windows: tests explicit RuntimeError fail-closed guard; Linux: original integration test still runs.')
    print('No runtime security changes, Render configuration changes, commit, push, or Docker actions.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, SyntaxError, UnicodeError) as exc:
        print('STAGE43_PATCH_NOT_APPLIED:', exc, file=sys.stderr)
        raise SystemExit(1)
