"""DeepSeek（OpenAI 兼容）LLM Provider：聊天补全并解析 JSON 响应。"""

from typing import Any

import httpx

from app.core.errors import AppError, ErrorCode


class DeepSeekProvider:
    """调用 DeepSeek Chat Completions，要求模型仅回复 JSON。"""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        """保存凭据与模型名；base_url 去掉尾部斜杠便于拼接路径。"""
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        """发起一次 chat/completions，将 message.content 解析为 dict。

        参数:
            task: 写入 system prompt 的任务标识
            payload: 至少可含 prompt；缺省时用整个 payload 的 str
        返回:
            模型返回的 JSON 对象
        副作用:
            对外 HTTP 请求；失败时抛 AppError(AI_FAILED)
        """
        if not self.api_key:
            raise AppError(
                ErrorCode.AI_FAILED,
                "未配置 DEEPSEEK_API_KEY",
                http_status=500,
            )

        prompt = payload.get("prompt") or str(payload)
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a K12 education CRM assistant. Task={task}. Reply JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                import json

                return json.loads(content)
        except Exception as exc:  # noqa: BLE001 — 统一收敛为业务侧 AI 失败
            raise AppError(
                ErrorCode.AI_FAILED,
                "AI 任务失败",
                data={"detail": str(exc)},
                http_status=500,
            ) from exc
