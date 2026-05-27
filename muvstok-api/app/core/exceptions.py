class MuvstokError(Exception):
    """Base application exception."""


class QueuePublishError(MuvstokError):
    """Raised when a job cannot be published to Redis."""


class JobNotFoundError(MuvstokError):
    """Raised when a job cannot be found."""


class JobLimitExceededError(MuvstokError):
    """Raised when a submitted job exceeds configured limits."""


class TokenUnavailableError(MuvstokError):
    """Raised when a usable Muvstok token cannot be retrieved or refreshed."""
