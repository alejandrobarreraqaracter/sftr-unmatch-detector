"""
Proactive field validation for SFTR reconciliation.

Validates field values against known SFTR format rules before/during comparison.
Returns validation warnings that enrich the root_cause classification.

Supported validations:
  - LEI: 20 alphanumeric characters (ISO 17442)
  - ISIN: 12 characters, 2-letter country prefix + 9 alphanum + 1 check digit
  - Dates: ISO 8601 (YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ)
  - ISO Currencies: 3-letter ISO 4217 code
  - Booleans: true/false (case-insensitive)
  - Numerics: valid decimal or integer
"""

import re
from datetime import date, datetime
from typing import Optional


# ── LEI validation (ISO 17442) ──────────────────────────────────────────────

LEI_RE = re.compile(r"^[A-Z0-9]{20}$")

def validate_lei(value: str) -> Optional[str]:
    """Validate a Legal Entity Identifier (20 alphanumeric chars)."""
    if not value:
        return None
    v = value.strip().upper()
    if not LEI_RE.match(v):
        return f"INVALID_LEI_FORMAT"
    return None


# ── ISIN validation ─────────────────────────────────────────────────────────

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

def validate_isin(value: str) -> Optional[str]:
    """Validate an International Securities Identification Number."""
    if not value:
        return None
    v = value.strip().upper()
    if not ISIN_RE.match(v):
        return f"INVALID_ISIN_FORMAT"
    return None


# ── Date validation (ISO 8601) ──────────────────────────────────────────────

DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD
    r"(T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?)?$"  # optional time
)

def validate_date(value: str) -> Optional[str]:
    """Validate an ISO 8601 date or datetime."""
    if not value:
        return None
    v = value.strip()
    if not DATE_RE.match(v):
        return "INVALID_DATE_FORMAT"
    try:
        if "T" in v:
            normalized = v.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            year = parsed.year
        else:
            parsed = date.fromisoformat(v)
            year = parsed.year
        if not (1900 <= year <= 2100):
            return "INVALID_DATE_RANGE"
    except ValueError:
        return "INVALID_DATE_RANGE"
    return None


# ── ISO 4217 Currency codes ─────────────────────────────────────────────────

ISO_CURRENCIES = {
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD",
    "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS",
    "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS", "KHR",
    "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD",
    "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU",
    "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK",
    "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
    "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK",
    "SGD", "SHP", "SLE", "SLL", "SOS", "SRD", "SSP", "STN", "SVC", "SYP",
    "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS",
    "UAH", "UGX", "USD", "UYU", "UZS", "VED", "VES", "VND", "VUV", "WST",
    "XAF", "XAG", "XAU", "XCD", "XDR", "XOF", "XPF", "YER", "ZAR", "ZMW",
    "ZWL",
}

CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

def validate_currency(value: str) -> Optional[str]:
    """Validate an ISO 4217 currency code."""
    if not value:
        return None
    v = value.strip().upper()
    if not CURRENCY_RE.match(v):
        return "INVALID_CURRENCY_FORMAT"
    if v not in ISO_CURRENCIES:
        return "UNKNOWN_CURRENCY_CODE"
    return None


# ── Boolean validation ──────────────────────────────────────────────────────

BOOLEAN_VALUES = {"TRUE", "FALSE", "YES", "NO", "Y", "N", "1", "0"}

def validate_boolean(value: str) -> Optional[str]:
    """Validate a boolean-like value."""
    if not value:
        return None
    v = value.strip().upper()
    if v not in BOOLEAN_VALUES:
        return "INVALID_BOOLEAN_FORMAT"
    return None


# ── Numeric validation ──────────────────────────────────────────────────────

NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")

def validate_numeric(value: str) -> Optional[str]:
    """Validate a numeric value."""
    if not value:
        return None
    v = value.strip()
    if not NUMERIC_RE.match(v):
        return "INVALID_NUMERIC_FORMAT"
    return None


# ── Field type classification ───────────────────────────────────────────────

# Map normalized field names to their expected validation type
# These are the key SFTR fields that have known format requirements.
FIELD_TYPE_MAP: dict[str, str] = {
    # LEI fields
    "report submitting entity": "lei",
    "reporting counterparty": "lei",
    "other counterparty": "lei",
    "entity responsible for the report": "lei",
    "broker": "lei",
    "clearing member": "lei",
    "csd participant or indirect participant": "lei",
    "agent lender": "lei",
    "tri-party agent": "lei",
    "beneficiary": "lei",

    # ISIN fields
    "security identifier": "isin",
    "security identifier (leg 2)": "isin",

    # Date fields
    "reporting timestamp": "datetime",
    "event date": "date",
    "execution timestamp": "datetime",
    "value date": "date",
    "maturity date": "date",
    "termination date": "date",
    "earliest call-back date": "date",
    "general collateral indicator date": "date",
    "value date (leg 2)": "date",
    "maturity date (leg 2)": "date",

    # Currency fields
    "principal amount currency": "currency",
    "principal amount currency (leg 2)": "currency",
    "base currency of outstanding margin loan": "currency",
    "currency of initial margin posted": "currency",
    "currency of initial margin received": "currency",
    "currency of variation margin posted": "currency",
    "currency of variation margin received": "currency",
    "currency of excess collateral posted": "currency",
    "currency of excess collateral received": "currency",
    "currency of margin lending": "currency",
    "currency of reinvested cash": "currency",
    "funding source currency": "currency",

    # Boolean fields
    "availability for collateral reuse": "boolean",
    "uncollateralised sl flag": "boolean",
    "general collateral indicator": "boolean",
    "dbv indicator": "boolean",
    "level": "boolean",
    "short sell indicator": "boolean",

    # Numeric fields
    "principal amount on value date": "numeric",
    "principal amount on maturity date": "numeric",
    "principal amount on value date (leg 2)": "numeric",
    "principal amount on maturity date (leg 2)": "numeric",
    "fixed rate": "numeric",
    "fixed rate (leg 2)": "numeric",
    "spread": "numeric",
    "spread (leg 2)": "numeric",
    "margin lending rate": "numeric",
    "outstanding margin loan": "numeric",
    "short market value": "numeric",
    "collateral market value": "numeric",
    "collateral quantity or nominal amount": "numeric",
    "price per unit": "numeric",
    "haircut or margin": "numeric",
    "value of initial margin posted": "numeric",
    "value of initial margin received": "numeric",
    "value of variation margin posted": "numeric",
    "value of variation margin received": "numeric",
    "excess collateral posted": "numeric",
    "excess collateral received": "numeric",
    "margin lending provided to counterparty": "numeric",
    "cash reinvestment rate": "numeric",
    "estimated reuse of collateral": "numeric",
    "value of reused collateral": "numeric",
    "reinvested cash amount": "numeric",
}

# Validator dispatch
_VALIDATORS = {
    "lei": validate_lei,
    "isin": validate_isin,
    "date": validate_date,
    "datetime": validate_date,
    "currency": validate_currency,
    "boolean": validate_boolean,
    "numeric": validate_numeric,
}


def validate_field_value(field_name: str, value: str) -> Optional[str]:
    """
    Validate a field value based on its expected format.

    Returns a validation error string if invalid, None if valid or no rule exists.
    """
    if not value or not value.strip():
        return None

    field_key = field_name.strip().lower()
    field_type = FIELD_TYPE_MAP.get(field_key)
    if not field_type:
        return None

    validator = _VALIDATORS.get(field_type)
    if not validator:
        return None

    return validator(value.strip())


def get_field_type(field_name: str) -> Optional[str]:
    """Return the expected validation type for a field, or None if unknown."""
    return FIELD_TYPE_MAP.get(field_name.strip().lower())
