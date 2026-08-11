from __future__ import annotations

from pydantic import BaseModel

from pai.config import Settings, get_settings
from pai.llm.provider import LLMProvider
from pai.llm.providers.deepseek import DeepSeekProvider
from pai.llm.schemas import LLMMessage, LLMRequest, LLMResponse


class LLMGateway:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._providers: dict[str, LLMProvider] = {}
        if self._settings.deepseek_api_key:
            self._providers["deepseek"] = DeepSeekProvider(self._settings)

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        self._providers[name] = provider

    def _provider_for_task(self, task: str) -> LLMProvider:
        name = self._settings.llm_default_provider
        provider = self._providers.get(name)
        if provider is None:
            from pai.core.errors import AuthError

            raise AuthError(
                code="LLM_NOT_CONFIGURED",
                message="No LLM provider is configured.",
                status_code=503,
            )
        return provider

    def _model_for_task(self, task: str) -> str:
        if task in ("extraction", "extract_facts", "fact_extraction"):
            return self._settings.llm_extraction_model
        if task in ("document", "document_extract"):
            return self._settings.llm_document_model
        if task in ("counseling", "student_conversation"):
            return self._settings.llm_counseling_model
        return self._settings.llm_counseling_model

    async def run(
        self,
        *,
        task: str,
        messages: list[LLMMessage],
        output_schema: type[BaseModel] | None = None,
        temperature: float = 0.3,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
    ) -> LLMResponse | BaseModel:
        provider = self._provider_for_task(task)
        request = LLMRequest(
            messages=messages,
            temperature=temperature,
            model=self._model_for_task(task),
            tools=tools,
            tool_choice=tool_choice,
        )
        if output_schema is not None:
            return await provider.generate_structured(request, output_schema)
        return await provider.generate(request)

    async def aclose(self) -> None:
        for provider in self._providers.values():
            if hasattr(provider, "aclose"):
                await provider.aclose()
