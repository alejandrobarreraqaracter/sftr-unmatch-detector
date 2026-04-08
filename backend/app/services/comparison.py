"""
Field-level comparison engine for SFTR reconciliation.

For each trade row, compares emisor vs receptor values across all 155 SFTR fields.
Produces a FieldComparison result per field with result, severity, and root_cause.
"""

import re
from typing import Optional
from app.services.field_registry import get_all_fields, get_obligation

MIRROR_PAIRS = {
    "GIVE": "TAKE",
    "TAKE": "GIVE",
    "MRGG": "MRGE",
    "MRGE": "MRGG",
}

# Numeric tolerance per obligation type (absolute delta)
NUMERIC_TOLERANCES: dict[str, float] = {
    "M": 0.0001,   # Critical fields: very tight
    "C": 0.01,     # Conditional fields: slightly looser
    "O": 0.01,
}

NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).strip().upper()


def is_numeric(val: str) -> bool:
    return bool(NUMERIC_RE.match(val.strip()))


def is_date_like(val: str) -> bool:
    return bool(DATE_RE.match(val.strip()))


def is_mirror_match(emisor_val: str, receptor_val: str) -> bool:
    e = normalize(emisor_val)
    r = normalize(receptor_val)
    return MIRROR_PAIRS.get(e) == r


def classify_severity(obligation: str) -> str:
    if obligation == "M":
        return "CRITICAL"
    elif obligation == "C":
        return "WARNING"
    elif obligation == "O":
        return "INFO"
    return "NONE"


def detect_root_cause(
    e_norm: str,
    r_norm: str,
    obligation: str,
    is_mirror: bool,
) -> str:
    if not e_norm and not r_norm:
        return "BOTH_EMPTY"
    if not e_norm:
        return "MISSING_EMISOR"
    if not r_norm:
        return "MISSING_RECEPTOR"
    if is_mirror and is_mirror_match(e_norm, r_norm):
        return "MIRROR_MATCH"
    if is_numeric(e_norm) and is_numeric(r_norm):
        return "NUMERIC_DELTA"
    if is_date_like(e_norm) and is_date_like(r_norm):
        return "DATE_MISMATCH"
    if e_norm.replace(" ", "").upper() == r_norm.replace(" ", "").upper():
        return "FORMAT_DIFFERENCE"
    return "VALUE_MISMATCH"


def numeric_match(e_norm: str, r_norm: str, tolerance: float) -> bool:
    try:
        return abs(float(e_norm) - float(r_norm)) <= tolerance
    except (ValueError, TypeError):
        return False


def compare_trade(
    emisor_data: dict[str, str],
    receptor_data: dict[str, str],
    sft_type: str = "Repo",
    action_type: str = "NEWT",
) -> list[dict]:
    """
    Compare emisor vs receptor data for a single trade.
    Returns list of field comparison dicts.
    """
    results = []
    all_fields = get_all_fields()

    for field in all_fields:
        field_name = field["name"]
        table_number = field["table"]
        field_number = field["number"]
        is_mirror = field.get("is_mirror", False)

        obligation = get_obligation(field, sft_type, action_type)

        # Match field by name (case-insensitive fuzzy match against emisor/receptor dicts)
        emisor_val = _get_field_value(emisor_data, field_name)
        receptor_val = _get_field_value(receptor_data, field_name)

        e_norm = normalize(emisor_val)
        r_norm = normalize(receptor_val)

        tolerance = NUMERIC_TOLERANCES.get(obligation, 0.0001)

        if obligation == "-":
            result = "NA"
            severity = "NONE"
            root_cause = "NOT_APPLICABLE"
        elif not e_norm and not r_norm:
            result = "NA"
            severity = "NONE"
            root_cause = "BOTH_EMPTY"
        elif e_norm == r_norm:
            result = "MATCH"
            severity = "NONE"
            root_cause = "MATCH"
        elif is_mirror and is_mirror_match(emisor_val, receptor_val):
            result = "MIRROR"
            severity = "NONE"
            root_cause = "MIRROR_MATCH"
        elif is_numeric(e_norm) and is_numeric(r_norm) and numeric_match(e_norm, r_norm, tolerance):
            result = "MATCH"
            severity = "NONE"
            root_cause = "NUMERIC_WITHIN_TOLERANCE"
        else:
            result = "UNMATCH"
            severity = classify_severity(obligation)
            root_cause = detect_root_cause(e_norm, r_norm, obligation, is_mirror)

        status = "PENDING" if result == "UNMATCH" else "EXCLUDED"

        results.append({
            "table_number": table_number,
            "field_number": field_number,
            "field_name": field_name,
            "obligation": obligation,
            "emisor_value": emisor_val if emisor_val else None,
            "receptor_value": receptor_val if receptor_val else None,
            "result": result,
            "severity": severity,
            "root_cause": root_cause,
            "status": status,
            "validated": True,
        })

    return results


def _get_field_value(data: dict[str, str], field_name: str) -> str:
    """
    Look up a field value in data dict with case-insensitive and
    normalized-name matching.
    """
    # Exact match first
    if field_name in data:
        return data[field_name]
    # Case-insensitive match
    field_lower = field_name.lower()
    for k, v in data.items():
        if k.lower() == field_lower:
            return v
    # Normalized match (spaces -> underscores)
    field_norm = re.sub(r"[^a-z0-9]+", "_", field_lower).strip("_")
    for k, v in data.items():
        k_norm = re.sub(r"[^a-z0-9]+", "_", k.lower()).strip("_")
        if k_norm == field_norm:
            return v
    return ""
