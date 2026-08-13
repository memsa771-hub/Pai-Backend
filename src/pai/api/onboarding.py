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
        "Returns path choices, required/optional/conditional fields, and `enums` "
        "(closed lists for goal, education, gender, countries, budget, intake, …). "
        "Onboarding is only a starting seed; chat and documents enrich the Vault. "
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
        "Accepts a small starting profile in one request (the UI may still show steps). "
        "Only critical identity fields are required. Optional extras are stored if sent. "
        "Deeper Vault facts come from chat extraction and documents. "
        "Sets `onboardingCompleted` only on success. Idempotent. After a CV upload, "
        "POST the same payload with any missing critical fields to confirm."
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
        "Extracts profile facts from a CV/PDF into the Vault. Does **not** mark "
        "onboarding complete. Confirm missing *critical* fields with POST /onboarding. "
        "Skills, work history, and other details can stay in the Vault from extraction "
        "and later chat — they are not required to finish onboarding."
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
