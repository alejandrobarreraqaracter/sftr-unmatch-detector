"""
Tests for the tabular CSV parser.
"""

import pytest
from app.services.file_parser import parse_tabular_csv
from app.services.column_mapping import normalize_col, resolve_alias, build_column_index


# ── normalize_col ────────────────────────────────────────────────────────────

class TestNormalizeCol:
    def test_basic(self):
        assert normalize_col("Reporting timestamp") == "reporting_timestamp"

    def test_special_chars(self):
        assert normalize_col("Principal amount (Leg 2)") == "principal_amount_leg_2"

    def test_collapse_underscores(self):
        assert normalize_col("some___field") == "some_field"

    def test_strip_edges(self):
        assert normalize_col("  _hello_ ") == "hello"

    def test_uppercase(self):
        assert normalize_col("SFT_Type") == "sft_type"


# ── resolve_alias ────────────────────────────────────────────────────────────

class TestResolveAlias:
    def test_known_alias(self):
        assert resolve_alias("rep_timestamp") == "reporting_timestamp"
        assert resolve_alias("principal_amount") == "principal_amount_on_value_date"
        assert resolve_alias("isin") == "security_identifier"

    def test_unknown_returns_self(self):
        assert resolve_alias("some_unknown_field") == "some_unknown_field"

    def test_metadata_aliases(self):
        assert resolve_alias("action") == "action_type"
        assert resolve_alias("type_sft") == "sft_type"


# ── build_column_index ───────────────────────────────────────────────────────

class TestBuildColumnIndex:
    def test_basic_columns(self):
        columns = [
            "UTI", "SFT_Type",
            "Reporting timestamp_CP1", "Reporting timestamp_CP2",
        ]
        cp1, cp2, norm = build_column_index(columns)
        assert "reporting_timestamp" in cp1
        assert "reporting_timestamp" in cp2
        assert "uti" in norm
        assert "sft_type" in norm

    def test_alias_resolution(self):
        columns = ["Rep_Timestamp_CP1", "Rep_Timestamp_CP2"]
        cp1, cp2, _ = build_column_index(columns)
        assert "reporting_timestamp" in cp1
        assert "reporting_timestamp" in cp2

    def test_no_cp_suffix(self):
        columns = ["UTI", "SFT_Type"]
        cp1, cp2, norm = build_column_index(columns)
        assert len(cp1) == 0
        assert len(cp2) == 0
        assert "uti" in norm


# ── parse_tabular_csv ────────────────────────────────────────────────────────

class TestParseTabularCSV:
    def test_basic_parse(self, minimal_csv_bytes):
        rows = parse_tabular_csv(minimal_csv_bytes)
        assert len(rows) == 1
        row = rows[0]
        assert row["uti"] == "UTI001"
        assert row["sft_type"] == "Repo"
        assert row["action_type"] == "NEWT"

    def test_emisor_receptor_fields(self, minimal_csv_bytes):
        rows = parse_tabular_csv(minimal_csv_bytes)
        row = rows[0]
        assert "reporting timestamp" in row["emisor"]
        assert "reporting timestamp" in row["receptor"]
        assert row["emisor"]["reporting timestamp"] == "2024-03-15T09:32:00Z"
        assert row["receptor"]["reporting timestamp"] == "2024-03-15T09:32:00Z"

    def test_numeric_mismatch(self, minimal_csv_bytes):
        rows = parse_tabular_csv(minimal_csv_bytes)
        row = rows[0]
        assert row["emisor"]["principal amount on value date"] == "5000000.00"
        assert row["receptor"]["principal amount on value date"] == "4950000.00"

    def test_sample_csv(self, sample_csv_bytes):
        rows = parse_tabular_csv(sample_csv_bytes)
        assert len(rows) == 5
        # All rows should have UTIs
        for row in rows:
            assert row["uti"].startswith("UTI2024SANTANDER")
            assert row["sft_type"] == "Repo"
            assert row["action_type"] == "NEWT"

    def test_empty_csv(self):
        header = "UTI;SFT_Type;Action_Type"
        content = header.encode("utf-8")
        rows = parse_tabular_csv(content)
        assert len(rows) == 0

    def test_missing_metadata_defaults(self):
        header = "Reporting timestamp_CP1;Reporting timestamp_CP2"
        row_data = "2024-01-01;2024-01-01"
        content = f"{header}\n{row_data}".encode("utf-8")
        rows = parse_tabular_csv(content)
        assert len(rows) == 1
        assert rows[0]["sft_type"] == "Repo"  # default
        assert rows[0]["action_type"] == "NEWT"  # default

    def test_alias_columns_in_csv(self):
        header = "UTI;Rep_Timestamp_CP1;Rep_Timestamp_CP2"
        row_data = "UTI999;2024-06-01;2024-06-02"
        content = f"{header}\n{row_data}".encode("utf-8")
        rows = parse_tabular_csv(content)
        assert len(rows) == 1
        assert "reporting timestamp" in rows[0]["emisor"]
        assert rows[0]["emisor"]["reporting timestamp"] == "2024-06-01"
        assert rows[0]["receptor"]["reporting timestamp"] == "2024-06-02"
