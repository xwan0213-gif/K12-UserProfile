"""Model Gateway: generate(task, payload) with DeepSeek / FakeLLM."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.features.ai.providers.deepseek import DeepSeekProvider
from app.features.ai.providers.fake import FakeLLMProvider


class ModelGateway:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.mock_llm:
            self._provider = FakeLLMProvider()
        else:
            self._provider = DeepSeekProvider(
                api_key=settings.deepseek_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
            )

    async def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._provider.generate(task, payload)


_gateway: ModelGateway | None = None


def get_gateway() -> ModelGateway:
    global _gateway
    if _gateway is None:
        _gateway = ModelGateway()
    return _gateway
