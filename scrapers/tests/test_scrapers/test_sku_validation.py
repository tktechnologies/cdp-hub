"""Tests for SKU normalization and validation logic."""

from src.scrapers.base import BaseScraper


class TestSKUValidation:
    """Test exact SKU match validation."""

    def test_exact_match_identical(self):
        assert BaseScraper.validate_exact_match("A0001234567", "A0001234567") is True

    def test_exact_match_with_spaces(self):
        assert BaseScraper.validate_exact_match("A000 123 4567", "A0001234567") is True

    def test_exact_match_with_hyphens(self):
        assert BaseScraper.validate_exact_match("A000-1234-567", "A0001234567") is True

    def test_exact_match_case_insensitive(self):
        assert BaseScraper.validate_exact_match("a0001234567", "A0001234567") is True

    def test_no_match_different_codes(self):
        assert BaseScraper.validate_exact_match("A0001234567", "B0001234567") is False

    def test_no_match_partial(self):
        assert BaseScraper.validate_exact_match("A000123", "A0001234567") is False

    def test_no_match_similar(self):
        assert BaseScraper.validate_exact_match("A0001234567", "A0001234568") is False
