"""Tests for proxy rotation helpers."""

import pytest

from src.config import settings
from src.utils.proxy_manager import ProxyEndpoint, ProxyManager, reset_proxy_manager


def test_proxy_endpoint_parses_authenticated_url() -> None:
    endpoint = ProxyEndpoint.from_url("http://user:pass@20.1.2.3:3128")

    assert endpoint.server == "http://20.1.2.3:3128"
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


def test_proxy_manager_round_robin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    manager = ProxyManager(
        [
            "http://20.1.2.3:3128",
            "http://20.1.2.4:3128",
            "http://20.1.2.5:3128",
        ]
    )

    assert manager.next_proxy().server == "http://20.1.2.3:3128"
    assert manager.next_proxy().server == "http://20.1.2.4:3128"
    assert manager.next_proxy().server == "http://20.1.2.5:3128"
    assert manager.next_proxy().server == "http://20.1.2.3:3128"


def test_proxy_manager_disabled_without_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "proxy_rotation_enabled", False)
    manager = ProxyManager(["http://20.1.2.3:3128"])

    assert manager.next_proxy() is None


def teardown_function() -> None:
    reset_proxy_manager()
