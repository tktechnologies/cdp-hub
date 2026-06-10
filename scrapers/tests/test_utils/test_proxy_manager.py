"""Tests for proxy rotation helpers."""

import pytest

from src.config import settings
from src.utils.proxy_manager import (
    ProxyEndpoint,
    ProxyManager,
    get_proxy_manager,
    reset_proxy_manager,
)


def test_proxy_endpoint_parses_authenticated_url() -> None:
    endpoint = ProxyEndpoint.from_url("http://user:pass@20.1.2.3:3128")

    assert endpoint.server == "http://20.1.2.3:3128"
    assert endpoint.host == "20.1.2.3"
    assert endpoint.username == "user"
    assert endpoint.password == "pass"


def test_proxy_endpoint_rejects_invalid_url() -> None:
    with pytest.raises(ValueError):
        ProxyEndpoint.from_url("20.1.2.3:3128")


def test_proxy_to_playwright_includes_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_bypass", "localhost,127.0.0.1")

    endpoint = ProxyEndpoint.from_url("http://20.1.2.3:3128")

    assert endpoint.to_playwright() == {
        "server": "http://20.1.2.3:3128",
        "bypass": "localhost,127.0.0.1",
    }


def test_proxy_to_httpx_url_preserves_authenticated_proxy() -> None:
    endpoint = ProxyEndpoint.from_url("http://user:pa ss@20.1.2.3:3128")

    assert endpoint.to_httpx_url() == "http://user:pa%20ss@20.1.2.3:3128"


def test_proxy_manager_strict_alternation_per_sku(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    monkeypatch.setattr(settings, "proxy_strict_alternation", True)
    monkeypatch.setattr(settings, "proxy_affinity_enabled", False)
    manager = ProxyManager(
        [
            "http://20.1.2.3:3128",
            "http://20.1.2.4:3128",
        ]
    )

    sku1_gm = manager.begin_sku("ABC123", "")
    sku1_ml = manager.proxy_for_current_scope("ml")
    manager.clear_sku()
    sku2_gm = manager.begin_sku("XYZ999", "")
    manager.clear_sku()
    sku3_gm = manager.begin_sku("DEF456", "")

    assert sku1_gm is not None
    assert sku1_ml is not None
    assert sku2_gm is not None
    assert sku3_gm is not None
    assert sku1_gm.host == "20.1.2.3"
    assert sku1_ml.host == "20.1.2.3"
    assert sku2_gm.host == "20.1.2.4"
    assert sku3_gm.host == "20.1.2.3"


def test_proxy_manager_without_sku_scope_alternates_per_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    monkeypatch.setattr(settings, "proxy_strict_alternation", True)
    manager = ProxyManager(
        [
            "http://20.1.2.3:3128",
            "http://20.1.2.4:3128",
        ]
    )

    first = manager.select_proxy_for_search("gm")
    second = manager.select_proxy_for_search("ml")
    third = manager.select_proxy_for_search("vw")

    assert first.host == "20.1.2.3"
    assert second.host == "20.1.2.4"
    assert third.host == "20.1.2.3"


def test_proxy_manager_round_robin_three_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    monkeypatch.setattr(settings, "proxy_strict_alternation", True)
    manager = ProxyManager(
        [
            "http://20.1.2.3:3128",
            "http://20.1.2.4:3128",
            "http://20.1.2.5:3128",
        ]
    )

    hosts = [manager.next_proxy().host for _ in range(4)]
    assert hosts == ["20.1.2.3", "20.1.2.4", "20.1.2.5", "20.1.2.3"]


def test_proxy_manager_site_affinity_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    monkeypatch.setattr(settings, "proxy_strict_alternation", False)
    monkeypatch.setattr(settings, "proxy_affinity_enabled", True)
    manager = ProxyManager(
        [
            "http://20.1.2.3:3128",
            "http://20.1.2.4:3128",
        ]
    )

    gm_proxy = manager.select_proxy_for_search("gm")
    ml_proxy = manager.select_proxy_for_search("ml")

    assert gm_proxy is not None
    assert ml_proxy is not None
    assert gm_proxy.server == "http://20.1.2.3:3128"
    assert ml_proxy.server == "http://20.1.2.4:3128"
    assert manager.select_proxy_for_search("gm").server == gm_proxy.server


def test_proxy_manager_disabled_without_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", False)
    manager = ProxyManager(["http://20.1.2.3:3128"])

    assert manager.select_proxy_for_search("gm") is None


def test_proxy_manager_fail_closed_without_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    monkeypatch.setattr(settings, "proxy_urls", [])
    monkeypatch.setattr(settings, "proxy_fail_closed", True)

    with pytest.raises(RuntimeError, match="no proxy URLs"):
        get_proxy_manager()


def teardown_function() -> None:
    reset_proxy_manager()
