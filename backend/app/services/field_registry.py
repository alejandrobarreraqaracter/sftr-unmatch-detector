import json
import os
from typing import Optional

_fields = None
_fields_by_name = None


def _load():
    global _fields, _fields_by_name
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sftr_fields.json")
    with open(path) as f:
        _fields = json.load(f)
    _fields_by_name = {}
    for field in _fields:
        _fields_by_name[field["name"].strip().upper()] = field


def get_all_fields() -> list[dict]:
    if _fields is None:
        _load()
    return _fields  # type: ignore


def get_field_by_name(name: str) -> Optional[dict]:
    if _fields_by_name is None:
        _load()
    return _fields_by_name.get(name.strip().upper())  # type: ignore


def get_obligation(field: dict, sft_type: str, action_type: str) -> str:
    sft_type = sft_type.upper()
    action_type = action_type.upper()
    sft_map = {"REPO": "Repo", "BSB": "BSB", "SL": "SL", "ML": "ML"}
    sft_key = sft_map.get(sft_type, "Repo")
    obl = field.get("obligation", {})
    sft_obl = obl.get(sft_key, {})
    return sft_obl.get(action_type, "-")
