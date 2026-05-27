from urllib.parse import urlparse


def is_public_callback_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    hostname = parsed.hostname or ""
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}
    return hostname not in blocked_hosts and not hostname.endswith(".local")
