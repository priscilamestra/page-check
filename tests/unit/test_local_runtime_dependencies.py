"""Regression tests for local runtime dependencies and security."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_html_parser_is_declared_as_runtime_dependency():
    project = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    deps = project["project"]["dependencies"]
    assert any(dep.startswith("beautifulsoup4") for dep in deps)


def test_crawl_and_browser_dependencies_are_declared():
    project = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    deps = project["project"]["dependencies"]
    assert any(dep.startswith("scrapling") for dep in deps)
    assert any(dep.startswith("playwright") for dep in deps)


def test_isolated_worker_runs_static_engines_inside_the_network_guard():
    worker = (
        ROOT / "src/pagecheck/common/security/isolated_audit_worker.py"
    ).read_text(encoding="utf-8")
    assert "external_collector=collect_static_engines" in worker
