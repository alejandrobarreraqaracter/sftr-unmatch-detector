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

import re
import pandas as pd
from io import BytesIO
from typing import Optional


def normalize_col(name: str) -> str:
    """Normalize a string to a column-safe name."""
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def parse_tabular_csv(content: bytes) -> list[dict]:
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

    # Build normalized column index
    norm_to_original: dict[str, str] = {normalize_col(c): c for c in df.columns}

    # Identify CP1/CP2 column pairs
    cp1_cols: dict[str, str] = {}   # base_name -> original_col
    cp2_cols: dict[str, str] = {}

    for norm, orig in norm_to_original.items():
        if norm.endswith("_cp1"):
            base = norm[:-4]
            cp1_cols[base] = orig
        elif norm.endswith("_cp2"):
            base = norm[:-4]
            cp2_cols[base] = orig

    metadata_keys = {"uti", "sft_type", "action_type", "emisor_name", "receptor_name", "emisor_lei", "receptor_lei"}

    rows = []
    for _, row in df.iterrows():
        raw = row.to_dict()

        def get_meta(key: str, default: str = "") -> str:
            orig = norm_to_original.get(key)
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

        rows.append({
            "uti": get_meta("uti"),
            "sft_type": get_meta("sft_type", "Repo"),
            "action_type": get_meta("action_type", "NEWT"),
            "emisor_lei": get_meta("emisor_lei") or get_meta("reporting_counterparty_cp1"),
            "receptor_lei": get_meta("receptor_lei") or get_meta("reporting_counterparty_cp2"),
            "emisor": emisor,
            "receptor": receptor,
            "raw": raw,
        })

    return rows
