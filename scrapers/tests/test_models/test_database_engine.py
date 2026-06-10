"""Tests for database engine configuration."""

from sqlalchemy.pool import NullPool

from src.models.database import build_engine_options, normalize_asyncpg_url


def test_sqlite_engine_uses_default_options() -> None:
    options = build_engine_options("sqlite+aiosqlite:///:memory:", "local")

    assert options == {"echo": False}


def test_local_postgres_engine_uses_bounded_pool() -> None:
    options = build_engine_options("postgresql+asyncpg://user:pass@host/db", "local")

    assert options["pool_size"] == 5
    assert options["max_overflow"] == 10
    assert "poolclass" not in options


def test_celery_postgres_engine_disables_pooling() -> None:
    options = build_engine_options("postgresql+asyncpg://user:pass@host/db", "celery")

    assert options["poolclass"] is NullPool
    assert "pool_size" not in options
    assert "max_overflow" not in options


def test_asyncpg_ssl_query_moves_to_connect_args() -> None:
    url, connect_args = normalize_asyncpg_url("postgresql+asyncpg://user:pass@host/db?ssl=require")

    assert url == "postgresql+asyncpg://user:pass@host/db"
    assert connect_args == {"ssl": True}


def test_asyncpg_sslmode_query_moves_to_connect_args() -> None:
    url, connect_args = normalize_asyncpg_url(
        "postgresql+asyncpg://user:pass@host/db?sslmode=require&application_name=cdp"
    )

    assert url == "postgresql+asyncpg://user:pass@host/db?application_name=cdp"
    assert connect_args == {"ssl": True}
