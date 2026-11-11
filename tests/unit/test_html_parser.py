
from pagecheck.acquisition.http.parser import parse_html


def test_metadata_and_headings():
    html = """
    <html>
      <head>
        <title>Meu Site</title>
        <meta name="description" content="Landing page de tecnologia">
        <meta name="robots" content="index,follow">
        <link rel="canonical" href="/landing">
      </head>
      <body>
        <h1>Automação de vendas</h1>
        <h2>Benefícios</h2>
      </body>
    </html>
    """

    result = parse_html(html, "https://example.com")

    assert result["title"] == "Meu Site"
    assert result["meta_description"] == "Landing page de tecnologia"
    assert result["meta_robots"] == "index,follow"
    assert result["canonical"] == "https://example.com/landing"
    assert len(result["headings"]) == 2
    assert result["headings"][0]["level"] == "h1"


def test_relative_links():
    html = '<a href="/contato">Fale conosco</a>'

    result = parse_html(html, "https://example.com/landing")

    assert result["links"][0]["text"] == "Fale conosco"
    assert result["links"][0]["resolved_url"] == (
        "https://example.com/contato"
    )


def test_lazy_images():
    html = """
    <img data-src="/produto.webp" loading="lazy" alt="Produto">
    <img src="/banner.jpg">
    """

    result = parse_html(html, "https://example.com/landing")

    assert len(result["images"]) == 2
    assert result["images"][0]["loading"] == "lazy"
    assert result["images"][0]["alt"] == "Produto"
    assert result["images"][0]["data_src"] == (
        "https://example.com/produto.webp"
    )
    assert result["images"][1]["alt"] is None


def test_missing_metadata():
    result = parse_html("<html><body></body></html>", "https://example.com")

    assert result["title"] is None
    assert result["meta_description"] is None
    assert result["canonical"] is None
    assert result["headings"] == []
    assert result["links"] == []
    assert result["images"] == []
