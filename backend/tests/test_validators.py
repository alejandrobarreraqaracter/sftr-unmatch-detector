"""
Tests for proactive field validation.
"""

import pytest
from app.services.validators import (
    validate_lei,
    validate_isin,
    validate_date,
    validate_currency,
    validate_boolean,
    validate_numeric,
    validate_field_value,
    get_field_type,
)


class TestValidateLEI:
    def test_valid(self):
        assert validate_lei("R0MUWSFPU8MPRO8K5P83") is None

    def test_invalid_length(self):
        assert validate_lei("R0MUWSFPU8") == "INVALID_LEI_FORMAT"

    def test_invalid_chars(self):
        assert validate_lei("R0MUWSFPU8MPRO8K5P8!") == "INVALID_LEI_FORMAT"

    def test_empty(self):
        assert validate_lei("") is None

    def test_lowercase_normalized(self):
        # LEI validation uppercases, so lowercase should still match
        assert validate_lei("r0muwsfpu8mpro8k5p83") is None


class TestValidateISIN:
    def test_valid(self):
        assert validate_isin("ES0000012B61") is None

    def test_invalid_format(self):
        assert validate_isin("INVALID") == "INVALID_ISIN_FORMAT"

    def test_empty(self):
        assert validate_isin("") is None

    def test_too_short(self):
        assert validate_isin("ES000001") == "INVALID_ISIN_FORMAT"


class TestValidateDate:
    def test_date(self):
        assert validate_date("2024-03-15") is None

    def test_datetime(self):
        assert validate_date("2024-03-15T09:32:00Z") is None

    def test_datetime_offset(self):
        assert validate_date("2024-03-15T09:32:00+01:00") is None

    def test_invalid_format(self):
        assert validate_date("15/03/2024") == "INVALID_DATE_FORMAT"

    def test_invalid_range(self):
        assert validate_date("2024-13-01") == "INVALID_DATE_RANGE"
        assert validate_date("2026-02-31") == "INVALID_DATE_RANGE"

    def test_empty(self):
        assert validate_date("") is None


class TestValidateCurrency:
    def test_valid(self):
        assert validate_currency("EUR") is None
        assert validate_currency("USD") is None
        assert validate_currency("GBP") is None

    def test_unknown(self):
        assert validate_currency("XYZ") == "UNKNOWN_CURRENCY_CODE"

    def test_invalid_format(self):
        assert validate_currency("EU") == "INVALID_CURRENCY_FORMAT"

    def test_empty(self):
        assert validate_currency("") is None


class TestValidateBoolean:
    def test_valid(self):
        assert validate_boolean("true") is None
        assert validate_boolean("false") is None
        assert validate_boolean("YES") is None
        assert validate_boolean("NO") is None

    def test_invalid(self):
        assert validate_boolean("maybe") == "INVALID_BOOLEAN_FORMAT"

    def test_empty(self):
        assert validate_boolean("") is None


class TestValidateNumeric:
    def test_valid(self):
        assert validate_numeric("123.45") is None
        assert validate_numeric("-100") is None
        assert validate_numeric("1.23e+10") is None

    def test_invalid(self):
        assert validate_numeric("abc") == "INVALID_NUMERIC_FORMAT"

    def test_empty(self):
        assert validate_numeric("") is None


class TestValidateFieldValue:
    def test_lei_field(self):
        assert validate_field_value("Reporting counterparty", "R0MUWSFPU8MPRO8K5P83") is None
        assert validate_field_value("Reporting counterparty", "INVALID") == "INVALID_LEI_FORMAT"

    def test_date_field(self):
        assert validate_field_value("Reporting timestamp", "2024-03-15T09:32:00Z") is None
        assert validate_field_value("Reporting timestamp", "bad-date") == "INVALID_DATE_FORMAT"

    def test_currency_field(self):
        assert validate_field_value("Principal amount currency", "EUR") is None
        assert validate_field_value("Principal amount currency", "XYZ") == "UNKNOWN_CURRENCY_CODE"

    def test_boolean_field(self):
        assert validate_field_value("Availability for collateral reuse", "true") is None
        assert validate_field_value("Availability for collateral reuse", "maybe") == "INVALID_BOOLEAN_FORMAT"

    def test_unknown_field(self):
        assert validate_field_value("Unknown field", "anything") is None

    def test_empty_value(self):
        assert validate_field_value("Reporting counterparty", "") is None


class TestGetFieldType:
    def test_known_field(self):
        assert get_field_type("Reporting counterparty") == "lei"
        assert get_field_type("Reporting timestamp") == "datetime"
        assert get_field_type("Principal amount currency") == "currency"

    def test_unknown_field(self):
        assert get_field_type("Unknown field") is None
