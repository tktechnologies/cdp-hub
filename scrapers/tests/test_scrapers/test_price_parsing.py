"""Tests for price parsing functions."""

from src.services.sku_validator import parse_brazilian_price, parse_usd_eur_price


class TestBrazilianPriceParsing:
    """Test R$ price format parsing."""

    def test_standard_format(self):
        assert parse_brazilian_price("R$ 1.234,56") == 1234.56

    def test_no_thousands(self):
        assert parse_brazilian_price("R$ 234,56") == 234.56

    def test_no_decimals(self):
        assert parse_brazilian_price("R$ 1.234") == 1234.0

    def test_large_number(self):
        assert parse_brazilian_price("R$ 12.345.678,90") == 12345678.90

    def test_just_number(self):
        assert parse_brazilian_price("1234,56") == 1234.56

    def test_zero(self):
        assert parse_brazilian_price("R$ 0,00") == 0.0

    def test_empty_string(self):
        assert parse_brazilian_price("") == 0.0

    def test_garbage(self):
        assert parse_brazilian_price("not a price") == 0.0

    def test_with_spaces(self):
        assert parse_brazilian_price("R$  1.234,56 ") == 1234.56


class TestUsdEurPriceParsing:
    """Test USD/EUR price format parsing."""

    def test_usd_format(self):
        assert parse_usd_eur_price("$1,234.56") == 1234.56

    def test_eur_format(self):
        assert parse_usd_eur_price("€1,234.56") == 1234.56

    def test_no_thousands(self):
        assert parse_usd_eur_price("$234.56") == 234.56

    def test_no_symbol(self):
        assert parse_usd_eur_price("1234.56") == 1234.56

    def test_empty(self):
        assert parse_usd_eur_price("") == 0.0
