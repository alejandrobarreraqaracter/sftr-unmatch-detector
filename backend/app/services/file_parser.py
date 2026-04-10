"""
Tabular CSV parser for SFTR reconciliation reports.

Expected CSV format (semicolon-separated, UTF-8):
  - Header row required
  - One row per trade/operation
  - Metadata columns: uti, sft_type, action_type (case-insensitive)
  - Per-field columns: {normalized_field_name}_cp1 (emisor) and {normalized_field_name}_cp2 (receptor)

Column name normalization: lowercase, non-alphanumeric chars replaced with underscore.
Example: "Reporting timestamp" → "reporting_timestamp_cp1" / "reporting_timestamp_cp2"
"""

from io import BytesIO

import pandas as pd

from app.services.column_mapping import normalize_col, build_column_index, resolve_alias


def parse_tabular_csv(content: bytes, product_type: str = "sftr") -> list[dict]:
    """
    Parse a tabular SFTR reconciliation CSV.
    Returns a list of row dicts, each with:
      - 'uti', 'sft_type', 'action_type' (metadata)
      - 'emisor': dict[field_name -> value]
      - 'receptor': dict[field_name -> value]
      - 'raw': dict of all original column values
    """
    df = pd.read_csv(BytesIO(content), sep=";", dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]

    # Build column index with alias resolution
    cp1_cols, cp2_cols, norm_to_original = build_column_index(list(df.columns))

    rows = []
    for _, row in df.iterrows():
        raw = row.to_dict()

        def get_meta(key: str, default: str = "") -> str:
            # Check direct normalized key first
            orig = norm_to_original.get(key)
            if orig:
                return str(raw.get(orig, "")).strip()
            # Check alias
            canonical = resolve_alias(key)
            if canonical != key:
                orig = norm_to_original.get(canonical)
                if orig:
                    return str(raw.get(orig, "")).strip()
            return default

        emisor: dict[str, str] = {}
        receptor: dict[str, str] = {}

        for base, orig_cp1 in cp1_cols.items():
            orig_cp2 = cp2_cols.get(base)
            # Reconstruct canonical field name (underscore -> space, title-case as fallback)
            field_name = base.replace("_", " ")
            emisor[field_name] = str(raw.get(orig_cp1, "")).strip()
            if orig_cp2:
                receptor[field_name] = str(raw.get(orig_cp2, "")).strip()
            else:
                receptor[field_name] = ""

        uti_value = get_meta("uti")
        if not uti_value:
            uti_value = emisor.get("UTI", "") or receptor.get("UTI", "")

        sft_type_value = get_meta("sft_type", "Repo")
        if product_type == "predatadas":
            sft_type_value = emisor.get("Type of SFT", "") or receptor.get("Type of SFT", "") or "Predatadas"

        rows.append({
            "uti": uti_value,
            "sft_type": sft_type_value,
            "action_type": get_meta("action_type", "NEWT"),
            "emisor_lei": get_meta("emisor_lei") or get_meta("reporting_counterparty_cp1"),
            "receptor_lei": get_meta("receptor_lei") or get_meta("reporting_counterparty_cp2"),
            "emisor": emisor,
            "receptor": receptor,
            "raw": raw,
        })

    return rows
