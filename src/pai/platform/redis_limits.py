"""Single-round-trip, atomic reservations across API replicas.

Use a dedicated Redis primary (or Sentinel endpoint), not a sharded cluster:
multi-key reservations must execute together. Only hashed subjects are stored.
"""

import hashlib

from redis.asyncio import Redis

_clients: dict[str, Redis] = {}

_RESERVE = """
local now = tonumber(redis.call('TIME')[1])
local retry = 0
for i, key in ipairs(KEYS) do
    local offset = (i - 1) * 3
    local cost = tonumber(ARGV[offset + 1])
    local limit = tonumber(ARGV[offset + 2])
    local window = tonumber(ARGV[offset + 3])
    local bucket = math.floor(now / window)
    local previous = redis.call('HMGET', key, 'bucket', 'used')
    local used = 0
    if tonumber(previous[1]) == bucket then used = tonumber(previous[2]) or 0 end
    if used + cost > limit then retry = math.max(retry, (bucket + 1) * window - now) end
end
if retry > 0 then return retry end
for i, key in ipairs(KEYS) do
    local offset = (i - 1) * 3
    local cost = tonumber(ARGV[offset + 1])
    local window = tonumber(ARGV[offset + 3])
    local bucket = math.floor(now / window)
    if tonumber(redis.call('HGET', key, 'bucket')) ~= bucket then
        redis.call('HSET', key, 'bucket', bucket, 'used', 0)
    end
    redis.call('HINCRBY', key, 'used', cost)
    redis.call('EXPIREAT', key, (bucket + 1) * window + 1)
end
return 0
"""


def get_client(settings) -> Redis:
    url = settings.rate_limit_redis_url
    if url not in _clients:
        _clients[url] = Redis.from_url(
            url,
            socket_timeout=settings.redis_timeout_seconds,
            socket_connect_timeout=settings.redis_timeout_seconds,
            max_connections=100,
            decode_responses=True,
        )
    return _clients[url]


async def reserve(settings, items) -> int:
    keys, args = [], []
    for namespace, subject, cost, limit, window in items:
        digest = hashlib.sha256(str(subject).encode()).hexdigest()
        keys.append(f"pai:limits:{namespace}:{digest}:{window}")
        args.extend([cost, limit, window])
    return int(await get_client(settings).eval(_RESERVE, len(keys), *keys, *args))


async def close_clients() -> None:
    clients = list(_clients.values())
    _clients.clear()
    for client in clients:
        await client.aclose()
