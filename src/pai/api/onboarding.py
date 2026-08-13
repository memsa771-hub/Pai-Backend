from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.dependencies import get_db, resolve_person_from_token
from pai.llm.gateway import LLMGateway
from pai.onboarding.schema import OnboardingSubmit
from pai.onboarding.service import OnboardingService
from pai.person.models import Person
from pai.schemas import ApiErrorResponse, success
from pai.storage.supabase import SupabaseStorageProvider

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

_ONBOARDING_ERRORS = {
    400: {"model": ApiErrorResponse},
    401: {"model": ApiErrorResponse},
    403: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
}


def _svc(settings: Settings) -> OnboardingService:
    return OnboardingService(settings)


@router.get(
    "",
    responses=_ONBOARDING_ERRORS,
    summary="Get onboarding status",
    description=(
        "Returns path choices (`manual` or `cv`), required vs optional fields, "
        "extracted CV facts, and `onboardingCompleted` / `nextPath` for routing. "
        "Signup and login never mark onboarding complete."
    ),
)
async def get_onboarding(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).status(session, person)
    return JSONResponse(content=success(data))


@router.post(
    "",
    responses=_ONBOARDING_ERRORS,
    summary="Submit complete onboarding",
    description=(
        "Accepts the full profile in one request (the frontend may collect it in steps). "
        "Validates required identity fields, maps accepted values into the Person Vault, "
        "and sets `onboardingCompleted` only on success. Idempotent: re-submit updates "
        "the vault and still returns completed status. After a CV upload, send the same "
        "payload with any missing critical fields filled in to confirm and complete."
    ),
)
async def submit_onboarding(
    body: OnboardingSubmit,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).submit(session, person, body)
    return JSONResponse(content=success(data))


@router.post(
    "/cv",
    responses=_ONBOARDING_ERRORS,
    summary="Upload CV/PDF for profile extraction",
    description=(
        "Extracts profile facts from a CV/PDF. Does **not** mark onboarding complete. "
        "GET /onboarding then lists `missingRequired`; POST /onboarding with those "
        "fields (plus extracted values) to confirm and unlock PAI."
    ),
)
async def upload_onboarding_cv(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
    file: UploadFile = File(...),
) -> JSONResponse:
    data = await file.read()
    storage = SupabaseStorageProvider(settings)
    gateway: LLMGateway = getattr(request.app.state, "llm_gateway", None) or LLMGateway(settings)
    try:
        result = await _svc(settings).ingest_cv(
            session,
            person,
            filename=file.filename or "cv.pdf",
            content_type=file.content_type or "application/pdf",
            data=data,
            storage=storage,
            gateway=gateway,
        )
    finally:
        await storage.aclose()
    return JSONResponse(status_code=202, content=success(result))
