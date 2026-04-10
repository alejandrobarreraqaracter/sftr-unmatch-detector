import json
import os
from functools import lru_cache
from typing import Optional


PRODUCT_TYPE_SFTR = "sftr"
PRODUCT_TYPE_PREDATADAS = "predatadas"
DEFAULT_PRODUCT_TYPE = PRODUCT_TYPE_SFTR

PRODUCT_FIELD_FILES = {
    PRODUCT_TYPE_SFTR: "sftr_fields.json",
    PRODUCT_TYPE_PREDATADAS: "predatadas_fields.json",
}


def normalize_product_type(product_type: Optional[str]) -> str:
    if not product_type:
        return DEFAULT_PRODUCT_TYPE
    normalized = str(product_type).strip().lower()
    return normalized if normalized in PRODUCT_FIELD_FILES else DEFAULT_PRODUCT_TYPE


@lru_cache(maxsize=None)
def _load_product_fields(product_type: str) -> tuple[list[dict], dict[str, dict]]:
    normalized_product = normalize_product_type(product_type)
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        PRODUCT_FIELD_FILES[normalized_product],
    )
    with open(path, encoding="utf-8") as f:
        fields = json.load(f)
    fields_by_name = {field["name"].strip().upper(): field for field in fields}
    return fields, fields_by_name


def get_all_fields(product_type: str = DEFAULT_PRODUCT_TYPE) -> list[dict]:
    return _load_product_fields(product_type)[0]


def get_field_by_name(name: str, product_type: str = DEFAULT_PRODUCT_TYPE) -> Optional[dict]:
    return _load_product_fields(product_type)[1].get(name.strip().upper())


def get_obligation(
    field: dict,
    sft_type: str,
    action_type: str,
    product_type: str = DEFAULT_PRODUCT_TYPE,
) -> str:
    normalized_product = normalize_product_type(product_type)
    obligation = field.get("obligation", {})

    if normalized_product == PRODUCT_TYPE_PREDATADAS:
        product_obligation = obligation.get("Predatadas", {})
        return product_obligation.get(action_type.upper(), "M")

    sft_type_upper = sft_type.upper()
    action_type_upper = action_type.upper()
    sft_map = {"REPO": "Repo", "BSB": "BSB", "SL": "SL", "ML": "ML"}
    sft_key = sft_map.get(sft_type_upper, "Repo")
    sft_obligation = obligation.get(sft_key, {})
    return sft_obligation.get(action_type_upper, "-")
