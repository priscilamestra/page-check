"""User-facing English copy for the existing multilingual audit data contracts.

Preserves raw source data; only presentation is localized to English.
"""
from __future__ import annotations

from collections.abc import Mapping

TEAM_NAMES = {
    "SEO / Conteúdo": "SEO / Content",
    "Revisão técnica": "Technical review",
    "Frontend / Acessibilidade": "Frontend / Accessibility",
    "Design / Conteúdo": "Design / Content",
    "Equipe": "Team",
}


def team_name(raw: object) -> str:
    return TEAM_NAMES.get(str(raw or ""), str(raw or "Technical review"))


def check_copy(check: Mapping) -> tuple[str, str]:
    """Return an English issue title and actionable guidance for known rules."""
    code = str(check.get("check_id") or check.get("id") or "")
    status = check.get("status")
    evidence = check.get("evidence") or {}
    if not isinstance(evidence, Mapping):
        evidence = {}
    observed = evidence.get("observed_value")
    if code.startswith("SEO_TARGET_KEYWORD_") or code in {"SEO_CONTENT_LANGUAGE", "SEO_NICHE_CONTEXT"}:
        return str(check.get("title") or "Content review"), str(check.get("recommendation") or "")
    if code == "SEO_TITLE":
        return ("Page title is present" if status == "passed" else "Missing page title",
                "Add a clear, descriptive <title> element." if status != "passed" else "")
    if code == "SEO_DESCRIPTION":
        return ("Meta description is present" if status == "passed" else "Missing meta description",
                "Add a useful meta description that describes this page." if status != "passed" else "")
    if code == "SEO_H1":
        return ("Page H1 is present" if status == "passed" else
                "Multiple H1 headings need review" if status == "warning" else "Missing H1 heading",
                "Use a clear main heading and review the heading structure." if status != "passed" else "")
    if code == "SEO_HEADING_ORDER":
        return ("Heading hierarchy is consistent" if status == "passed" else "Heading levels need review",
                "Review skipped heading levels; they are a structural signal, not a ranking guarantee."
                if status != "passed" else "")
    if code == "SEO_CANONICAL":
        return ("Canonical URL is declared" if status == "passed" else "Canonical URL needs review",
                "Check whether this page needs a valid canonical HTTP(S) URL." if status != "passed" else "")
    if code == "SEO_NOINDEX":
        return ("Noindex directive check" if status != "failed" else "Noindex conflicts with organic traffic goal",
                "Review the noindex directive for a page intended to gain organic traffic."
                if status == "failed" else "")
    if code == "SEO_IMAGE_ALT":
        return ("Image alternative text checked" if status == "passed" else "Images may lack alternative text",
                "Add meaningful alt text for informative images; decorative images can have empty alt text."
                if status == "warning" else "")
    if code == "URL_UTM_STRUCTURE":
        return ("UTM parameters are well formed" if status == "passed" else
                "UTM parameters need review" if status == "warning" else "No campaign UTMs supplied",
                "Review empty, duplicated, and inconsistent UTM parameters."
                if status == "warning" else "")
    if code == "URL_REDIRECT_PARAMETERS":
        return ("Campaign parameters retained" if status == "passed" else
                "Campaign parameters changed on redirect" if status == "warning" else "No redirect comparison needed",
                "Review the redirect and your attribution setup; a dropped UTM does not automatically prove lost tracking."
                if status == "warning" else "")
    if code.startswith("NAV_"):
        if "BUTTON_CTA" in code:
            return ("CTA action not executed", "Test the CTA in an authorized browser session; no form was submitted.")
        href = str(evidence.get("href") or "")
        if status == "failed":
            return ("Broken in-page anchor", "Correct the target anchor ID for this link.")
        if status == "not_verified":
            return ("Link destination identified, not tested", "Check the destination with an approved network test.")
        if not href or href == "#":
            return ("Link has no destination", "Set a valid URL or verify its JavaScript behavior.")
        return ("Link structure reviewed", "Review this link's destination and behavior." if status == "warning" else "")
    if code == "FORM_PRESENCE":
        return ("No HTML form detected", "Check whether the form is hosted in another page or widget.")
    if code.startswith("FORM_FIELDS_"):
        return ("Form fields have labels" if status == "passed" else "Form fields are missing labels",
                "Associate labels or accessible names with every relevant form field."
                if status == "warning" else "")
    if code.startswith("FORM_PASSWORD_GET_"):
        return ("Password form uses GET", "Avoid passing passwords through URL query parameters.")
    if code.startswith("FORM_METHOD_"):
        return ("Form submission not tested", "Test submission only in an authorized environment.")
    if code.startswith("FORM_ACTION_"):
        return ("Form target needs review", "Check that the form action is a valid URL.")
    if code == "TRACK_TAG_PRESENCE":
        return ("Analytics tags detected, delivery not verified" if evidence.get("tags_observed") else
                "Analytics tag delivery not verified",
                "Observed script tags do not confirm that analytics events were received.")
    if code.startswith("TRACK_UTM"):
        return ("UTM parameters checked", "Review campaign URL parameters for completeness.")
    if code.startswith("image-broken-"):
        return ("Broken image", "Repair the image source and verify it loads after scrolling.")
    return (str(check.get("title") or "Audit check"), str(check.get("recommendation") or ""))


def englishize_report(report: dict) -> dict:
    """Localize known audit findings for the public API without changing evidence.

    Input is a freshly consolidated mutable report; IDs, statuses, and scores remain
    untouched so both technical tests and clients keep stable identifiers.
    """
    for collection in ("checks", "findings"):
        for item in report.get(collection) or []:
            if not isinstance(item, dict):
                continue
            title, recommendation = check_copy(item)
            item["title"] = title
            item["recommendation"] = recommendation
            item["team"] = team_name(item.get("team"))
    # Consolidation built team actions before localization.
    localized_checks = {item["id"]: item for item in report.get("checks") or []}
    for group in report.get("actions_by_team") or []:
        if not isinstance(group, dict):
            continue
        group["team"] = team_name(group.get("team"))
        for action in group.get("actions") or []:
            if not isinstance(action, dict):
                continue
            reference = localized_checks.get(action.get("finding_id"))
            if reference:
                action["title"] = reference["title"]
                action["action"] = reference["recommendation"]
    coverage = (report.get("summary") or {}).get("check_coverage")
    if isinstance(coverage, dict):
        coverage["meaning"] = "Only checks received; not full coverage of all possible audits."
    report["limitations"] = [
        "The Page Check technical SEO score is separate from Lighthouse scores.",
        "Only executed checks are covered; unrun tools do not count as successful.",
        "This HTML audit does not execute JavaScript or validate checkout actions.",
        "No keyword ranking, search volume, or paid API research is performed.",
    ]
    return report
