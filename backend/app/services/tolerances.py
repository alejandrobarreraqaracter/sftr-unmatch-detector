"""
Per-field configurable numeric tolerances for SFTR reconciliation.

Design:
  - FIELD_TOLERANCES: dict mapping normalized field name → absolute tolerance
  - OBLIGATION_DEFAULTS: fallback tolerances by obligation level (M/C/O)
  - DEFAULT_TOLERANCE: ultimate fallback if neither field nor obligation match

Lookup order:
  1. Exact field name match in FIELD_TOLERANCES
  2. Obligation-level default from OBLIGATION_DEFAULTS
  3. DEFAULT_TOLERANCE (0.01)

To add a custom tolerance for a field, add it to FIELD_TOLERANCES below.
"""

from typing import Optional


DEFAULT_TOLERANCE: float = 0.01

# Fallback tolerances by obligation level
OBLIGATION_DEFAULTS: dict[str, float] = {
    "M": 0.0001,   # Mandatory fields: very tight
    "C": 0.01,     # Conditional fields: slightly looser
    "O": 0.01,     # Optional fields
}

# Per-field tolerance overrides (normalized field name → absolute tolerance)
# Add entries here to override the obligation-level default for specific fields.
FIELD_TOLERANCES: dict[str, float] = {
    # Table 2 – Loan & Collateral
    "principal amount on value date": 0.01,
    "principal amount on maturity date": 0.01,
    "principal amount on value date (leg 2)": 0.01,
    "principal amount on maturity date (leg 2)": 0.01,
    "fixed rate": 0.0001,
    "fixed rate (leg 2)": 0.0001,
    "spread": 0.0001,
    "spread (leg 2)": 0.0001,
    "margin lending rate": 0.001,
    "outstanding margin loan": 0.01,
    "short market value": 0.01,
    "collateral market value": 0.01,
    "collateral quantity or nominal amount": 0.01,
    "price per unit": 0.0001,
    "collateral quality": 0.01,
    "haircut or margin": 0.0001,

    # Table 3 – Margin Data
    "value of initial margin posted": 0.01,
    "value of initial margin received": 0.01,
    "value of variation margin posted": 0.01,
    "value of variation margin received": 0.01,
    "excess collateral posted": 0.01,
    "excess collateral received": 0.01,
    "margin lending provided to counterparty": 0.01,

    # Table 4 – Re-use Data
    "cash reinvestment rate": 0.0001,
    "estimated reuse of collateral": 0.01,
    "value of reused collateral": 0.01,
    "reinvested cash amount": 0.01,
}


def get_tolerance(field_name: str, obligation: str = "-") -> float:
    """
    Get the numeric tolerance for a specific field.

    Lookup order:
      1. FIELD_TOLERANCES (exact field name, case-insensitive)
      2. OBLIGATION_DEFAULTS (by obligation level)
      3. DEFAULT_TOLERANCE
    """
    # 1. Check per-field override
    field_key = field_name.strip().lower()
    if field_key in FIELD_TOLERANCES:
        return FIELD_TOLERANCES[field_key]

    # 2. Check obligation-level default
    if obligation in OBLIGATION_DEFAULTS:
        return OBLIGATION_DEFAULTS[obligation]

    # 3. Ultimate fallback
    return DEFAULT_TOLERANCE
