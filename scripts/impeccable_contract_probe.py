"""Probe the *locally installed* Impeccable on a safe offline HTML fixture.

Usage: uv run python scripts/impeccable_contract_probe.py
Optional: --html-file path/to/known-local-file.html (never fetches a URL).
Prints only schema field names, counts, and outcome; no page content.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from pagecheck.integrations.cli_runner import local_binary
from pagecheck.integrations.impeccable.contract_probe import summarize_impeccable_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = """<!doctype html><html lang='en'><head><title>Fixture</title></head>
<body><main><h1>Marketing overview</h1><p>Test-only content for a static rule scan.</p>
<button type='button'>Details</button></main></body></html>"""


def probe(*, root: Path = ROOT, html_file: Path | None = None,
          timeout: int = 40) -> dict:
    binary = local_binary(root, "impeccable")
    if binary is None:
        return {"detector_status": "missing_local_binary",
                "instruction": "Install the project's local Impeccable package; no npx download is run."}
    if html_file is None:
        html = FIXTURE
    else:
        html_file = html_file.resolve(strict=True)
        if not html_file.is_file() or html_file.suffix.lower() not in {".html", ".htm"}:
            return {"detector_status": "invalid_local_html_file"}
        if html_file.stat().st_size > 1_000_000:
            return {"detector_status": "input_too_large"}
        html = html_file.read_text(encoding="utf-8", errors="replace")
    # Import the existing sanitizer only when the local detector is present.
    # This keeps missing-binary diagnostics independent of the browser stack.
    from pagecheck.application.use_cases.collect_static_engines import sanitize_static_html
    safe = sanitize_static_html(html)
    with TemporaryDirectory(prefix="pagecheck-impeccable-probe-") as tmp:
        snapshot = Path(tmp) / "snapshot.html"
        snapshot.write_text(safe, encoding="utf-8")
        try:
            proc = subprocess.run(
                [str(binary), "detect", "--json", str(snapshot)],
                cwd=str(root.resolve()), capture_output=True, timeout=timeout,
                text=True, encoding="utf-8", errors="replace", check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"detector_status": "unavailable", "error_type": type(exc).__name__}
    if proc.returncode not in (0, 2):
        return {"detector_status": "failed", "exit_code": proc.returncode,
                "note": "Detector stderr is intentionally not displayed."}
    if len(proc.stdout) > 2_000_000:
        return {"detector_status": "output_too_large"}
    try:
        payload = json.loads(proc.stdout)
    except (ValueError, TypeError):
        return {"detector_status": "invalid_json"}
    return {"detector_status": "ran", "exit_code": proc.returncode,
            "contract": summarize_impeccable_json(payload)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe offline Impeccable JSON schema probe")
    parser.add_argument("--html-file", type=Path,
                        help="Optional existing local HTML file, never a URL")
    args = parser.parse_args()
    print(json.dumps(probe(html_file=args.html_file), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
