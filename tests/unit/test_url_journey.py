from pagecheck.audits.tracking.url_journey import inspect_url_journey

def by_id(rows, check_id):
    return next(row for row in rows if row['check_id'] == check_id)

def test_no_utm_not_error():
    result = inspect_url_journey('https://example.com/p', 'https://example.com/p')
    assert by_id(result, 'URL_UTM_STRUCTURE')['status'] == 'not_applicable'

def test_full_utms_pass():
    url = 'https://example.com/?utm_source=google&utm_medium=cpc&utm_campaign=launch'
    assert by_id(inspect_url_journey(url, url), 'URL_UTM_STRUCTURE')['status'] == 'passed'

def test_partial_utms_warning():
    url = 'https://example.com/?utm_source=google&utm_medium=cpc'
    a = by_id(inspect_url_journey(url, url), 'URL_UTM_STRUCTURE')
    assert a['status'] == 'warning'
    assert 'utm_campaign' in a['evidence']['missing_recommended']

def test_empty_and_duplicate_utms():
    url = 'https://example.com/?utm_source=&utm_source=google&utm_medium=cpc&utm_campaign=x'
    a = by_id(inspect_url_journey(url, url), 'URL_UTM_STRUCTURE')
    assert a['status'] == 'warning'
    assert 'utm_source' in a['evidence']['empty_keys']
    assert 'utm_source' in a['evidence']['conflicting_duplicates']

def test_redirect_drops_click_id_warning_and_does_not_leak_value():
    initial = 'https://example.com/p?gclid=SENSITIVE123'
    final = 'https://example.com/p'
    a = by_id(inspect_url_journey(initial, final, (final,)), 'URL_REDIRECT_PARAMETERS')
    assert a['status'] == 'warning'
    assert 'gclid' in a['evidence']['lost_or_changed_keys']
    assert 'SENSITIVE123' not in str(a)

def test_redirect_preserved_utms_pass():
    initial = 'https://example.com/from?utm_source=google&utm_medium=cpc&utm_campaign=promo'
    final = initial.replace('/from?', '/to?')
    a = by_id(inspect_url_journey(initial, final, (final,)), 'URL_REDIRECT_PARAMETERS')
    assert a['status'] == 'passed'

def test_no_redirect_not_applicable():
    url = 'https://example.com/?utm_source=a'
    assert by_id(inspect_url_journey(url, url), 'URL_REDIRECT_PARAMETERS')['status'] == 'not_applicable'

def test_casefold_utm_keys():
    url = 'https://example.com/?UTM_SOURCE=google&UTM_MEDIUM=cpc&UTM_CAMPAIGN=promo'
    assert by_id(inspect_url_journey(url, url), 'URL_UTM_STRUCTURE')['status'] == 'passed'
