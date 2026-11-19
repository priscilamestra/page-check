"""Contextual, deterministic checks for page language and user-supplied keywords.

No keyword discovery, translations, SERP queries, LLMs, or ranking claims.
These guidance checks supplement technical SEO. They do not change its score.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from typing import Any

from bs4 import BeautifulSoup

LANGUAGES = {"en": "English", "pt": "Portuguese", "es": "Spanish"}
MAX_KEYWORDS = 8
STOPWORDS = {
    "en": {"about", "after", "also", "from", "have", "into", "more", "that", "their",
           "these", "this", "with", "your", "the", "and", "for", "you"},
    "pt": {"como", "mais", "para", "pela", "pelo", "sobre", "tambem", "uma", "das",
           "dos", "que", "com", "seu", "sua"},
    "es": {"como", "para", "sobre", "tambien", "una", "del", "las", "los", "que",
           "con", "sus"},
}


def normalize_keywords(keywords: Sequence[str] | None) -> list[str]:
    if keywords is None:
        return []
    if isinstance(keywords, (str, bytes)) or not isinstance(keywords, (list, tuple)):
        raise TypeError("Keywords must be a list of phrases.")
    if len(keywords) > MAX_KEYWORDS:
        raise ValueError(f"Select up to {MAX_KEYWORDS} keywords.")
    result: list[str] = []
    seen: set[str] = set()
    for item in keywords:
        if not isinstance(item, str):
            raise TypeError("Keywords must be text.")
        phrase = " ".join(item.strip().split())
        if not 2 <= len(phrase) <= 60:
            raise ValueError("Each keyword must contain 2–60 characters.")
        canonical = phrase.casefold()
        if canonical in seen:
            raise ValueError("Duplicate keywords are not allowed.")
        seen.add(canonical)
        result.append(phrase)
    return result


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def _phrase_present(phrase: str, text: object) -> bool:
    # Match word boundaries rather than substring matches (e.g. 'sale' != 'wholesale').
    needle = re.escape(_fold(phrase))
    needle = needle.replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<!\w){needle}(?!\w)", _fold(text)))


def _terms(value: object) -> list[tuple[str, str]]:
    """Return display and comparison forms for meaningful word-like terms."""
    result = []
    for match in re.finditer(r"[^\W\d_]{4,}", str(value or ""), re.UNICODE):
        raw = match.group(0)
        result.append((raw, _fold(raw)))
    return result


def _relevance_candidates(*, title: str, h1: str, visible_copy: str,
                          language: str, niche: str,
                          keywords: Sequence[str]) -> list[dict[str, Any]]:
    """Flag prominent terms outside the user's supplied SEO context for review."""
    supplied = {folded for phrase in [niche, *keywords] for _, folded in _terms(phrase)}
    stopwords = STOPWORDS[language]
    visible_counts = Counter(folded for _, folded in _terms(visible_copy))
    candidates: dict[str, dict[str, Any]] = {}
    for location, text in (("title", title), ("h1", h1)):
        for raw, folded in _terms(text):
            if folded in supplied or folded in stopwords or folded in candidates:
                if folded in candidates:
                    candidates[folded]["locations"][location] = True
                continue
            candidates[folded] = {
                "term": raw,
                "locations": {"title": location == "title", "h1": location == "h1"},
                "visible_occurrences": visible_counts[folded],
                "reason": "Prominent in the title or H1 but outside the supplied niche and target terms.",
            }
    return list(candidates.values())[:5]


def _check(rule: str, status: str, title: str, observed: dict[str, Any],
           recommendation: str = "", severity: str = "info") -> dict[str, Any]:
    return {
        "check_id": rule,
        "module": "seo",
        "status": status,
        "severity": severity,
        "title": title,
        "team": "SEO / Content",
        "recommendation": recommendation,
        "evidence": {"source": "html_content", **observed},
    }


def inspect_content_guidance(html: str, extracted: dict[str, Any], *,
                             language: str, niche: str,
                             keywords: Sequence[str] | None = None) -> dict[str, Any]:
    """Check observable content alignment in the language selected by the user.

    This is guidance, not linguistic understanding or market-wide keyword research.
    """
    if language not in LANGUAGES:
        raise ValueError("Choose English, Portuguese, or Spanish.")
    phrases = normalize_keywords(keywords)
    soup = BeautifulSoup(html, "html.parser")
    declared = str((soup.html.get("lang") if soup.html else "") or "").strip().lower()
    page_language = declared.split("-")[0] if declared else None
    checks: list[dict[str, Any]] = []
    if not page_language:
        checks.append(_check("SEO_CONTENT_LANGUAGE", "warning", "Page language not declared",
            {"selected_language": language, "declared_language": None},
            "Set the HTML lang attribute to the actual page language.", "low"))
    elif page_language != language:
        checks.append(_check("SEO_CONTENT_LANGUAGE", "warning", "Page language differs from the selected language",
            {"selected_language": language, "declared_language": declared},
            "Verify the language selection and the HTML lang attribute.", "low"))
    else:
        checks.append(_check("SEO_CONTENT_LANGUAGE", "passed", "Page language matches the selection",
            {"selected_language": language, "declared_language": declared}))

    title = str(extracted.get("title") or "")
    description = str(extracted.get("meta_description") or "")
    headings = extracted.get("headings") or []
    h1 = " ".join(str(row.get("text") or "") for row in headings
                  if isinstance(row, dict) and row.get("level") == "h1")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    visible_copy = soup.body.get_text(" ", strip=True) if soup.body else soup.get_text(" ", strip=True)
    for index, keyword in enumerate(phrases, 1):
        where = {
            "title": _phrase_present(keyword, title),
            "description": _phrase_present(keyword, description),
            "h1": _phrase_present(keyword, h1),
            "visible_copy": _phrase_present(keyword, visible_copy),
        }
        prominent = any(where[field] for field in ("title", "description", "h1"))
        status = "passed" if prominent else "warning"
        checks.append(_check(f"SEO_TARGET_KEYWORD_{index}", status,
            "Target keyword found in key page elements" if prominent else
            "Target keyword not found in key page elements",
            {"keyword": keyword, "locations": where, "selected_language": language},
            "Review whether this phrase belongs naturally in the title, description, or H1; avoid keyword stuffing."
            if not prominent else "", "low" if not prominent else "info"))
    # Niche is broad context only. An unmatched niche is NOT proof of bad SEO:
    # synonyms, abbreviations and category names require semantic interpretation.
    niche_locations = {"title": _phrase_present(niche, title),
                       "description": _phrase_present(niche, description),
                       "h1": _phrase_present(niche, h1),
                       "visible_copy": _phrase_present(niche, visible_copy)}
    niche_observed = any(niche_locations.values())
    checks.append(_check("SEO_NICHE_CONTEXT",
        "passed" if niche_observed else "not_verified",
        "Niche phrase observed in page text" if niche_observed else "Niche context requires manual review",
        {"niche": niche, "locations": niche_locations, "selected_language": language},
        "The niche may be described with synonyms; use target keywords and review the page manually."
        if not niche_observed else ""))
    relevance_candidates = _relevance_candidates(
        title=title, h1=h1, visible_copy=visible_copy, language=language,
        niche=niche, keywords=phrases,
    )
    return {"language": language, "niche": niche, "keywords": phrases,
            "checks": checks, "relevance_candidates": relevance_candidates,
            "limitations": ["Context checks rely on exact words or phrases with accent-insensitive matching.",
                            "No external keyword research, search volume, ranking, or semantic AI analysis was performed."]}
