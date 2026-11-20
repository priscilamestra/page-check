from pagecheck.acquisition.http.fetcher import FetchedPage, FetchedResource
from pagecheck.application.use_cases.crawl_public_site import crawl_public_site

ROOT_HTML = """<html><head><title>Home</title>
<meta name="description" content="Home description"></head><body>
<main><h1>Home</h1><section id="details">Details</section>
<a href="#details">Details</a><a href="#missing">Missing section</a>
<a href="/about">About</a><a href="/gone">Gone</a><a href="/old">Old</a>
<a href="/blocked">Blocked</a><a href="https://outside.example/x">Outside</a>
</main></body></html>"""


def resource(url, status=200, text="", *, final=None, redirects=(), content_type="text/html"):
    return FetchedResource(url, final or url, status, content_type, text, tuple(redirects))


def test_crawl_checks_internal_links_redirects_anchors_and_robots():
    start = FetchedPage("https://example.com/", "https://example.com/", 200, ROOT_HTML, ())
    calls = []

    def fetch(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return resource(url, text="User-agent: *\nDisallow: /blocked")
        if url.endswith("/about"):
            return resource(url, text="<html><title>About</title><h1>About</h1></html>")
        if url.endswith("/gone"):
            return resource(url, status=404, text="missing")
        if url.endswith("/old"):
            return resource(
                url, text="<html><title>New</title><h1>New</h1></html>",
                final="https://example.com/new", redirects=("https://example.com/new",),
            )
        raise AssertionError(f"unexpected fetch: {url}")

    result = crawl_public_site(start, fetch=fetch)
    assert result["status"] == "limited"
    assert result["adapter"] == "scrapling.Selector"
    assert result["transport"] == "pagecheck_safe_get"
    assert result["summary"] == {
        "discovered": 6, "tested": 5, "valid": 2, "broken": 2,
        "needs_review": 1, "not_tested": 1, "out_of_scope": 1, "pages_crawled": 3,
    }
    states = {(row["href"], row["state"], row["limitation"]) for row in result["links"]}
    assert ("#details", "valid", "") in states
    assert ("#missing", "broken", "fragment_missing") in states
    assert ("/gone", "broken", "") in states
    assert ("/old", "needs_review", "") in states
    assert ("/blocked", "not_tested", "blocked_by_robots") in states
    assert "https://example.com/blocked" not in calls
    assert {page["url"] for page in result["pages"]} == {
        "https://example.com/", "https://example.com/about", "https://example.com/new",
    }
    assert all(row["method"] == "GET" for row in result["links"])
    assert all(row["selector"] and row["element_html"] for row in result["links"])


def test_page_limit_stops_expansion_but_not_link_verification():
    start = FetchedPage("https://example.com/", "https://example.com/", 200,
                        '<a href="/one">One</a><a href="/two">Two</a>', ())

    def fetch(url):
        if url.endswith("robots.txt"):
            return resource(url, status=404)
        return resource(url, text="<html><title>Page</title></html>")

    result = crawl_public_site(start, fetch=fetch, max_pages=1)
    assert result["summary"]["tested"] == 2
    assert result["summary"]["not_tested"] == 0
    assert result["summary"]["pages_crawled"] == 1


def test_two_hundred_eligible_links_are_all_verified_with_bounded_discovery():
    html = "".join(f'<a href="/page-{index}">Page {index}</a>' for index in range(200))
    start = FetchedPage("https://example.com/", "https://example.com/", 200, html, ())

    def fetch(url):
        if url.endswith("robots.txt"):
            return resource(url, status=404)
        return resource(url, text="<html><title>Verified</title></html>")

    result = crawl_public_site(
        start, fetch=fetch, max_pages=5, max_depth=1, max_links=200,
        time_budget_seconds=30,
    )
    assert result["summary"]["discovered"] == 200
    assert result["summary"]["tested"] == 200
    assert result["summary"]["valid"] == 200
    assert result["summary"]["not_tested"] == 0
    assert result["summary"]["pages_crawled"] == 5


def test_local_time_budget_is_configurable(monkeypatch):
    monkeypatch.setenv("PAGECHECK_CRAWL_TIME_BUDGET_SECONDS", "180")
    start = FetchedPage("https://example.com/", "https://example.com/", 200, "", ())
    result = crawl_public_site(start, fetch=lambda url: resource(url, status=404))
    assert result["limits"]["time_budget_seconds"] == 180.0
