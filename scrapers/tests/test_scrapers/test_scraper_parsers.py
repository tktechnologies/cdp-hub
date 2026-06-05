"""Per-scraper parser and contract smoke tests."""

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId, SiteResult
from src.scrapers.base import BaseScraper
from src.scrapers.ebay import EbayScraper
from src.scrapers.eu_imports import EUImportsScraper
from src.scrapers.gm import GMScraper
from src.scrapers.goparts import GoPartsScraper
from src.scrapers.melibox import MeliboxScraper
from src.scrapers.mercadolivre import MercadoLivreScraper
from src.scrapers.pecadireta import PecaDiretaScraper
from src.scrapers.procurapecas import ProcuraPecasScraper
from src.scrapers.vw import VWScraper


def _ml_part(condition: ItemCondition) -> PartResult:
    return PartResult(
        sku_searched="06K907811B",
        sku_found="06K907811B",
        exact_match=True,
        site=SiteId.MERCADO_LIVRE,
        site_name="Mercado Livre",
        price=100.0,
        currency=Currency.BRL,
        condition=condition,
        availability="Disponível",
        seller_name="",
        product_url="",
        origin="Brasil",
        raw_title="Sensor 06K907811B",
    )


def test_gm_parses_brazilian_price() -> None:
    assert GMScraper._parse_price("R$ 1.234,56") == 1234.56


def test_base_scraper_extracts_brazil_uf_and_cnpj() -> None:
    assert BaseScraper.extract_brazil_uf("Macapá - AP") == "AP"
    assert BaseScraper.extract_brazil_uf("São Paulo") == "SP"
    assert BaseScraper.extract_cnpj_digits("CNPJ 05.788.992/0001-87") == "05788992000187"


def test_mercado_livre_filters_used_items() -> None:
    results = MercadoLivreScraper()._filter_new_only(
        [_ml_part(ItemCondition.NEW), _ml_part(ItemCondition.USED)]
    )

    assert len(results) == 1
    assert results[0].condition == ItemCondition.NEW


class _FakeMLElement:
    def __init__(self, text: str = "", attrs: dict[str, str] | None = None) -> None:
        self._text = text
        self._attrs = attrs or {}

    async def inner_text(self) -> str:
        return self._text

    async def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)


class _FakeMLCard:
    def __init__(
        self,
        *,
        text: str,
        title: str,
        product_url: str,
        price: str = "100",
        condition: str = "Novo",
    ) -> None:
        self._text = text
        self._title = _FakeMLElement(title)
        self._link = _FakeMLElement(attrs={"href": product_url})
        self._price = _FakeMLElement(price)
        self._condition = _FakeMLElement(condition)

    async def inner_text(self) -> str:
        return self._text

    async def query_selector(self, selector: str) -> _FakeMLElement | None:
        if "andes-money-amount__fraction" in selector:
            return self._price
        if "condition" in selector or "poly-component__sold-count" in selector:
            return self._condition
        if "ui-search-link" in selector or "href*='MLB'" in selector:
            return self._link
        if "title" in selector:
            return self._title
        return None


async def test_mercado_livre_matches_sku_in_card_text_or_url() -> None:
    card = _FakeMLCard(
        text="Farol esquerdo Fiat Palio codigo 51766536 Novo",
        title="Farol esquerdo Fiat Palio",
        product_url="https://produto.mercadolivre.com.br/MLB-123-farol-51766536",
    )

    result = await MercadoLivreScraper()._extract_card_result(card, "51766536")

    assert result is not None
    assert result.exact_match
    assert result.sku_found == "51766536"


async def test_mercado_livre_rejects_near_sku_without_exact_evidence() -> None:
    card = _FakeMLCard(
        text="Farol esquerdo Fiat Palio codigo 51766537 Novo",
        title="Farol esquerdo Fiat Palio",
        product_url="https://produto.mercadolivre.com.br/MLB-123-farol",
    )

    result = await MercadoLivreScraper()._extract_card_result(card, "51766536")

    assert result is not None
    assert not result.exact_match
    assert result.sku_found == ""


def test_mercado_livre_sku_evidence_allows_variant_suffix_but_not_longer_sku() -> None:
    scraper = MercadoLivreScraper()

    assert scraper._contains_sku_evidence("51766536", "Número de peça 51766536_1")
    assert not scraper._contains_sku_evidence("51766536", "Número de peça 517665360")


def test_mercado_livre_parses_poly_card_price_parts() -> None:
    price = MercadoLivreScraper._parse_card_price("1.801", "11", "1801 reais", "")

    assert price == 1801.11


def test_mercado_livre_parses_price_from_aria_label_when_fraction_missing() -> None:
    price = MercadoLivreScraper._parse_card_price("", "", "599 reais com 32 centavos", "")

    assert price == 599.0


def test_mercado_livre_parses_price_from_card_text_fallback() -> None:
    price = MercadoLivreScraper._parse_card_price("", "", "", "Oferta R$ 1.234,56 à vista")

    assert price == 1234.56


class _FakeMLBlockedPage:
    def __init__(self, body: str, *, has_challenge: bool = False) -> None:
        self._body = body
        self._has_challenge = has_challenge

    async def inner_text(self, selector: str) -> str:
        assert selector == "body"
        return self._body

    async def query_selector(self, selector: str):
        return object() if self._has_challenge and "challenge" in selector else None


async def test_mercado_livre_detects_security_verification_as_blocked() -> None:
    page = _FakeMLBlockedPage("Verificação de segurança. Por favor, tente novamente.")

    assert await MercadoLivreScraper()._detect_blocked(page) is True


async def test_mercado_livre_detects_challenge_selector_as_blocked() -> None:
    page = _FakeMLBlockedPage("", has_challenge=True)

    assert await MercadoLivreScraper()._detect_blocked(page) is True


class _FakeLocator:
    def __init__(self, count: int = 0, visible: list[bool] | None = None) -> None:
        self._count = count
        self._visible = visible or []

    async def count(self) -> int:
        return self._count

    def nth(self, index: int) -> "_FakeLocator":
        return _FakeLocator(1, [self._visible[index]])

    async def is_visible(self, timeout: int = 500) -> bool:
        return self._visible[0]


class _FakeEbayPage:
    def __init__(self, body: str, result_count: int, challenge_visible: list[bool]) -> None:
        self._body = body
        self._result_count = result_count
        self._challenge_visible = challenge_visible

    async def inner_text(self, selector: str) -> str:
        assert selector == "body"
        return self._body

    def locator(self, selector: str) -> _FakeLocator:
        if "srp-results" in selector or "srp-river-results" in selector:
            return _FakeLocator(self._result_count)
        return _FakeLocator(len(self._challenge_visible), self._challenge_visible)


async def test_ebay_detector_ignores_hidden_challenge_markup_when_results_are_visible() -> None:
    page = _FakeEbayPage("captcha", result_count=20, challenge_visible=[False])

    assert not await EbayScraper()._detect_blocked(page)


async def test_ebay_detector_blocks_visible_challenge_page() -> None:
    page = _FakeEbayPage(
        "Pardon our interruption",
        result_count=0,
        challenge_visible=[True],
    )

    assert await EbayScraper()._detect_blocked(page)


def test_vw_normalizes_and_parses_price() -> None:
    scraper = VWScraper()

    assert scraper._normalize_sku("06K 907-811.B") == "06K907811B"
    assert scraper._parse_price("R$ 293,34") == 293.34
    assert scraper._contains_sku("Suporte VW 5U6867287Y20", "5U6867287Y20")


def test_eu_imports_parses_usd_and_eur_prices() -> None:
    assert EUImportsScraper._parse_price_and_currency("292.13 $") == (292.13, Currency.USD)
    assert EUImportsScraper._parse_price_and_currency("292,13 €") == (292.13, Currency.EUR)


def test_goparts_parses_brazilian_price() -> None:
    assert GoPartsScraper._parse_price("R$ 1.234,56") == 1234.56


def test_procurapecas_parses_brazilian_price() -> None:
    assert ProcuraPecasScraper._parse_price("R$ 1.234,56") == 1234.56


def test_pecadireta_parses_brazilian_price() -> None:
    assert PecaDiretaScraper._parse_price("R$ 1.234,56") == 1234.56


def test_melibox_parses_brazilian_price_and_exact_sku() -> None:
    assert MeliboxScraper._parse_price("R$ 1.234,56") == 1234.56
    assert MeliboxScraper._contains_sku("Anuncio Mercado Livre 06K 907-811.B", "06K907811B")


def test_melibox_first_brl_price_token() -> None:
    assert MeliboxScraper._first_brl_price_token("Coluna R$ 1.234,56 fim") == "1.234,56"
    assert MeliboxScraper._first_brl_price_token("x R$293,34 y") == "293,34"
    assert MeliboxScraper._parse_price(MeliboxScraper._first_brl_price_token("R$ 99,00")) == 99.0


def test_melibox_price_column_without_currency_prefix() -> None:
    cells = [
        "3",
        "Farol Esquerdo Strada 51766536 Esquerdo/motorista",
        "",
        "5 %",
        "",
        "568,83",
        "Places FLEX",
        "",
        "",
    ]

    token = MeliboxScraper._price_token_from_cells_or_text(
        cells,
        "3 Farol Esquerdo Strada 51766536 Esquerdo/motorista 5 % 568,83 Places FLEX",
    )

    assert token == "568,83"
    assert MeliboxScraper._parse_price(token) == 568.83


def test_melibox_work_page_and_login_urls_from_credentials() -> None:
    scraper = MeliboxScraper()
    scraper._credentials = {"url": "https://app.melibox.com.br", "username": "u", "password": "p"}
    assert scraper._login_url() == "https://app.melibox.com.br"
    assert scraper._work_page_url() == "https://app.melibox.com.br/advProductPosition"

    scraper._credentials = {
        "url": "https://app.melibox.com.br/advProductPosition",
        "username": "u",
        "password": "p",
    }
    assert scraper._login_url() == "https://app.melibox.com.br"
    assert scraper._work_page_url() == "https://app.melibox.com.br/advProductPosition"


async def test_melibox_maps_blocked_login_to_blocked_status(monkeypatch) -> None:
    async def fake_base_scrape(self, sku: str, brand: str = "") -> SiteResult:
        return SiteResult(
            site=self.site_id,
            site_name=self.site_name,
            status="error",
            error_message="Authentication failed",
            search_time_ms=123,
        )

    monkeypatch.setattr(BaseScraper, "scrape_sku", fake_base_scrape)
    scraper = MeliboxScraper()
    scraper._last_login_blocked = True

    result = await scraper.scrape_sku("51766536")

    assert result.status == "blocked"
    assert result.error_message == "Melibox login entry returned 403/access block"
