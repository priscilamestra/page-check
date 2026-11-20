from pagecheck.audits.seo.site_rules import audit_crawled_pages


def test_adapted_jev_rules_report_duplicate_titles_and_descriptions_with_urls():
    pages = [
        {"url": "https://example.com/a", "status_code": 200,
         "title": "Same title", "meta_description": "Same description"},
        {"url": "https://example.com/b", "status_code": 200,
         "title": " same   TITLE ", "meta_description": "same description"},
        {"url": "https://example.com/missing", "status_code": 404,
         "title": "Same title", "meta_description": "Same description"},
    ]
    title, description = audit_crawled_pages(pages)
    assert title["check_id"] == "SEO_SITE_UNIQUE_TITLES"
    assert description["check_id"] == "SEO_SITE_UNIQUE_DESCRIPTIONS"
    assert title["status"] == description["status"] == "warning"
    assert title["evidence"]["pages_checked"] == 2
    assert title["evidence"]["duplicate_groups"] == [{
        "observed_value": "same   TITLE",
        "urls": ["https://example.com/a", "https://example.com/b"],
    }]


def test_adapted_jev_rules_pass_when_observed_values_are_unique():
    checks = audit_crawled_pages([
        {"url": "https://example.com/a", "status_code": 200,
         "title": "A", "meta_description": "Description A"},
        {"url": "https://example.com/b", "status_code": 200,
         "title": "B", "meta_description": "Description B"},
    ])
    assert [row["status"] for row in checks] == ["passed", "passed"]
