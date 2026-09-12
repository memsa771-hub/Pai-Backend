"""Read-only auth dependency timings. No passwords, tokens or URLs are printed.

Run from the project root: python scripts/auth_diagnostics.py
Uses the configured provider health endpoint and SELECT 1 only. Does not send email,
create sessions, mutate counters, run migrations or read student records.
"""

import asyncio
import json
from time import perf_counter

from sqlalchemy import text

from pai.config import get_settings
from pai.platform.database.db import get_engine
from pai.platform.security.auth.supabase import SupabaseAuthProvider


async def main():
    settings = get_settings()
    results = {}
    provider = SupabaseAuthProvider(settings)
    engine = get_engine(settings)

    async def measure(name, operation):
        timings = []
        for _ in range(3):
            started = perf_counter()
            try:
                async with asyncio.timeout(10):
                    healthy = await operation()
                timings.append(
                    {"ms": round((perf_counter() - started) * 1000, 1), "ok": bool(healthy)}
                )
            except Exception as exc:
                timings.append(
                    {
                        "ms": round((perf_counter() - started) * 1000, 1),
                        "error_type": type(exc).__name__,
                    }
                )
                break
        results[name] = timings

    async def database():
        async with engine.connect() as conn:
            return (await conn.execute(text("SELECT 1"))).scalar_one() == 1

    try:
        operations = [
            measure("supabase_health", provider.health_check),
            measure("database_select_one", database),
        ]
        if settings.rate_limit_redis_url:
            from pai.platform.redis_limits import get_client

            operations.append(measure("redis_ping", get_client(settings).ping))
        else:
            results["redis"] = "not_configured; development uses PostgreSQL counters"
        await asyncio.gather(*operations)
    finally:
        await provider.aclose()
        await engine.dispose()
        from pai.platform.redis_limits import close_clients

        await close_clients()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
