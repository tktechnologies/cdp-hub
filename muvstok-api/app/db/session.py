from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _async_database_url(url: str) -> str:
    """Normalize Azure/KV URLs for SQLAlchemy async psycopg driver."""
    url = url.strip().strip('"').strip("'").replace("\n", "").replace("\r", "")
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
    for token in ("ssl=require", "ssl=true", "ssl=1", "ssl=false", "ssl=0"):
        if token in url:
            url = url.replace(token, token.replace("ssl=", "sslmode=", 1))
    if "ssl=" in url and "sslmode=" not in url:
        url = url.replace("ssl=", "sslmode=", 1)
    # Key Vault values occasionally include stray quotes in query params.
    url = url.replace('sslmode="', "sslmode=").replace("sslmode='", "sslmode=")
    url = url.replace('require"', "require").replace("require'", "require")
    return url


engine = create_async_engine(_async_database_url(settings.database_url), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
