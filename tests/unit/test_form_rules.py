from pagecheck.audits.forms.rules import inspect_forms

URL = "https://example.com/campanha"


def test_form_label_for_is_accepted():
    html = '<form><label for="email">Email</label><input id="email" name="email"></form>'
    result = inspect_forms(html, URL)
    assert result[0]["status"] == "passed"
    assert result[1]["status"] == "not_verified"


def test_field_without_label_is_warning():
    html = '<form><input name="email" type="email"></form>'
    result = inspect_forms(html, URL)
    assert result[0]["status"] == "warning"
    assert result[0]["evidence"]["unlabeled_fields"] == ["email"]
    assert result[0]["evidence"]["selector"] == "form:nth-of-type(1)"


def test_form_id_is_used_as_specific_location():
    result = inspect_forms('<form id="signup"><input name="email"></form>', URL)
    assert result[0]["evidence"]["selector"] == "#signup"


def test_wrapping_label_is_accepted():
    html = '<form><label>Nome <input name="nome"></label></form>'
    assert inspect_forms(html, URL)[0]["status"] == "passed"


def test_aria_labelledby_is_accepted():
    html = '<form><span id="label">Nome</span><input aria-labelledby="label"></form>'
    assert inspect_forms(html, URL)[0]["status"] == "passed"


def test_get_password_is_flagged():
    html = '<form method="get"><label>Senha<input type="password"></label></form>'
    assert any(item["status"] == "failed" for item in inspect_forms(html, URL))


def test_no_form_for_leads_is_warning_not_failure():
    result = inspect_forms('<a href="/agenda">Agendar</a>', URL, objective="leads")
    assert result[0]["status"] == "warning"


def test_no_form_for_organic_is_not_applicable():
    result = inspect_forms('<main>Artigo</main>', URL, objective="organic_traffic")
    assert result[0]["status"] == "not_applicable"


def test_missing_action_is_valid_same_page_but_not_submitted():
    html = '<form><input type="hidden" name="id" value="1"></form>'
    result = inspect_forms(html, URL)
    assert result[1]["status"] == "not_verified"
    assert result[1]["evidence"]["resolved_action"] == URL
