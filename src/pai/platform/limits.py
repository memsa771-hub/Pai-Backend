"""Atomic database-backed limits shared by API processes and background workers."""

import asyncio
import hashlib
import logging
import time
from contextvars import ContextVar

from sqlalchemy import text

from pai.kernel.errors import AuthError
from pai.platform.database.db import get_session_factory

usage_subject = ContextVar("usage_subject", default="background")
logger = logging.getLogger(__name__)
_last_backend_warning = 0.0
_local_lock = asyncio.Lock()
_local_buckets: dict[tuple[str, str, int], tuple[int, int]] = {}


class LimitExceeded(AuthError):
    def __init__(self, retry_after):
        super().__init__(
            code="USAGE_LIMIT",
            message="Usage limit reached. Please try again later.",
            status_code=429,
        )
        self.retry_after = retry_after


def enabled(settings):
    return settings.enable_rate_limits and settings.app_env not in {"test", "testing"}


async def _reserve_local(items) -> int:
    """Reserve limits atomically for a single-process development server."""
    now = int(time.time())
    retry_after = 0
    prepared = []
    async with _local_lock:
        for namespace, subject, cost, limit, window in items:
            bucket = now // window
            key = (namespace, hashlib.sha256(str(subject).encode()).hexdigest(), window)
            stored_bucket, used = _local_buckets.get(key, (bucket, 0))
            if stored_bucket != bucket:
                used = 0
            if used + cost > limit:
                retry_after = max(retry_after, (bucket + 1) * window - now)
            prepared.append((key, bucket, used, cost))
        if retry_after:
            return retry_after
        for key, bucket, used, cost in prepared:
            _local_buckets[key] = (bucket, used + cost)
        if len(_local_buckets) > 10_000:
            active = {
                key: value
                for key, value in _local_buckets.items()
                if value[0] >= now // key[2]
            }
            _local_buckets.clear()
            _local_buckets.update(active)
    return 0


async def consume(settings, items, *, fail_closed=None):
    """Reserve (namespace, subject, cost, limit, window seconds) atomically.

    Failed provider calls retain reservations to cap retry storms. Token costs
    are conservative upper bounds, not billing totals. No credentials are stored.
    """
    if not enabled(settings):
        return
    fail_closed = settings.rate_limit_fail_closed if fail_closed is None else fail_closed
    global _last_backend_warning
    try:
        if settings.rate_limit_redis_url:
            from pai.platform.redis_limits import reserve

            async with asyncio.timeout(settings.redis_timeout_seconds):
                retry_after = await reserve(settings, items)
            if retry_after:
                raise LimitExceeded(retry_after)
            return

        if settings.app_env.lower() not in {"production", "prod"}:
            retry_after = await _reserve_local(items)
            if retry_after:
                raise LimitExceeded(retry_after)
            return

        async def reserve_postgres():
            async with get_session_factory(settings)() as session:
                for namespace, subject, cost, limit, window in sorted(
                    items, key=lambda item: (item[0], str(item[1]), item[4])
                ):
                    key = f"{namespace}:{hashlib.sha256(str(subject).encode()).hexdigest()}:"
                    if cost > limit:
                        raise LimitExceeded(window)
                    accepted = await session.execute(
                        text(
                            "WITH bucket AS (SELECT floor(extract(epoch "
                            "FROM statement_timestamp()) "
                            "/ :window) AS n) "
                            "INSERT INTO usage_counters (key, used, expires_at) "
                            "SELECT :key || n::bigint::text, :cost, "
                            "to_timestamp((n + 1) * :window) FROM bucket "
                            "ON CONFLICT (key) DO UPDATE SET used = usage_counters.used + :cost "
                            "WHERE usage_counters.used + :cost <= :limit RETURNING used"
                        ),
                        {"key": key, "cost": cost, "window": window, "limit": limit},
                    )
                    if accepted.scalar_one_or_none() is None:
                        raise LimitExceeded(window)
                await session.commit()

        from pai.platform.bounded_io import run_bounded

        await run_bounded(
            reserve_postgres, settings.rate_limit_backend_timeout_seconds, group="postgres-limits"
        )
    except AuthError:
        raise
    except TimeoutError:
        now = time.monotonic()
        if now - _last_backend_warning >= 60:
            _last_backend_warning = now
            logger.warning(
                "Rate-limit backend timed out; %s request",
                "blocking" if fail_closed else "allowing",
            )
        if fail_closed:
            raise AuthError(
                code="LIMITS_UNAVAILABLE",
                message="Service temporarily unavailable.",
                status_code=503,
            )
    except Exception as exc:
        now = time.monotonic()
        if now - _last_backend_warning >= 60:
            _last_backend_warning = now
            logger.error(
                "Rate-limit backend unavailable; %s request (%s)",
                "blocking" if fail_closed else "allowing",
                type(exc).__name__,
                exc_info=True,
            )
        if fail_closed:
            raise AuthError(
                code="LIMITS_UNAVAILABLE",
                message="Service temporarily unavailable.",
                status_code=503,
            ) from exc


async def reserve_llm(settings, request, *, subject=None):
    if not enabled(settings):
        return
    # UTF-8 bytes conservatively bound text tokens, including structured inputs.
    import json

    tokens = (
        len(json.dumps(request.model_dump(), ensure_ascii=False, default=str).encode())
        + request.max_tokens
        + (1024 if request.reasoning_effort not in (None, "none") else 0)
    )
    subject = subject or usage_subject.get()
    await consume(
        settings,
        [
            ("llm_calls", subject, 1, settings.llm_call_limit_per_day, 86400),
            ("llm_tokens", subject, tokens, settings.llm_token_limit_per_day, 86400),
            ("llm_global", "all", tokens, settings.llm_global_token_limit_per_day, 86400),
        ],
    )
