"""Unit tests for the optional GitHub star link (Stage 21A)."""
import pytest

from pagecheck.ui.github_link import normalize_github_repository_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://github.com/my-user/page-check", "https://github.com/my-user/page-check"),
        ("  https://github.com/my-user/Page_Check  ", "https://github.com/my-user/Page_Check"),
        ("https://github.com/my-user/page-check/", "https://github.com/my-user/page-check"),
        ("https://github.com/my-user/page-check.git", "https://github.com/my-user/page-check"),
    ],
)
def test_normalizes_valid_repository_url(raw, expected):
    assert normalize_github_repository_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "https://github.com/my-user",  # Profile, not a repository
        "http://github.com/my-user/page-check",  # No insecure HTTP
        "https://github.com.evil.example/my-user/page-check",
        "https://github.com/my-user/page-check/issues",
        "https://github.com/my-user/page-check?tab=readme",
        "https://github.com/my-user/page-check#readme",
        "https://alice:secret@github.com/my-user/page-check",
        "https://github.com/my-user/..",
        "https://github.com/my-user/p%2Fq",
        "https://github.com/my-user/page-check:444",
        "https://github.com/my-user/page-check/extra",
    ],
)
def test_rejects_invalid_repository_url(raw):
    assert normalize_github_repository_url(raw) is None
