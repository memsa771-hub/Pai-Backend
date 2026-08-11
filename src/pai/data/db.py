from collections.abc import AsyncIterator

import ssl

import certifi
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pai.config import Settings, get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _engine_connect_args(database_url: str, *, ssl_verify: bool = True) -> dict:
    if "supabase.co" in database_url or "pooler.supabase.com" in database_url:
        ctx = ssl.create_default_context(cafile=certifi.where())
        if not ssl_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}
    return {}


def get_engine(settings: Settings | None = None):
    global _engine, _session_factory
    settings = settings or get_settings()
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=3 if settings.app_env == "test" else 5,
            max_overflow=0 if settings.app_env == "test" else 10,
            connect_args=_engine_connect_args(
                settings.database_url, ssl_verify=settings.database_ssl_verify
            ),
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    get_engine(settings)
    assert _session_factory is not None
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def reset_engine_for_tests() -> None:
    global _engine, _session_factory
    _engine = None
    _session_factory = None
