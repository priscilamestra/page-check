"""Validate the public GitHub repository link shown in Page Check's Tools menu."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


def normalize_github_repository_url(value: str | None) -> str | None:
    """Return a canonical HTTPS GitHub owner/repository URL, or None.

    A profile URL alone cannot be starred. Unknown hosts, deep paths,
    credentials, query strings, fragments and invalid path components are
    rejected so the configured link cannot turn into an arbitrary redirect.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return None
    if (
        parts.scheme.lower() != "https"
        or parts.netloc.lower() != "github.com"
        or parts.query
        or parts.fragment
    ):
        return None
    segments = parts.path.strip("/").split("/")
    if len(segments) != 2:
        return None
    owner, repository = segments
    if repository.endswith(".git"):
        repository = repository[:-4]
    if (
        not _OWNER.fullmatch(owner)
        or not _REPOSITORY.fullmatch(repository)
        or repository in {".", ".."}
    ):
        return None
    return f"https://github.com/{owner}/{repository}"
