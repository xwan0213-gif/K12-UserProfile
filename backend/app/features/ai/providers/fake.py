from typing import Any


def _join_messages(context: dict[str, Any]) -> str:
    parts: list[str] = []
    for m in context.get("messages") or []:
        text = m.get("asr_text") or m.get("content") or ""
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def _detect_weak_subjects(blob: str) -> list[str]:
    subjects = [
        ("数学", "数学"),
        ("物理", "物理"),
        ("化学", "化学"),
        ("英语", "英语"),
        ("语文", "语文"),
    ]
    found = [label for key, label in subjects if key in blob]
    return found or ["综合"]


def _last_inbound(context: dict[str, Any]) -> str:
    for m in reversed(context.get("messages") or []):
        if m.get("direction") == "in":
            text = m.get("asr_text") or m.get("content") or ""
            if text:
                return str(text)
    blob = _join_messages(context)
    return blob.split("\n")[-1] if blob else ""


class FakeLLMProvider:
    """Deterministic JSON for local/demo; derives fields from payload context."""

    async def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") or {}
        customer = context.get("customer") or {}
        blob = _join_messages(context)
        parent = customer.get("parent_name") or "家长"
        student = customer.get("student_name") or "学生"
        grade = customer.get("grade") or "未填写"
        stage = customer.get("stage") or "junior"

        if task == "profile":
            weak = _detect_weak_subjects(blob)
            school = customer.get("school") or "未填写"
            intent = "试听" if ("试听" in blob or "体验" in blob) else "咨询"
            goal = "夯实基础" if ("基础" in blob or "薄弱" in blob) else "提升成绩"
            return {
                "basic_info": {
                    "school": school,
                    "grade": grade,
                    "parent": parent,
                    "student": student,
                },
                "study_info": {
                    "weak_subjects": weak,
                    "score_hint": "见近窗聊天" if blob else None,
                    "goal": goal,
                    "intent": intent,
                    "chat_excerpt": blob[:120] if blob else None,
                },
                "prefer_info": {
                    "active_hours": "20:00-22:00",
                    "price_sensitive": "价格" in blob or "便宜" in blob,
                    "decision_style": "谨慎需试听" if intent == "试听" else "信息收集中",
                },
                "timeline": [
                    {
                        "date": "recent",
                        "text": (blob.split("\n")[-1][:80] if blob else f"{parent} 咨询"),
                    }
                ],
                "confidence": 0.72 if blob else 0.5,
                "sources": [
                    {"type": "chat", "label": "近窗聊天"},
                    {"type": "fake_llm", "label": "context-derived"},
                ],
            }

        if task == "reply":
            weak = _detect_weak_subjects(blob)
            subject = weak[0]
            based_on = _last_inbound(context)
            templates = context.get("templates") or []
            tpl_hint = ""
            if templates:
                tpl_hint = str(templates[0].get("title") or templates[0].get("content") or "")[
                    :40
                ]
            scene = context.get("scene") or "sales"
            primary = (
                f"{parent}您好，结合{student}（{grade}）近期{subject}情况，"
                f"建议先安排一次针对性诊断/试听，再讨论班型与价格。"
            )
            if "价格" in blob or "多少" in blob:
                primary = (
                    f"{parent}您好，价格会因班型与课时略有差异；"
                    f"结合{student}{subject}基础，更建议先试听摸清缺口，再给准确方案。"
                )
            alt1 = (
                f"方便的话本周可约{subject}体验课，课后我会把薄弱点与提升路径发给您。"
            )
            alt2 = (
                f"如果时间紧张，也可以先发一份近期试卷/错题，我帮您做初步评估后再约课。"
            )
            if tpl_hint:
                alt2 = f"可参考话术要点「{tpl_hint}」：先价值后报价，邀约到访/试听。"
            return {
                "primary": primary,
                "alternatives": [alt1, alt2],
                "stage": stage,
                "based_on_asr": based_on[:120] if based_on else None,
                "scene": scene,
            }

        if task == "tag_recommend":
            catalog = context.get("tag_catalog") or []
            catalog_names = {t.get("name") for t in catalog if t.get("name")}
            active = {
                t.get("name") for t in (context.get("active_tags") or []) if t.get("name")
            }
            add: list[dict[str, str]] = []
            remove: list[dict[str, str]] = []

            def _maybe_add(name: str, reason: str) -> None:
                if name in catalog_names and name not in active and name not in {
                    a["tag_name"] for a in add
                }:
                    add.append({"tag_name": name, "reason": reason})

            def _maybe_remove(name: str, reason: str) -> None:
                if name in active and name not in {r["tag_name"] for r in remove}:
                    remove.append({"tag_name": name, "reason": reason})

            if "试听" in blob or "体验" in blob:
                _maybe_add("高意向", "近窗提到试听/体验")
                _maybe_add("近期决策", "连续咨询并提到试听")
            if "价格" in blob or "便宜" in blob or "分期" in blob:
                _maybe_add("价格敏感", "近窗讨论价格/分期")
            for subj in _detect_weak_subjects(blob):
                name = f"{subj}薄弱"
                if name in catalog_names:
                    _maybe_add(name, f"近窗提到{subj}")
            if stage == "junior" or (grade and "初" in str(grade)):
                _maybe_add("初中", "客户学段为初中")
            if stage == "primary" or (grade and "小" in str(grade)):
                _maybe_add("小学", "客户学段为小学")
            if stage == "senior" or (grade and "高" in str(grade)):
                _maybe_add("高中", "客户学段为高中")
            if "刚加微信" in active and ("试听" in blob or len(blob) > 40):
                _maybe_remove("刚加微信", "已进入深度咨询")
            if not add and catalog_names:
                # deterministic fallback from catalog
                for name in sorted(catalog_names):
                    if name not in active:
                        _maybe_add(name, "基于近窗上下文的默认推荐")
                        break
            return {"add": add[:5], "remove": remove[:3]}

        return {"task": task, "echo": payload, "provider": "fake"}
