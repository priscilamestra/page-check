"""Privacy-preserving Impeccable JSON contract diagnostics.

Only structural information is returned. Never store or display the HTML,
CLI finding messages, selectors, file paths, URLs, or stdout from the detector.
"""
from __future__ import annotations

import re
from typing import Any

_ALLOWED_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_RULE_KEYS = ("ruleId", "rule_id", "rule", "id", "checkId", "check_id")


def _safe_keys(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(k for k in value if isinstance(k, str) and _ALLOWED_KEY.fullmatch(k))[:20]


def _has_rule_id(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    for key in _RULE_KEYS:
        rule = value.get(key)
        if isinstance(rule, str) and rule.strip():
            return True
        if isinstance(rule, dict):
            nested = rule.get("id") or rule.get("ruleId") or rule.get("rule_id") or rule.get("key")
            if isinstance(nested, str) and nested.strip():
                return True
    return False


def summarize_impeccable_json(payload: object) -> dict[str, Any]:
    """Shape-only summary, robust to unknown future JSON formats.

    The output intentionally excludes **all** original values. This is a
    diagnostic, never a substitute for validating the detector's real output.
    """
    envelope = type(payload).__name__
    top_keys = _safe_keys(payload)
    if isinstance(payload, list):
        records = payload
        recognized_envelope = True
    elif isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        records = payload["findings"]
        recognized_envelope = True
    else:
        records = []
        recognized_envelope = False
    shape_samples = []
    seen = set()
    valid_rule_ids = 0
    for item in records:
        valid_rule_ids += int(_has_rule_id(item))
        sample = (type(item).__name__, tuple(_safe_keys(item)))
        if sample not in seen and len(shape_samples) < 4:
            seen.add(sample)
            shape_samples.append({"record_type": sample[0], "field_names": list(sample[1])})
    return {
        "envelope_type": envelope,
        "envelope_fields": top_keys,
        "recognized_envelope": recognized_envelope,
        "record_count": len(records),
        "records_with_explicit_rule_id": valid_rule_ids,
        "records_without_explicit_rule_id": len(records) - valid_rule_ids,
        "sample_schemas": shape_samples,
        "adapter_compatible": recognized_envelope and valid_rule_ids == len(records),
        "privacy": "Only key names, type names and counts. No HTML or finding values.",
    }
