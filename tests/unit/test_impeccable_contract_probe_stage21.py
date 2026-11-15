"""The contract probe must not leak page or finding values."""

from pagecheck.integrations.impeccable.contract_probe import summarize_impeccable_json


def test_empty_list_is_a_valid_clean_scan():
    summary = summarize_impeccable_json([])
    assert summary["adapter_compatible"] is True
    assert summary["record_count"] == 0


def test_canonical_rule_id_is_detected():
    value = summarize_impeccable_json([{"ruleId": "x", "message": "SECRET"}])
    assert value["adapter_compatible"]
    assert value["records_with_explicit_rule_id"] == 1
    assert "SECRET" not in str(value)


def test_mismatched_record_shows_fields_not_values():
    value = summarize_impeccable_json([{"summary": "PRIVATE HTML", "category": "design"}])
    assert not value["adapter_compatible"]
    assert value["records_without_explicit_rule_id"] == 1
    assert "summary" in value["sample_schemas"][0]["field_names"]
    assert "PRIVATE HTML" not in str(value)


def test_nested_rule_object_accepted():
    assert summarize_impeccable_json([{"rule": {"id": "small-type"}}])["adapter_compatible"]


def test_recognized_findings_envelope():
    value = summarize_impeccable_json({"findings": [{"id": "x"}], "token": "SECRET"})
    assert value["adapter_compatible"]
    assert "SECRET" not in str(value)


def test_unrecognized_envelope_refuses_to_call_success():
    value = summarize_impeccable_json({"results": [{"id": "x"}]})
    assert not value["adapter_compatible"]
    assert value["record_count"] == 0


def test_unrecognized_record_is_not_fabricated():
    value = summarize_impeccable_json(["garbage"])
    assert not value["adapter_compatible"]
    assert value["records_with_explicit_rule_id"] == 0


def test_shape_samples_are_bounded():
    data = [{"field" + chr(97 + i): i} for i in range(10)]
    value = summarize_impeccable_json(data)
    assert len(value["sample_schemas"]) <= 4
