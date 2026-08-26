from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.dependencies import get_db, resolve_person_from_token
from pai.platform.llm.gateway import LLMGateway
from pai.domains.onboarding.schema import OnboardingSubmit
from pai.domains.onboarding.service import OnboardingService
from pai.domains.student.person.models import Person
from pai.schemas import ApiErrorResponse, success
from pai.platform.storage.supabase import SupabaseStorageProvider

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
        "Incomplete: form catalog (`choices`, `requiredFields`, `enums`). "
        "Country dropdowns use `enums.countries` once. "
        "Complete: compact status only (`onboardingCompleted`, `nextPath`, `identity`). "
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
    summary="Submit starting onboarding profile",
    description=(
        "Accepts a small starting profile in one request. "
        "Returns compact status (`onboardingCompleted`, `nextPath`, `identity`) — "
        "not the form catalog. Dropdowns come from GET /onboarding. "
        "Idempotent. CV users should POST /onboarding/cv instead."
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
        "Extracts the CV into the Person Vault and **marks onboarding complete**. "
        "Returns compact status, not the form catalog. Chat unlocks immediately. "
        "Upload a text-based PDF or DOCX (not a scanned image)."
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
    return JSONResponse(content=success(result))
