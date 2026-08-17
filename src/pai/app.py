from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from pai.api.auth import account_router
from pai.api.auth import router as auth_router
from pai.api.chat import chat_router
from pai.api.documents import router as documents_router
from pai.api.onboarding import router as onboarding_router
from pai.api.person import router as person_router
from pai.api.vault import router as vault_router
from pai.config import Settings, get_settings
from pai.core.errors import AuthError
from pai.data.db import warmup_database
from pai.documents.worker import document_worker_loop
from pai.llm.gateway import LLMGateway
from pai.openapi import API_DESCRIPTION, OPENAPI_TAGS, customize_openapi_schema
from pai.orchestration.checkpoint import close_graph_checkpointer, init_graph_checkpointer
from pai.orchestration.prompts import validate_prompt_templates
from pai.providers.supabase import SupabaseAuthProvider
from pai.schemas import error, humanize_validation_error, success

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    validate_prompt_templates()
    await init_graph_checkpointer(
        settings.database_url,
        enabled=(
            settings.enable_graph_checkpoint
            and settings.app_env not in ("test", "testing")
        ),
    )
    app.state.llm_gateway = LLMGateway(settings)
    if settings.app_env not in {"test", "testing"}:
        try:
            await warmup_database(settings)
        except Exception:
            logger.warning(
                "Database warmup failed; first request may be slower.", exc_info=True
            )
    if not getattr(app.state, "_provider_initialized", False):
        provider = SupabaseAuthProvider(settings)
        app.state.auth_provider = provider
        app.state._provider_initialized = True
        app.state._owns_provider = True
    worker_stop = asyncio.Event()
    worker_task: asyncio.Task | None = None
    if settings.enable_document_worker:
        worker_task = asyncio.create_task(document_worker_loop(settings, worker_stop))
    try:
        yield
    finally:
        worker_stop.set()
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        gateway = getattr(app.state, "llm_gateway", None)
        if gateway is not None:
            await gateway.aclose()
        if getattr(app.state, "_owns_provider", False):
            await app.state.auth_provider.aclose()
        await close_graph_checkpointer()


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    docs_enabled = app_settings.app_env != "production"

    app = FastAPI(
        title="Placement AI (PAI)",
        description=API_DESCRIPTION,
        version="0.2.0",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
            "docExpansion": "list",
            "defaultModelsExpandDepth": 1,
            "syntaxHighlight.theme": "monokai",
        },
    )
    app.state.settings = app_settings

    def override_get_settings() -> Settings:
        return app.state.settings

    app.dependency_overrides[get_settings] = override_get_settings

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=OPENAPI_TAGS,
        )
        app.openapi_schema = customize_openapi_schema(schema)
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=app_settings.trusted_hosts)

    @app.exception_handler(AuthError)
    async def auth_error_handler(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error("VALIDATION_ERROR", humanize_validation_error(exc.errors())),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error("VALIDATION_ERROR", humanize_validation_error(exc.errors())),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request error")
        return JSONResponse(
            status_code=500,
            content=error("INTERNAL_ERROR", "Request failed. Try again."),
        )

    @app.get(
        "/health/live",
        tags=["health"],
        summary="Liveness probe",
        description="Process is up. No auth required.",
    )
    async def health_live() -> JSONResponse:
        return JSONResponse(content=success({"status": "live"}))

    @app.get(
        "/health/ready",
        tags=["health"],
        summary="Readiness probe",
        description="Auth provider reachable. No auth required.",
    )
    async def health_ready(request: Request) -> JSONResponse:
        provider: SupabaseAuthProvider = request.app.state.auth_provider
        ok = await provider.health_check()
        if not ok:
            return JSONResponse(
                status_code=503,
                content=error("NOT_READY", "Authentication provider is not reachable."),
            )
        return JSONResponse(content=success({"status": "ready"}))

    app.include_router(auth_router)
    app.include_router(account_router)
    app.include_router(person_router)
    app.include_router(onboarding_router)
    app.include_router(vault_router)
    app.include_router(chat_router)
    app.include_router(documents_router)
    return app


def create_app_from_env() -> FastAPI:
    return create_app(get_settings())
