"""Regression: missing runtime modules must fail image build, not API startup."""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def test_html_parser_is_declared_as_runtime_dependency():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = project["project"]["dependencies"]
    assert any(dep.startswith("beautifulsoup4") for dep in deps)


def test_docker_build_checks_api_imports_and_uses_current_lock():
    api = (ROOT / "deploy" / "Dockerfile.api").read_text(encoding="utf-8")
    ui = (ROOT / "deploy" / "Dockerfile.ui").read_text(encoding="utf-8")
    assert "uv sync --locked --no-dev --no-editable" in api
    assert "uv sync --locked --no-dev --no-editable" in ui
    assert "from bs4 import BeautifulSoup" in api
    assert "from pagecheck.api.app import app" in api
    assert "from playwright.sync_api import sync_playwright" in api
    assert "API_RUNTIME_IMPORTS_OK" in api
