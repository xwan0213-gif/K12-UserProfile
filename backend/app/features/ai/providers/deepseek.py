from typing import Any

import httpx

from app.core.errors import AppError, ErrorCode


class DeepSeekProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
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
        except Exception as exc:  # noqa: BLE001 — surface as AI failure
            raise AppError(
                ErrorCode.AI_FAILED,
                "AI 任务失败",
                data={"detail": str(exc)},
                http_status=500,
            ) from exc
