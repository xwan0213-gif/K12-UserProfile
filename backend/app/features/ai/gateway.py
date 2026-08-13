"""模型网关：按配置选择 DeepSeek / FakeLLM，并统一暴露 generate / transcribe。"""

from __future__ import annotations

from typing import Any, Protocol

from app.core.config import get_settings
from app.features.ai.providers.asr_fake import FakeAsrProvider, StubAsrProvider
from app.features.ai.providers.deepseek import DeepSeekProvider
from app.features.ai.providers.fake import FakeLLMProvider


class AsrProvider(Protocol):
    """语音转写 Provider 协议；实现方需提供 async transcribe。"""

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str: ...


class ModelGateway:
    """统一入口：LLM 生成与 ASR 转写；构造时按 settings 选定具体 Provider。"""

    def __init__(self) -> None:
        settings = get_settings()
        # mock_llm 开启时走确定性 Fake，避免本地/演示依赖真实 Key
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
        """按任务类型调用 LLM，返回结构化 JSON（dict）。

        参数:
            task: 业务任务名（如 profile / reply / schedule / tag_recommend）
            payload: 任务上下文与 prompt 等输入
        返回:
            Provider 解析后的 JSON 对象
        """
        return await self._provider.generate(task, payload)

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str:
        """将语音引用/元数据转写为文本；委托当前 ASR Provider。

        参数:
            audio_ref: 音频引用标识（URL/路径/业务侧 key）
            bytes_meta: 附加元数据（可含 hint）
            content_hint: 优先使用的文本提示（有则 Fake ASR 直接返回）
        返回:
            转写文本；Stub 模式下可能抛 AppError
        """
        return await self._asr.transcribe(
            audio_ref, bytes_meta, content_hint=content_hint
        )


def _build_asr(settings) -> AsrProvider:
    """按配置选择 Fake 或 Stub ASR（真实厂商尚未接入时 Stub 明确失败）。"""
    # mock、显式 fake、或未配置 key 时均走 Fake，便于本地联调
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
    """进程内单例 ModelGateway；首次调用时按当前 settings 初始化。"""
    global _gateway
    if _gateway is None:
        _gateway = ModelGateway()
    return _gateway


def get_asr() -> AsrProvider:
    """返回 ASR Provider 单例（mock/无 key 用 Fake，否则 Stub）。"""
    global _asr
    if _asr is None:
        _asr = _build_asr(get_settings())
    return _asr
