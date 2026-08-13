from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pai.config import Settings, get_settings
from pai.dependencies import get_db, resolve_person_from_token
from pai.llm.gateway import LLMGateway
from pai.onboarding.schema import (
    ChoosePathRequest,
    OnboardingGapAnswers,
    OnboardingStep1,
    OnboardingStep2,
    OnboardingStep3,
)
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
        "After first login, choose `manual` or `cv`. Chat stays locked until "
        "`POST /api/v1/onboarding/complete` and required profile facts are present."
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
    "/path",
    responses=_ONBOARDING_ERRORS,
    summary="Choose Complete Onboarding or Upload My CV",
)
async def choose_path(
    body: ChoosePathRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).choose_path(session, person, body.path)
    return JSONResponse(content=success(data))


@router.put(
    "/steps/1",
    responses=_ONBOARDING_ERRORS,
    summary="Manual step 1 — about you",
)
async def put_step1(
    body: OnboardingStep1,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).save_step(session, person, 1, body)
    return JSONResponse(content=success(data))


@router.put(
    "/steps/2",
    responses=_ONBOARDING_ERRORS,
    summary="Manual step 2 — education",
)
async def put_step2(
    body: OnboardingStep2,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).save_step(session, person, 2, body)
    return JSONResponse(content=success(data))


@router.put(
    "/steps/3",
    responses=_ONBOARDING_ERRORS,
    summary="Manual step 3 — goal",
)
async def put_step3(
    body: OnboardingStep3,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).save_step(session, person, 3, body)
    return JSONResponse(content=success(data))


@router.post(
    "/cv",
    responses=_ONBOARDING_ERRORS,
    summary="Upload CV for onboarding",
    description="Extracts education, skills, and projects, then returns only missing questions.",
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


@router.post(
    "/review",
    responses=_ONBOARDING_ERRORS,
    summary="Answer missing onboarding questions after CV (or leftover gaps)",
)
async def review_onboarding(
    body: OnboardingGapAnswers,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).apply_gap_answers(session, person, body)
    return JSONResponse(content=success(data))


@router.post(
    "/complete",
    responses=_ONBOARDING_ERRORS,
    summary="Mark onboarding complete and unlock PAI",
)
async def complete_onboarding(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await _svc(settings).complete(session, person)
    return JSONResponse(content=success(data))
