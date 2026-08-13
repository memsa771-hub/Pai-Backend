from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pai.dependencies import get_db, resolve_person_from_token
from pai.onboarding.schema import OnboardingStep1, OnboardingStep2, OnboardingStep3
from pai.onboarding.service import OnboardingService
from pai.person.models import Person
from pai.schemas import ApiErrorResponse, success

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

_ONBOARDING_ERRORS = {
    400: {"model": ApiErrorResponse},
    401: {"model": ApiErrorResponse},
    403: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
}


@router.get(
    "",
    responses=_ONBOARDING_ERRORS,
    summary="Get onboarding status and saved answers",
    description=(
        "Call after first verified login. If `completed` is false, collect the three steps "
        "then `POST /api/v1/onboarding/complete` before chat."
    ),
)
async def get_onboarding(
    session: Annotated[AsyncSession, Depends(get_db)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await OnboardingService().status(session, person)
    return JSONResponse(content=success(data))


@router.put(
    "/steps/1",
    responses=_ONBOARDING_ERRORS,
    summary="Save onboarding step 1 — identity",
)
async def put_step1(
    body: OnboardingStep1,
    session: Annotated[AsyncSession, Depends(get_db)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await OnboardingService().save_step(session, person, 1, body)
    return JSONResponse(content=success(data))


@router.put(
    "/steps/2",
    responses=_ONBOARDING_ERRORS,
    summary="Save onboarding step 2 — location and status",
)
async def put_step2(
    body: OnboardingStep2,
    session: Annotated[AsyncSession, Depends(get_db)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await OnboardingService().save_step(session, person, 2, body)
    return JSONResponse(content=success(data))


@router.put(
    "/steps/3",
    responses=_ONBOARDING_ERRORS,
    summary="Save onboarding step 3 — academic background",
)
async def put_step3(
    body: OnboardingStep3,
    session: Annotated[AsyncSession, Depends(get_db)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await OnboardingService().save_step(session, person, 3, body)
    return JSONResponse(content=success(data))


@router.post(
    "/complete",
    responses=_ONBOARDING_ERRORS,
    summary="Mark onboarding complete and unlock PAI",
    description="Fails unless every required field across the three steps is present.",
)
async def complete_onboarding(
    session: Annotated[AsyncSession, Depends(get_db)],
    person: Annotated[Person, Depends(resolve_person_from_token)],
) -> JSONResponse:
    data = await OnboardingService().complete(session, person)
    return JSONResponse(content=success(data))
