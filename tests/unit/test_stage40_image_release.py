"""Stage40: offline checks for local Docker -> private image deploy route.

These tests do not run Docker, publish images or contact any registry.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "stage40_render_free_images.ps1"


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_release_script_exists_and_requires_explicit_publish():
    text = _script()
    assert "[ValidateSet('Build', 'Publish')]" in text
    assert "[string]$Mode = 'Build'" in text
    assert "if ($Mode -eq 'Build')" in text
    assert "-Mode Publish" in text


def test_builds_original_two_dockerfiles_for_render_amd64():
    text = _script()
    assert "deploy/Dockerfile.api" in text
    assert "deploy/Dockerfile.ui" in text
    assert "'--platform', 'linux/amd64'" in text
    assert "'pagecheck-api:stage40'" in text
    assert "'pagecheck-ui:stage40'" in text
    assert "Assert-LinuxAmd64" in text


def test_one_private_registry_repository_with_two_explicit_tags():
    text = _script()
    assert "[string]$DockerHubRepo = 'pagecheck-staging'" in text
    assert '):stage40-api"' in text
    assert '):stage40-ui"' in text
    assert "The Docker Hub repository MUST be private" in text
    assert "[switch]$PrivateRepositoryConfirmed" in text
    assert "if (-not $PrivateRepositoryConfirmed)" in text
    assert "Invoke-Docker -Arguments @('push', $api)" in text
    assert "Invoke-Docker -Arguments @('push', $ui)" in text


def test_no_git_push_and_no_secrets_in_build_args():
    text = _script()
    assert "& git" not in text
    assert "'git', 'push'" not in text
    assert "--build-arg" not in "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    assert "PAGECHECK_DATABASE_URL=" not in text
    assert "PAGECHECK_PRIVATE_API_KEY=" not in text


def test_chromium_kernel_guard_is_part_of_local_smoke():
    assert 'pagecheck-chromium-sandbox' in _script()
    assert "'--self-test'" in _script()


def test_docker_build_context_excludes_private_env_and_git():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for marker in (".git/", ".env", ".env.*", "artifacts/", "tests/"):
        assert marker in ignore


def test_stage39_images_have_no_secret_build_arguments():
    for relative in ("deploy/Dockerfile.api", "deploy/Dockerfile.ui"):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "ARG PAGECHECK_DATABASE_URL" not in content
        assert "ARG PAGECHECK_PRIVATE_API_KEY" not in content
        assert "COPY . ." not in content
