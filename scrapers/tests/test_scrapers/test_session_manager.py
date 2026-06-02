"""Tests for browser session state management."""

from src.config import settings
from src.models.schemas import SiteId
from src.scrapers.session_manager import SessionManager


def test_invalidate_session_removes_proxy_partitioned_state_files(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "browser_state_dir", tmp_path)
    legacy_state = tmp_path / "ml_state.json"
    proxy_state = tmp_path / "ml_abcdef123456_state.json"
    other_state = tmp_path / "gm_state.json"
    legacy_state.write_text("{}", encoding="utf-8")
    proxy_state.write_text("{}", encoding="utf-8")
    other_state.write_text("{}", encoding="utf-8")

    SessionManager().invalidate_session(SiteId.MERCADO_LIVRE)

    assert not legacy_state.exists()
    assert not proxy_state.exists()
    assert other_state.exists()
