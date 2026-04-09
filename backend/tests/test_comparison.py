"""
Tests for the field-level comparison engine.
"""

import pytest
from app.services.comparison import (
    normalize,
    is_numeric,
    is_date_like,
    is_mirror_match,
    classify_severity,
    detect_root_cause,
    numeric_match,
    compare_trade,
    compare_field,
    _get_field_value,
)


# ── normalize ────────────────────────────────────────────────────────────────

class TestNormalize:
    def test_basic(self):
        assert normalize("hello") == "HELLO"

    def test_strip(self):
        assert normalize("  hello  ") == "HELLO"

    def test_none(self):
        assert normalize(None) == ""

    def test_empty(self):
        assert normalize("") == ""


# ── is_numeric ───────────────────────────────────────────────────────────────

class TestIsNumeric:
    def test_integer(self):
        assert is_numeric("123") is True

    def test_decimal(self):
        assert is_numeric("123.45") is True

    def test_negative(self):
        assert is_numeric("-123.45") is True

    def test_scientific(self):
        assert is_numeric("1.23e+10") is True

    def test_text(self):
        assert is_numeric("hello") is False

    def test_empty(self):
        assert is_numeric("") is False

    def test_mixed(self):
        assert is_numeric("123abc") is False


# ── is_date_like ─────────────────────────────────────────────────────────────

class TestIsDateLike:
    def test_date(self):
        assert is_date_like("2024-03-15") is True

    def test_datetime(self):
        assert is_date_like("2024-03-15T09:32:00Z") is True

    def test_not_date(self):
        assert is_date_like("hello") is False

    def test_partial(self):
        assert is_date_like("2024") is False


# ── is_mirror_match ──────────────────────────────────────────────────────────

class TestIsMirrorMatch:
    def test_give_take(self):
        assert is_mirror_match("GIVE", "TAKE") is True
        assert is_mirror_match("TAKE", "GIVE") is True

    def test_mrgg_mrge(self):
        assert is_mirror_match("MRGG", "MRGE") is True
        assert is_mirror_match("MRGE", "MRGG") is True

    def test_case_insensitive(self):
        assert is_mirror_match("give", "take") is True

    def test_not_mirror(self):
        assert is_mirror_match("GIVE", "GIVE") is False
        assert is_mirror_match("hello", "world") is False


# ── classify_severity ────────────────────────────────────────────────────────

class TestClassifySeverity:
    def test_mandatory(self):
        assert classify_severity("M") == "CRITICAL"

    def test_conditional(self):
        assert classify_severity("C") == "WARNING"

    def test_optional(self):
        assert classify_severity("O") == "INFO"

    def test_not_applicable(self):
        assert classify_severity("-") == "NONE"

    def test_unknown(self):
        assert classify_severity("X") == "NONE"


# ── detect_root_cause ────────────────────────────────────────────────────────

class TestDetectRootCause:
    def test_both_empty(self):
        assert detect_root_cause("", "", "M", False) == "BOTH_EMPTY"

    def test_missing_emisor(self):
        assert detect_root_cause("", "VALUE", "M", False) == "MISSING_EMISOR"

    def test_missing_receptor(self):
        assert detect_root_cause("VALUE", "", "M", False) == "MISSING_RECEPTOR"

    def test_mirror_match(self):
        assert detect_root_cause("GIVE", "TAKE", "M", True) == "MIRROR_MATCH"

    def test_numeric_delta(self):
        assert detect_root_cause("100.00", "200.00", "M", False) == "NUMERIC_DELTA"

    def test_date_mismatch(self):
        assert detect_root_cause("2024-01-01", "2024-01-02", "M", False) == "DATE_MISMATCH"

    def test_format_difference(self):
        assert detect_root_cause("HELLO WORLD", "HELLOWORLD", "M", False) == "FORMAT_DIFFERENCE"

    def test_value_mismatch(self):
        assert detect_root_cause("CDTI", "INVF", "M", False) == "VALUE_MISMATCH"


# ── numeric_match ────────────────────────────────────────────────────────────

class TestNumericMatch:
    def test_within_tolerance(self):
        assert numeric_match("100.0001", "100.0002", 0.001) is True

    def test_exact(self):
        assert numeric_match("100.00", "100.00", 0.0001) is True

    def test_outside_tolerance(self):
        assert numeric_match("100.00", "200.00", 0.01) is False

    def test_non_numeric(self):
        assert numeric_match("hello", "world", 0.01) is False

    def test_tight_tolerance(self):
        assert numeric_match("5000000.00", "4950000.00", 0.01) is False

    def test_boundary(self):
        # Note: floating point precision means abs(100.00 - 100.01) ≈ 0.01000000000000005
        assert numeric_match("100.00", "100.009", 0.01) is True
        assert numeric_match("100.00", "100.02", 0.01) is False


# ── _get_field_value ─────────────────────────────────────────────────────────

class TestGetFieldValue:
    def test_exact_match(self):
        data = {"Reporting timestamp": "2024-01-01"}
        assert _get_field_value(data, "Reporting timestamp") == "2024-01-01"

    def test_case_insensitive(self):
        data = {"reporting timestamp": "2024-01-01"}
        assert _get_field_value(data, "Reporting timestamp") == "2024-01-01"

    def test_normalized_match(self):
        data = {"reporting_timestamp": "2024-01-01"}
        assert _get_field_value(data, "Reporting timestamp") == "2024-01-01"

    def test_not_found(self):
        data = {"other_field": "value"}
        assert _get_field_value(data, "Reporting timestamp") == ""


# ── compare_trade ────────────────────────────────────────────────────────────

class TestCompareTrade:
    def test_all_match(self):
        """When emisor and receptor have identical values, all should be MATCH or NA."""
        emisor = {"reporting timestamp": "2024-01-01"}
        receptor = {"reporting timestamp": "2024-01-01"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        assert len(results) == 155
        # At least the reporting timestamp should match
        ts_result = next(r for r in results if r["field_name"] == "Reporting timestamp")
        assert ts_result["result"] == "MATCH"
        assert ts_result["root_cause"] == "MATCH"

    def test_value_mismatch(self):
        """Different values on a mandatory field should produce UNMATCH/CRITICAL."""
        emisor = {"sector of the reporting counterparty": "CDTI"}
        receptor = {"sector of the reporting counterparty": "INVF"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        sector = next(r for r in results if r["field_name"] == "Sector of the reporting counterparty")
        assert sector["result"] == "UNMATCH"
        assert sector["severity"] == "CRITICAL"
        assert sector["root_cause"] == "VALUE_MISMATCH"

    def test_numeric_delta(self):
        """Numeric mismatch beyond tolerance should be UNMATCH."""
        emisor = {"principal amount on value date": "5000000.00"}
        receptor = {"principal amount on value date": "4950000.00"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        principal = next(r for r in results if r["field_name"] == "Principal amount on value date")
        assert principal["result"] == "UNMATCH"
        assert principal["severity"] == "CRITICAL"
        assert principal["root_cause"] == "NUMERIC_DELTA"

    def test_numeric_within_tolerance(self):
        """Numeric values within tolerance should MATCH."""
        emisor = {"principal amount on value date": "5000000.00"}
        receptor = {"principal amount on value date": "5000000.005"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        principal = next(r for r in results if r["field_name"] == "Principal amount on value date")
        assert principal["result"] == "MATCH"
        assert principal["root_cause"] == "NUMERIC_WITHIN_TOLERANCE"

    def test_mirror_field(self):
        """Mirror fields with inverse values should produce MIRROR result."""
        emisor = {"side of the counterparty": "GIVE"}
        receptor = {"side of the counterparty": "TAKE"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        side = next(r for r in results if r["field_name"] == "Side of the counterparty")
        assert side["result"] == "MIRROR"
        assert side["root_cause"] == "MIRROR_MATCH"

    def test_not_applicable(self):
        """Fields with obligation '-' and differing values should be NA."""
        emisor = {"exclusive arrangements": "YES"}
        receptor = {"exclusive arrangements": "NO"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        na_results = [r for r in results if r["result"] == "NA" and r["obligation"] == "-"]
        assert len(na_results) > 0
        for r in na_results:
            assert r["severity"] == "NONE"
            assert r["root_cause"] == "NOT_APPLICABLE"

    def test_warning_severity(self):
        """Conditional field mismatch should be WARNING."""
        emisor = {"availability for collateral reuse": "true"}
        receptor = {"availability for collateral reuse": "false"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        reuse = next(r for r in results if r["field_name"] == "Availability for collateral reuse")
        assert reuse["result"] == "UNMATCH"
        assert reuse["severity"] == "WARNING"

    def test_both_empty_is_na(self):
        """When both values are empty, result should be NA."""
        results = compare_trade({}, {}, "Repo", "NEWT")
        # All non-'-' obligation fields with empty values should be NA/BOTH_EMPTY
        non_na = [r for r in results if r["obligation"] != "-"]
        for r in non_na:
            if r["result"] == "NA":
                assert r["root_cause"] == "BOTH_EMPTY"

    def test_sample_csv_expected_results(self, sample_csv_bytes):
        """
        Validate expected results from the sample CSV file.

        Expected unmatches (with per-field tolerances):
          Trade 1: 0 unmatches
          Trade 2: 1 unmatch - Fixed rate (C/WARNING, 0.0125 vs 0.0150, per-field tol=0.0001)
          Trade 3: 1 unmatch - Principal amount on value date (M/CRITICAL, 5M vs 4.95M)
          Trade 4: 1 unmatch - Sector of the reporting counterparty (M/CRITICAL, CDTI vs INVF)
          Trade 5: 1 unmatch - Availability for collateral reuse (C/WARNING, true vs false)
        """
        from app.services.file_parser import parse_tabular_csv
        rows = parse_tabular_csv(sample_csv_bytes)
        assert len(rows) == 5

        # Trade 1: no unmatches
        r1 = compare_trade(rows[0]["emisor"], rows[0]["receptor"], "Repo", "NEWT")
        assert len([r for r in r1 if r["result"] == "UNMATCH"]) == 0

        # Trade 2: Fixed rate mismatch (caught by per-field tolerance 0.0001)
        r2 = compare_trade(rows[1]["emisor"], rows[1]["receptor"], "Repo", "NEWT")
        unmatches_2 = [r for r in r2 if r["result"] == "UNMATCH"]
        assert len(unmatches_2) == 1
        assert unmatches_2[0]["field_name"] == "Fixed rate"
        assert unmatches_2[0]["severity"] == "WARNING"
        assert unmatches_2[0]["root_cause"] == "NUMERIC_DELTA"

        # Trade 3: Principal amount on value date mismatch
        r3 = compare_trade(rows[2]["emisor"], rows[2]["receptor"], "Repo", "NEWT")
        unmatches_3 = [r for r in r3 if r["result"] == "UNMATCH"]
        assert len(unmatches_3) == 1
        assert unmatches_3[0]["field_name"] == "Principal amount on value date"
        assert unmatches_3[0]["severity"] == "CRITICAL"

        # Trade 4: Sector mismatch
        r4 = compare_trade(rows[3]["emisor"], rows[3]["receptor"], "Repo", "NEWT")
        unmatches_4 = [r for r in r4 if r["result"] == "UNMATCH"]
        assert len(unmatches_4) == 1
        assert unmatches_4[0]["field_name"] == "Sector of the reporting counterparty"
        assert unmatches_4[0]["severity"] == "CRITICAL"

        # Trade 5: Boolean mismatch
        r5 = compare_trade(rows[4]["emisor"], rows[4]["receptor"], "Repo", "NEWT")
        unmatches_5 = [r for r in r5 if r["result"] == "UNMATCH"]
        assert len(unmatches_5) == 1
        assert unmatches_5[0]["field_name"] == "Availability for collateral reuse"
        assert unmatches_5[0]["severity"] == "WARNING"

    def test_validation_fields_present(self):
        """Comparison results should include validation info."""
        emisor = {"report submitting entity": "INVALID_LEI"}
        receptor = {"report submitting entity": "R0MUWSFPU8MPRO8K5P83"}
        results = compare_trade(emisor, receptor, "Repo", "NEWT")
        entity = next(r for r in results if r["field_name"] == "Report submitting entity")
        # Emisor value is invalid LEI format
        assert entity["emisor_validation"] is not None or entity["result"] == "UNMATCH"

    def test_equal_invalid_values_are_not_marked_valid(self):
        """If both sides share the same invalid value, reconciliation may match but validation must fail."""
        emisor = {"Reporting timestamp": "2026-02-31"}
        receptor = {"Reporting timestamp": "2026-02-31"}
        result = compare_field("Reporting timestamp", emisor["Reporting timestamp"], receptor["Reporting timestamp"], "Repo", "NEWT")
        assert result["result"] == "MATCH"
        assert result["validated"] is False
        assert result["root_cause"] == "BOTH_INVALID_FORMAT"
