from pagecheck.acquisition.http.scrapling_adapter import discover_links


def test_scrapling_discovers_relative_links_with_element_evidence():
    links = discover_links(
        '<main><a id="cta" href="/pricing"><span>See pricing</span></a></main>',
        "https://example.com/start",
    )
    assert len(links) == 1
    assert links[0]["resolved_url"] == "https://example.com/pricing"
    assert links[0]["text"] == "See pricing"
    assert links[0]["selector"]
    assert '<a id="cta"' in links[0]["element_html"]
    assert links[0]["discovered_by"] == "scrapling.Selector"


def test_scrapling_adapter_does_not_invent_empty_or_non_anchor_links():
    links = discover_links(
        '<a href="">Empty</a><button data-href="/fake">No</button><a href="#faq">FAQ</a>',
        "https://example.com/",
    )
    assert [row["resolved_url"] for row in links] == ["https://example.com/#faq"]
