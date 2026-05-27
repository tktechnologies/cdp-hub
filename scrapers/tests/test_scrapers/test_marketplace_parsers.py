"""Focused parser tests for marketplace scrapers."""

from src.models.schemas import Currency
from src.scrapers.ebay import EbayScraper
from src.scrapers.melibox import MeliboxScraper
from src.scrapers.pecadireta import PecaDiretaScraper


def test_ebay_brl_dot_decimal_price() -> None:
    price, currency = EbayScraper._parse_ebay_price("R$293.34")

    assert price == 293.34
    assert currency == Currency.BRL


def test_ebay_brl_comma_decimal_price() -> None:
    price, currency = EbayScraper._parse_ebay_price("R$ 2.242,56")

    assert price == 2242.56
    assert currency == Currency.BRL


def test_ebay_usd_price_with_thousands_separator() -> None:
    price, currency = EbayScraper._parse_ebay_price("US $1,234.56")

    assert price == 1234.56
    assert currency == Currency.USD


def test_pecadireta_detects_sku_in_title() -> None:
    assert PecaDiretaScraper._contains_sku("TRANSMISS - 06K907811B", "06K907811B")


def test_pecadireta_does_not_treat_query_string_as_product_sku() -> None:
    href = "/procurar/pecas?query=06K907811B&page=1&obsoleto=0"

    assert not PecaDiretaScraper._contains_sku_in_path(href, "06K907811B")


def test_pecadireta_extracts_sku_from_product_path() -> None:
    href = "https://www.pecadireta.com.br/produto/volkswagen/5u6867287y20?obsoleto=0"

    assert PecaDiretaScraper._sku_from_product_path(href) == "5U6867287Y20"


def test_melibox_extracts_candidate_sku() -> None:
    text = "Produto ativo REF 06K907811B vendido no Mercado Livre"

    assert MeliboxScraper._extract_candidate_sku(text) == "06K907811B"
