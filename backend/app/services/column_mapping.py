"""
Robust column mapping for SFTR CSV ingestion.

The parser depends on column names matching a specific convention:
  {normalized_field_name}_cp1 / _cp2

This module provides:
  1. Alias resolution: maps common alternative column names to canonical names
  2. Consistent normalization: handles various naming conventions
  3. A deterministic, maintainable mapping layer (no AI)

Alias configuration format:
  COLUMN_ALIASES maps normalized alias → canonical normalized field name.
  Both sides are lowercase with underscores.

  Example:
    "rep_timestamp" → "reporting_timestamp"
    means a column named "Rep_Timestamp_CP1" will map to field "Reporting timestamp"
"""

import re
from typing import Optional


def normalize_col(name: str) -> str:
    """Normalize a string to a column-safe name (lowercase, non-alphanumeric → underscore)."""
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


# ── Alias Configuration ─────────────────────────────────────────────────────
# Maps normalized alternative column base names → canonical normalized field name.
# The canonical name should match the field registry after normalize_col().
#
# Add new aliases here when encountering CSV files with different column conventions.

COLUMN_ALIASES: dict[str, str] = {
    # Table 1: Counterparty Data
    "rep_timestamp": "reporting_timestamp",
    "report_timestamp": "reporting_timestamp",
    "reporting_ts": "reporting_timestamp",
    "rep_submitting_entity": "report_submitting_entity",
    "submitting_entity": "report_submitting_entity",
    "rep_counterparty": "reporting_counterparty",
    "reporting_cp": "reporting_counterparty",
    "cp_nature": "nature_of_the_reporting_counterparty",
    "nature_reporting_cp": "nature_of_the_reporting_counterparty",
    "cp_sector": "sector_of_the_reporting_counterparty",
    "sector_reporting_cp": "sector_of_the_reporting_counterparty",
    "other_cp": "other_counterparty",
    "other_counterparty_id": "other_counterparty",
    "cp_country": "country_of_the_other_counterparty",
    "other_cp_country": "country_of_the_other_counterparty",
    "cp_side": "counterparty_side",
    "side": "counterparty_side",

    # Table 2: Loan & Collateral
    "unique_transaction_id": "uti",
    "transaction_id": "uti",
    "execution_ts": "execution_timestamp",
    "exec_timestamp": "execution_timestamp",
    "maturity_dt": "maturity_date",
    "mat_date": "maturity_date",
    "value_dt": "value_date",
    "val_date": "value_date",
    "termination_dt": "termination_date",
    "term_date": "termination_date",
    "principal_amount": "principal_amount_on_value_date",
    "principal_value_date": "principal_amount_on_value_date",
    "principal_amt": "principal_amount_on_value_date",
    "principal_maturity": "principal_amount_on_maturity_date",
    "principal_amt_maturity": "principal_amount_on_maturity_date",
    "principal_ccy": "principal_amount_currency",
    "principal_currency": "principal_amount_currency",
    "security_id": "security_identifier",
    "isin": "security_identifier",
    "collateral_type": "type_of_collateral_component",
    "coll_type": "type_of_collateral_component",
    "coll_market_value": "collateral_market_value",
    "coll_mkt_value": "collateral_market_value",
    "coll_qty": "collateral_quantity_or_nominal_amount",
    "collateral_qty": "collateral_quantity_or_nominal_amount",
    "coll_reuse": "availability_for_collateral_reuse",
    "collateral_reuse": "availability_for_collateral_reuse",

    # Table 2: Rates
    "fix_rate": "fixed_rate",
    "rate_fixed": "fixed_rate",
    "float_ref_rate": "floating_reference_rate",
    "float_rate": "floating_reference_rate",
    "float_ref_period": "floating_reference_period",

    # Table 3: Margin Data
    "im_posted": "value_of_initial_margin_posted",
    "initial_margin_posted": "value_of_initial_margin_posted",
    "im_received": "value_of_initial_margin_received",
    "initial_margin_received": "value_of_initial_margin_received",
    "vm_posted": "value_of_variation_margin_posted",
    "variation_margin_posted": "value_of_variation_margin_posted",
    "vm_received": "value_of_variation_margin_received",
    "variation_margin_received": "value_of_variation_margin_received",
    "im_posted_ccy": "currency_of_initial_margin_posted",
    "im_received_ccy": "currency_of_initial_margin_received",
    "vm_posted_ccy": "currency_of_variation_margin_posted",
    "vm_received_ccy": "currency_of_variation_margin_received",

    # Table 4: Re-use Data
    "reuse_collateral": "estimated_reuse_of_collateral",
    "reuse_estimate": "estimated_reuse_of_collateral",
    "reused_value": "value_of_reused_collateral",
    "reinvest_rate": "cash_reinvestment_rate",
    "reinvestment_rate": "cash_reinvestment_rate",
    "reinvest_amount": "reinvested_cash_amount",
    "reinvested_amount": "reinvested_cash_amount",
    "reinvest_ccy": "currency_of_reinvested_cash",
    "reinvested_ccy": "currency_of_reinvested_cash",
    "funding_src": "funding_source",
    "funding_source_ccy": "funding_source_currency",

    # Metadata aliases
    "sft_type_code": "sft_type",
    "type_sft": "sft_type",
    "action": "action_type",
    "action_code": "action_type",
    "emisor": "emisor_name",
    "receptor": "receptor_name",
    "emisor_id": "emisor_lei",
    "receptor_id": "receptor_lei",
}


def resolve_alias(normalized_base: str) -> str:
    """
    Resolve a normalized column base name to its canonical form.

    If the base name is a known alias, returns the canonical name.
    Otherwise returns the input unchanged.
    """
    return COLUMN_ALIASES.get(normalized_base, normalized_base)


def build_column_index(columns: list[str]) -> tuple[
    dict[str, str],  # cp1_cols: canonical_base → original_col
    dict[str, str],  # cp2_cols: canonical_base → original_col
    dict[str, str],  # metadata: normalized_key → original_col
]:
    """
    Build a column index from raw CSV column names.

    Returns:
      - cp1_cols: mapping of canonical base name → original column name for CP1
      - cp2_cols: mapping of canonical base name → original column name for CP2
      - norm_to_original: full normalized mapping for metadata lookups
    """
    norm_to_original: dict[str, str] = {}
    cp1_cols: dict[str, str] = {}
    cp2_cols: dict[str, str] = {}

    for col in columns:
        norm = normalize_col(col)
        norm_to_original[norm] = col

        if norm.endswith("_cp1"):
            base = norm[:-4]
            canonical = resolve_alias(base)
            cp1_cols[canonical] = col
        elif norm.endswith("_cp2"):
            base = norm[:-4]
            canonical = resolve_alias(base)
            cp2_cols[canonical] = col

    return cp1_cols, cp2_cols, norm_to_original
