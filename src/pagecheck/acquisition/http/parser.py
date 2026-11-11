
"""Extrai informações de HTML já obtido; não faz acesso à rede."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    for tag in soup.find_all("meta"):
        if str(tag.get("name", "")).casefold() == name.casefold():
            content = tag.get("content")
            return str(content).strip() if content is not None else None
    return None


def parse_html(html: str, page_url: str) -> dict:
    """Extrai fatos observáveis do HTML, sem classificá-los como erros."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")

    canonical = None
    for link in soup.find_all("link"):
        rel = link.get("rel") or []

        if "canonical" in [str(item).casefold() for item in rel]:
            href = link.get("href")
            if href:
                canonical = urljoin(page_url, str(href))
            break

    headings = [
        {
            "level": tag.name,
            "text": tag.get_text(" ", strip=True),
        }
        for tag in soup.find_all(["h1", "h2", "h3"])
    ]

    links = [
        {
            "text": tag.get_text(" ", strip=True),
            "href": str(tag["href"]),
            "resolved_url": urljoin(page_url, str(tag["href"])),
        }
        for tag in soup.select("a[href]")
    ]

    images = []

    for tag in soup.find_all("img"):
        src = tag.get("src")
        data_src = tag.get("data-src")

        images.append(
            {
                "src": urljoin(page_url, str(src)) if src else None,
                "data_src": (
                    urljoin(page_url, str(data_src))
                    if data_src else None
                ),
                "alt": tag.get("alt"),
                "loading": tag.get("loading"),
            }
        )

    return {
        "page_url": page_url,
        "title": (
            " ".join(title.get_text(" ", strip=True).split())
            if title else None
        ),
        "meta_description": _meta_content(soup, "description"),
        "meta_robots": _meta_content(soup, "robots"),
        "canonical": canonical,
        "headings": headings,
        "links": links,
        "images": images,
    }
