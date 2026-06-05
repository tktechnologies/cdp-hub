from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()


def _sync_database_url(url: str) -> str:
    """Alembic runs on a sync engine; production uses psycopg (not asyncpg)."""
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+asyncpg://"):
        url = "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
    elif not url.startswith("postgresql+psycopg://"):
        return url

    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    flat = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}
    if "ssl" in flat and "sslmode" not in flat:
        flat["sslmode"] = flat.pop("ssl")
    if flat.get("sslmode") in ("true", "True", "1"):
        flat["sslmode"] = "require"
    return urlunparse(parsed._replace(query=urlencode(flat)))


config.set_main_option("sqlalchemy.url", _sync_database_url(settings.database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_database_url(settings.database_url),
        target_metadata=target_metadata,
        version_table="muvstok_alembic_version",
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="muvstok_alembic_version",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sqlalchemy_url = config.get_main_option("sqlalchemy.url")
    if sqlalchemy_url is None:
        raise RuntimeError("Missing sqlalchemy.url for Alembic migrations")

    connectable = create_engine(
        sqlalchemy_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
