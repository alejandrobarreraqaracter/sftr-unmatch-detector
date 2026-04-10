import re
from datetime import datetime
from typing import Optional
from app.services.field_registry import (
    DEFAULT_PRODUCT_TYPE,
    PRODUCT_TYPE_PREDATADAS,
    get_all_fields,
    get_field_by_name,
    get_obligation,
)
from app.services.tolerances import get_tolerance
from app.services.validators import validate_field_value

MIRROR_PAIRS = {
    "GIVE": "TAKE",
    "TAKE": "GIVE",
    "MRGG": "MRGE",
    "MRGE": "MRGG",
}

NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)


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


def _parse_datetime(value: str) -> Optional[datetime]:
    normalized = value.strip()
    if not normalized:
        return None

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue

    if normalized.endswith("Z"):
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def compute_difference(field_name: str, emisor_val: Optional[str], receptor_val: Optional[str]) -> tuple[Optional[float], Optional[str], Optional[str]]:
    if not emisor_val or not receptor_val:
        return None, None, None

    field_upper = field_name.strip().upper()
    if field_upper not in {"REPORTING TIMESTAMP", "EXECUTION TIMESTAMP", "EVENT DATE"}:
        return None, None, None

    emisor_dt = _parse_datetime(emisor_val)
    receptor_dt = _parse_datetime(receptor_val)
    if not emisor_dt or not receptor_dt:
        return None, None, None

    delta_seconds = (emisor_dt - receptor_dt).total_seconds()
    if field_upper == "EVENT DATE":
        delta_days = delta_seconds / 86400
        display = f"{delta_days:+.0f} días"
        return delta_days, "days", display

    display = f"{delta_seconds:+.0f} s"
    return delta_seconds, "seconds", display


def compare_trade(
    emisor_data: dict[str, str],
    receptor_data: dict[str, str],
    sft_type: str = "Repo",
    action_type: str = "NEWT",
    product_type: str = DEFAULT_PRODUCT_TYPE,
) -> list[dict]:
    """
    Compare emisor vs receptor data for a single trade.
    Returns list of field comparison dicts.
    """
    results = []
    all_fields = get_all_fields(product_type)

    for field in all_fields:
        field_name = field["name"]
        emisor_val = _get_field_value(emisor_data, field_name)
        receptor_val = _get_field_value(receptor_data, field_name)
        results.append(compare_field(field_name, emisor_val, receptor_val, sft_type, action_type, product_type))

    return results


def compare_field(
    field_name: str,
    emisor_val: Optional[str],
    receptor_val: Optional[str],
    sft_type: str = "Repo",
    action_type: str = "NEWT",
    product_type: str = DEFAULT_PRODUCT_TYPE,
) -> dict:
    field = get_field_by_name(field_name, product_type)
    if not field:
        raise ValueError(f"Field not found in registry: {field_name}")

    table_number = field["table"]
    field_number = field["number"]
    is_mirror = field.get("is_mirror", False)
    obligation = get_obligation(field, sft_type, action_type, product_type)

    e_norm = normalize(emisor_val)
    r_norm = normalize(receptor_val)
    tolerance = get_tolerance(field_name, obligation)
    difference_value, difference_unit, difference_display = compute_difference(field_name, emisor_val, receptor_val)

    # Proactive validation: check individual field values
    if product_type == PRODUCT_TYPE_PREDATADAS:
        emisor_validation = None
        receptor_validation = None
    else:
        emisor_validation = validate_field_value(field_name, emisor_val) if emisor_val else None
        receptor_validation = validate_field_value(field_name, receptor_val) if receptor_val else None

    if obligation == "-":
        if not e_norm and not r_norm:
            result = "MATCH"
            severity = "NONE"
            root_cause = "BOTH_EMPTY"
        elif e_norm == r_norm:
            result = "MATCH"
            severity = "NONE"
            root_cause = "MATCH"
        else:
            result = "NA"
            severity = "NONE"
            root_cause = "NOT_APPLICABLE"
    elif not e_norm and not r_norm:
        result = "MATCH"
        severity = "NONE"
        root_cause = "BOTH_EMPTY"
    elif e_norm == r_norm:
        result = "MATCH"
        severity = "NONE"
        root_cause = "MATCH"
    elif is_mirror and is_mirror_match(emisor_val or "", receptor_val or ""):
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

    # If root_cause is VALUE_MISMATCH but we have validation errors, enrich it
    if root_cause == "VALUE_MISMATCH" and (emisor_validation or receptor_validation):
        if emisor_validation and receptor_validation:
            root_cause = "BOTH_INVALID_FORMAT"
        elif emisor_validation:
            root_cause = f"EMISOR_{emisor_validation}"
        elif receptor_validation:
            root_cause = f"RECEPTOR_{receptor_validation}"

    return {
        "table_number": table_number,
        "field_number": field_number,
        "field_name": field_name,
        "obligation": obligation,
        "emisor_value": emisor_val if emisor_val else None,
        "receptor_value": receptor_val if receptor_val else None,
        "difference_value": difference_value,
        "difference_unit": difference_unit,
        "difference_display": difference_display,
        "result": result,
        "severity": severity,
        "root_cause": root_cause,
        "status": status,
        "validated": True,
        "emisor_validation": emisor_validation,
        "receptor_validation": receptor_validation,
    }


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
