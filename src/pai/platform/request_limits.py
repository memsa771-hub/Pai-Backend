"""Rate limits and streamed request-body bounds before endpoint parsing."""

from starlette.responses import JSONResponse

from pai.kernel.errors import AuthError
from pai.platform.limits import consume, enabled, usage_subject
from pai.platform.security.origin import request_origin_is_trusted


class RequestLimitsMiddleware:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith("/health/"):
            return await self.app(scope, receive, send)
        settings = self.settings
        is_auth = scope["path"].startswith("/api/v1/auth/")
        maximum = 32768 if is_auth else settings.document_max_bytes + 65536
        headers = dict(scope.get("headers", []))
        if is_auth:
            original_send = send

            async def auth_send(message):
                if message["type"] == "http.response.start":
                    from time import perf_counter

                    from pai.platform.latency import record

                    action = scope["path"].removeprefix("/api/v1/auth/")
                    if action in {
                        "signup",
                        "login",
                        "refresh",
                        "logout",
                        "session",
                        "me",
                        "password/forgot",
                        "password/reset",
                        "password/change",
                        "email-verification/request",
                        "email-verification/confirm",
                    }:
                        record(
                            "auth_response",
                            scope.get("state", {}).get("request_started", perf_counter()),
                            action=action,
                            status=message["status"],
                        )
                    message = dict(message)
                    message["headers"] = [
                        (key, value)
                        for key, value in message.get("headers", [])
                        if key.lower() not in {b"cache-control", b"pragma"}
                    ] + [(b"cache-control", b"no-store"), (b"pragma", b"no-cache")]
                await original_send(message)

            send = auth_send
            if scope["method"] == "POST":
                origin = headers.get(b"origin")
                host = headers.get(b"host", b"").decode("latin-1")
                if origin and not request_origin_is_trusted(
                    origin.decode("latin-1"), scope.get("scheme", "http"), host,
                    settings.cors_origins,
                ):
                    return await JSONResponse(
                        {
                            "success": False,
                            "error": {
                                "code": "CSRF_FAILED",
                                "message": "Untrusted request origin.",
                            },
                        },
                        status_code=403,
                    )(scope, receive, send)
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = maximum + 1
        if length > maximum or length < 0:
            return await JSONResponse(
                {
                    "error": {
                        "code": "UPLOAD_TOO_LARGE",
                        "message": "Request body exceeds the upload limit.",
                    }
                },
                status_code=413,
            )(scope, receive, send)
        try:
            if enabled(settings):
                ip = (scope.get("client") or ("unknown",))[0]
                limit = (
                    settings.auth_ip_limit_per_minute
                    if is_auth
                    else settings.request_limit_per_minute
                )
                await consume(
                    settings,
                    [("auth_ip" if is_auth else "requests", ip, 1, limit, 60)],
                    fail_closed=settings.auth_rate_limit_fail_closed if is_auth else None,
                )
            count = 0

            async def bounded_receive():
                nonlocal count
                message = await receive()
                if message["type"] == "http.request":
                    count += len(message.get("body", b""))
                    if count > maximum:
                        # FastAPI preserves HTTPException status during multipart parsing.
                        from starlette.exceptions import HTTPException

                        raise HTTPException(
                            status_code=413, detail="Request body exceeds upload limit."
                        )
                return message

            token = usage_subject.set("anonymous")
            try:
                await self.app(scope, bounded_receive, send)
            finally:
                usage_subject.reset(token)
        except AuthError as exc:
            await JSONResponse(
                {"error": {"code": exc.code, "message": exc.message}},
                status_code=exc.status_code,
                headers={"Retry-After": str(getattr(exc, "retry_after", 5))},
            )(scope, receive, send)
