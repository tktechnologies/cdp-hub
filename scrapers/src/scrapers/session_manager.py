"""Session health tracking and TTL management for browser sessions."""

from datetime import UTC, datetime, timedelta

import structlog

from src.config import settings
from src.models.schemas import SiteId

logger = structlog.get_logger()


class SessionManager:
    """Tracks browser session health across all sites.

    Responsibilities:
    - Track last successful login time per site
    - Determine if a session needs re-authentication based on TTL
    - Track consecutive failures for alerting
    - Clean up expired state files
    """

    def __init__(self) -> None:
        self._sessions: dict[SiteId, SessionInfo] = {}

    def record_login(self, site_id: SiteId) -> None:
        """Record a successful login for a site."""
        info = self._get_or_create(site_id)
        info.last_login = datetime.now(UTC)
        info.is_valid = True
        info.consecutive_failures = 0
        logger.info("Session login recorded", site=site_id.value)

    def record_success(self, site_id: SiteId) -> None:
        """Record a successful scrape (session still valid)."""
        info = self._get_or_create(site_id)
        info.last_success = datetime.now(UTC)
        info.consecutive_failures = 0

    def record_failure(self, site_id: SiteId, error: str) -> None:
        """Record a scrape failure."""
        info = self._get_or_create(site_id)
        info.consecutive_failures += 1
        info.last_error = error
        logger.warning(
            "Session failure recorded",
            site=site_id.value,
            consecutive_failures=info.consecutive_failures,
            error=error,
        )

    def is_session_expired(self, site_id: SiteId) -> bool:
        """Check if session TTL has been exceeded."""
        info = self._sessions.get(site_id)
        if not info or not info.last_login:
            return True
        ttl = timedelta(hours=settings.session_ttl_hours)
        return datetime.now(UTC) - info.last_login > ttl

    def should_alert(self, site_id: SiteId, threshold: int = 3) -> bool:
        """Check if consecutive failures warrant an alert."""
        info = self._sessions.get(site_id)
        return info is not None and info.consecutive_failures >= threshold

    def get_all_status(self) -> dict[SiteId, dict]:
        """Get status summary for all tracked sites."""
        return {
            site_id: {
                "is_valid": info.is_valid,
                "last_login": info.last_login.isoformat() if info.last_login else None,
                "last_success": info.last_success.isoformat() if info.last_success else None,
                "consecutive_failures": info.consecutive_failures,
                "session_expired": self.is_session_expired(site_id),
            }
            for site_id, info in self._sessions.items()
        }

    def invalidate_session(self, site_id: SiteId) -> None:
        """Force-invalidate a session (e.g., after auth failure)."""
        info = self._get_or_create(site_id)
        info.is_valid = False
        # Delete state file
        state_file = settings.browser_state_dir / f"{site_id.value}_state.json"
        if state_file.exists():
            state_file.unlink()
            logger.info("Session state file deleted", site=site_id.value)

    def _get_or_create(self, site_id: SiteId) -> "SessionInfo":
        if site_id not in self._sessions:
            self._sessions[site_id] = SessionInfo()
        return self._sessions[site_id]


class SessionInfo:
    """Internal state for a single site session."""

    def __init__(self) -> None:
        self.is_valid: bool = False
        self.last_login: datetime | None = None
        self.last_success: datetime | None = None
        self.last_error: str = ""
        self.consecutive_failures: int = 0


# Singleton
session_manager = SessionManager()
