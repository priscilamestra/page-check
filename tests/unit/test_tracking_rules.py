from pagecheck.audits.tracking.rules import inspect_tracking


def test_complete_utms_pass_structural_check():
    url = "https://example.com/?utm_source=linkedin&utm_medium=paid&utm_campaign=black-friday"
    assert inspect_tracking("", url)[0]["status"] == "passed"


def test_partial_utm_warns():
    url = "https://example.com/?utm_source=linkedin"
    result = inspect_tracking("", url)
    assert result[0]["status"] == "warning"
    assert set(result[0]["evidence"]["missing"]) == {"utm_medium", "utm_campaign"}


def test_empty_required_utm_warns():
    url = "https://example.com/?utm_source=&utm_medium=social&utm_campaign=x"
    assert inspect_tracking("", url)[0]["status"] == "warning"


def test_no_utms_is_not_applicable():
    assert inspect_tracking("", "https://example.com/")[0]["status"] == "not_applicable"


def test_tag_presence_never_confirms_delivery():
    html = '<script src="https://www.googletagmanager.com/gtm.js?id=GTM-TESTE"></script>'
    result = inspect_tracking(html, "https://example.com/")
    assert result[1]["status"] == "not_verified"
    assert "Google Tag Manager" in result[1]["evidence"]["tags_observed"]


def test_no_script_does_not_assert_tracking_broken():
    result = inspect_tracking("<html></html>", "https://example.com/")
    assert result[1]["status"] == "not_verified"
