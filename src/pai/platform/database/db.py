import socket
import ssl
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse

import certifi
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pai.config import Settings, get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _is_remote_postgres(database_url: str) -> bool:
    host = urlparse(database_url).hostname or ""
    return host.endswith(".supabase.co") or host.endswith(".pooler.supabase.com")


def _ipv4_for_host(host: str) -> str | None:
    """A-record only. Windows often stalls ~5s on a dead AAAA before falling back."""
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        return None
    if not infos:
        return None
    return infos[0][4][0]


def _engine_connect_args(database_url: str, *, ssl_verify: bool = True, ca_file: str = "") -> dict:
    host = urlparse(database_url).hostname or ""
    if host in {"localhost", "127.0.0.1", "::1", "postgres"}:
        return {}
    ctx = ssl.create_default_context(cafile=certifi.where())
    if _is_remote_postgres(database_url):
        ctx.load_verify_locations(
            cafile=str(Path(__file__).parent / "certs" / "supabase-root-2021.crt")
        )
    if ca_file:
        ctx.load_verify_locations(cafile=ca_file)
    args: dict = {"ssl": ctx, "timeout": 8}
    # Preserve the original hostname for TLS SNI and certificate verification.
    # Replacing it with an IP silently removed endpoint identity verification.
    if not ssl_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return args


def get_engine(settings: Settings | None = None):
    global _engine, _session_factory
    settings = settings or get_settings()
    if _engine is None:
        remote = _is_remote_postgres(settings.database_url)
        testing = settings.app_env in {"test", "testing"}
        # Session-mode Supabase poolers cap clients near pool_size=15 for the
        # whole project. API + three workers each using pool_size=5/overflow=10
        # hits EMAXCONNSESSION immediately. Keep remote pools tiny.
        if testing:
            pool_kwargs: dict = {"poolclass": NullPool}
        elif remote:
            pool_kwargs = {"pool_size": 2, "max_overflow": 1}
        else:
            pool_kwargs = {"pool_size": 5, "max_overflow": 10}
        _engine = create_async_engine(
            settings.database_url,
            # Remote pooler: skip pre-ping (extra RTT) and recycle idle sockets.
            pool_pre_ping=testing or not remote,
            pool_recycle=180 if remote else -1,
            **pool_kwargs,
            connect_args=_engine_connect_args(
                settings.database_url,
                ssl_verify=settings.database_ssl_verify,
                ca_file=settings.database_ssl_ca_file,
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


async def warmup_database(settings: Settings | None = None) -> None:
    engine = get_engine(settings)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


def reset_engine_for_tests() -> None:
    global _engine, _session_factory
    _engine = None
    _session_factory = None
