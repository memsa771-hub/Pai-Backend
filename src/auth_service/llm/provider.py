from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from auth_service.llm.schemas import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    name: str

    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_structured(
        self,
        request: LLMRequest,
        output_schema: type[BaseModel],
    ) -> BaseModel: ...
