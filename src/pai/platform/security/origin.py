"""Browser-origin checks shared by auth middleware and CSRF dependencies."""

from urllib.parse import urlsplit


def request_origin_is_trusted(
    origin: str | None,
    scheme: str,
    host: str,
    allowed: list[str],
) -> bool:
    if not origin:
        return True
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    normalized = f"{parsed.scheme}://{parsed.netloc}".lower()
    allowed_origins = {item.rstrip("/").lower() for item in allowed}
    if normalized in allowed_origins:
        return True
    # Swagger and other browser clients served directly by this API are same-origin.
    request_origin = f"{scheme}://{host}".rstrip("/").lower()
    return normalized == request_origin
