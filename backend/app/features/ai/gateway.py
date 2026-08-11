"""Model Gateway: generate(task, payload) with DeepSeek / FakeLLM; ASR via Fake/Stub."""

from __future__ import annotations

from typing import Any, Protocol

from app.core.config import get_settings
from app.features.ai.providers.asr_fake import FakeAsrProvider, StubAsrProvider
from app.features.ai.providers.deepseek import DeepSeekProvider
from app.features.ai.providers.fake import FakeLLMProvider


class AsrProvider(Protocol):
    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str: ...


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
        self._asr = _build_asr(settings)

    async def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._provider.generate(task, payload)

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str:
        return await self._asr.transcribe(
            audio_ref, bytes_meta, content_hint=content_hint
        )


def _build_asr(settings) -> AsrProvider:
    use_fake = (
        settings.mock_llm
        or settings.asr_provider == "fake"
        or not (settings.asr_api_key or "").strip()
    )
    if use_fake:
        return FakeAsrProvider()
    return StubAsrProvider()


_gateway: ModelGateway | None = None
_asr: AsrProvider | None = None


def get_gateway() -> ModelGateway:
    global _gateway
    if _gateway is None:
        _gateway = ModelGateway()
    return _gateway


def get_asr() -> AsrProvider:
    """Return ASR provider (Fake when mock/no key; Stub otherwise)."""
    global _asr
    if _asr is None:
        _asr = _build_asr(get_settings())
    return _asr
