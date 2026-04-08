"""
Tests for per-field configurable numeric tolerances.
"""

import pytest
from app.services.tolerances import (
    get_tolerance,
    FIELD_TOLERANCES,
    OBLIGATION_DEFAULTS,
    DEFAULT_TOLERANCE,
)


class TestGetTolerance:
    def test_known_field(self):
        """Known fields should return their specific tolerance."""
        assert get_tolerance("Principal amount on value date", "M") == 0.01
        assert get_tolerance("Fixed rate", "M") == 0.0001

    def test_case_insensitive(self):
        """Field lookup should be case-insensitive."""
        assert get_tolerance("PRINCIPAL AMOUNT ON VALUE DATE", "M") == 0.01
        assert get_tolerance("principal amount on value date", "M") == 0.01

    def test_obligation_fallback(self):
        """Unknown fields should fall back to obligation-level default."""
        assert get_tolerance("some unknown field", "M") == OBLIGATION_DEFAULTS["M"]
        assert get_tolerance("some unknown field", "C") == OBLIGATION_DEFAULTS["C"]
        assert get_tolerance("some unknown field", "O") == OBLIGATION_DEFAULTS["O"]

    def test_default_fallback(self):
        """Unknown field with unknown obligation should return DEFAULT_TOLERANCE."""
        assert get_tolerance("unknown field", "-") == DEFAULT_TOLERANCE
        assert get_tolerance("unknown field", "X") == DEFAULT_TOLERANCE

    def test_field_overrides_obligation(self):
        """Per-field tolerance should override obligation-level default."""
        # principal amount has tolerance 0.01, but M obligation default is 0.0001
        tol = get_tolerance("Principal amount on value date", "M")
        assert tol == 0.01  # field-specific, not obligation default

    def test_all_configured_fields_are_positive(self):
        """All configured tolerances should be positive."""
        for field, tol in FIELD_TOLERANCES.items():
            assert tol > 0, f"Tolerance for '{field}' should be positive"

    def test_margin_fields(self):
        """Margin fields should have configured tolerances."""
        assert get_tolerance("Value of initial margin posted", "M") == 0.01
        assert get_tolerance("Value of variation margin posted", "M") == 0.01

    def test_rate_fields(self):
        """Rate fields should have tight tolerances."""
        assert get_tolerance("Fixed rate", "M") == 0.0001
        assert get_tolerance("Cash reinvestment rate", "M") == 0.0001
        assert get_tolerance("Haircut or margin", "M") == 0.0001
