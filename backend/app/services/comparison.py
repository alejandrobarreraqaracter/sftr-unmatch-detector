from typing import Optional
from app.services.field_registry import get_all_fields, get_obligation

MIRROR_PAIRS = {
    "GIVE": "TAKE",
    "TAKE": "GIVE",
    "MRGG": "MRGE",
    "MRGE": "MRGG",
}


def normalize(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


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


def compare_fields(
    emisor_data: dict[str, str],
    receptor_data: dict[str, str],
    sft_type: str = "Repo",
    action_type: str = "NEWT",
) -> list[dict]:
    results = []
    all_fields = get_all_fields()

    for field in all_fields:
        field_name = field["name"]
        table_number = field["table"]
        field_number = field["number"]
        is_mirror = field.get("is_mirror", False)

        obligation = get_obligation(field, sft_type, action_type)

        emisor_val = emisor_data.get(field_name, "")
        receptor_val = receptor_data.get(field_name, "")

        e_norm = normalize(emisor_val)
        r_norm = normalize(receptor_val)

        if obligation == "-":
            result = "NA"
            severity = "NONE"
        elif e_norm == "" and r_norm == "":
            result = "NA"
            severity = "NONE"
        elif e_norm == r_norm:
            result = "MATCH"
            severity = "NONE"
        elif is_mirror and is_mirror_match(emisor_val, receptor_val):
            result = "MIRROR"
            severity = "NONE"
        else:
            result = "UNMATCH"
            severity = classify_severity(obligation)

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
            "status": status,
            "validated": True,
        })

    return results
