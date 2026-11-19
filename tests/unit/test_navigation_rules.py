from pagecheck.audits.navigation.rules import inspect_navigation

URL = "https://example.com/landing"


def test_existing_fragment_passes():
    checks = inspect_navigation('<a href="#contato">Contato</a><div id="contato"></div>', URL)
    assert checks[0]["status"] == "passed"


def test_missing_fragment_fails_with_evidence():
    checks = inspect_navigation('<a id="cta" href="#inexistente">Agendar</a>', URL)
    assert checks[0]["status"] == "failed"
    assert checks[0]["evidence"]["id"] == "cta"


def test_external_link_is_not_verified():
    checks = inspect_navigation('<a href="https://example.org">Oferta</a>', URL)
    assert checks[0]["status"] == "not_verified"
    assert checks[0]["evidence"]["resolved_url"] == "https://example.org"
    assert checks[0]["evidence"]["selector"] == "a:nth-of-type(1)"
    assert checks[0]["evidence"]["element_html"] == '<a href="https://example.org">Oferta</a>'


def test_empty_link_is_warning_not_broken_remote():
    checks = inspect_navigation('<a href="#">Agendar demonstração</a>', URL)
    assert checks[0]["status"] == "warning"


def test_cta_button_is_not_clicked():
    checks = inspect_navigation('<form><button type="submit">Agendar</button></form>', URL)
    assert checks[0]["status"] == "not_verified"
    assert checks[0]["evidence"]["inside_form"] is True


def test_relative_link_is_not_verified():
    checks = inspect_navigation('<a href="/precos">Preços</a>', URL)
    assert checks[0]["status"] == "not_verified"
    assert checks[0]["evidence"]["resolved_url"] == "https://example.com/precos"


def test_javascript_scheme_not_treated_as_verified_link():
    checks = inspect_navigation('<a href="javascript:alert(1)">Contato</a>', URL)
    assert checks[0]["status"] == "warning"
