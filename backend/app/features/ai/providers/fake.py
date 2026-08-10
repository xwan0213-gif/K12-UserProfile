from typing import Any


class FakeLLMProvider:
    """Returns fixed JSON for local/demo without DEEPSEEK_API_KEY."""

    async def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        if task == "profile":
            return {
                "basic_info": {
                    "school": "城南实验中学",
                    "grade": "初二",
                    "parent": "王女士",
                    "student": "王小明",
                },
                "study_info": {
                    "weak_subjects": ["数学"],
                    "score_hint": "期中约70",
                    "goal": "夯实基础",
                    "intent": "试听",
                },
                "prefer_info": {
                    "active_hours": "20:00-22:00",
                    "price_sensitive": True,
                    "decision_style": "谨慎需试听",
                },
                "timeline": [
                    {"date": "2026-06-20", "text": "首次咨询初二数学"},
                    {"date": "2026-06-25", "text": "了解班型与师资"},
                ],
                "confidence": 0.86,
                "sources": [
                    {"type": "chat", "ref": "recent"},
                    {"type": "fake_llm", "ref": "fixed"},
                ],
            }
        return {"task": task, "echo": payload, "provider": "fake"}
