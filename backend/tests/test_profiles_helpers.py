"""Unit tests for profile helper functions in app.api.profiles.

Tests cover:
- _title_case_name: name normalization for LinkedIn-imported names
- _parse_graduation_year: best-effort year extraction from PDL/Exa date strings
"""

import os

import pytest

os.environ["DEBUG"] = "false"

from app.api.profiles import _parse_graduation_year, _title_case_name  # noqa: E402


# ---------------------------------------------------------------------------
# _title_case_name
# ---------------------------------------------------------------------------


class TestTitleCaseName:
    """Tests for _title_case_name used when normalizing LinkedIn names."""

    def test_lowercased_full_name_is_title_cased(self):
        assert _title_case_name("aleksandar ilijevski") == "Aleksandar Ilijevski"

    def test_already_title_cased_name_unchanged(self):
        assert _title_case_name("Aleksandar Ilijevski") == "Aleksandar Ilijevski"

    def test_all_caps_name_is_title_cased(self):
        assert _title_case_name("JANE DOE") == "Jane Doe"

    def test_single_word_name_is_title_cased(self):
        assert _title_case_name("alice") == "Alice"

    def test_leading_and_trailing_whitespace_is_stripped(self):
        assert _title_case_name("  bob smith  ") == "Bob Smith"

    def test_three_part_name(self):
        result = _title_case_name("mary ann jones")
        assert result == "Mary Ann Jones"

    def test_hyphenated_name_each_part_capitalized(self):
        result = _title_case_name("anne-marie dupont")
        assert result == "Anne-Marie Dupont"


# ---------------------------------------------------------------------------
# _parse_graduation_year
# ---------------------------------------------------------------------------


class TestParseGraduationYear:
    """Tests for _parse_graduation_year used when parsing PDL/Exa education data."""

    def test_returns_none_for_none_input(self):
        assert _parse_graduation_year(None) is None

    def test_returns_none_for_empty_string(self):
        assert _parse_graduation_year("") is None

    def test_returns_none_for_whitespace_only(self):
        assert _parse_graduation_year("   ") is None

    def test_parses_four_digit_year(self):
        assert _parse_graduation_year("2026") == 2026

    def test_parses_year_month_format(self):
        assert _parse_graduation_year("2024-05") == 2024

    def test_parses_full_date_string(self):
        assert _parse_graduation_year("2023-06-15") == 2023

    def test_returns_none_for_year_below_1900(self):
        assert _parse_graduation_year("1899") is None

    def test_returns_none_for_year_above_2100(self):
        assert _parse_graduation_year("2101") is None

    def test_boundary_year_1900_is_accepted(self):
        assert _parse_graduation_year("1900") == 1900

    def test_boundary_year_2100_is_accepted(self):
        assert _parse_graduation_year("2100") == 2100

    def test_returns_none_for_non_numeric_string(self):
        assert _parse_graduation_year("present") is None

    def test_returns_none_for_partial_numeric_string(self):
        assert _parse_graduation_year("20ab") is None

    def test_strips_whitespace_before_parsing(self):
        assert _parse_graduation_year("  2025  ") == 2025
