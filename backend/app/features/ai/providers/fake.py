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
            if scene in ("cs", "service"):
                return _fake_cs_reply(
                    parent=parent,
                    student=student,
                    grade=grade,
                    stage=stage,
                    subject=subject,
                    blob=blob,
                    based_on=based_on,
                    tpl_hint=tpl_hint,
                    scene="cs",
                )
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

        if task == "schedule":
            return _fake_schedule(context, blob=blob, parent=parent, student=student)

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


def _fake_cs_reply(
    *,
    parent: str,
    student: str,
    grade: str,
    stage: str | None,
    subject: str,
    blob: str,
    based_on: str,
    tpl_hint: str,
    scene: str,
) -> dict[str, Any]:
    """Service-oriented wording: 补课/投诉/续费/到课 — not sales 试听逼单."""
    if "投诉" in blob or "不满" in blob or "差评" in blob:
        primary = (
            f"{parent}您好，非常理解您的着急。关于{student}近期上课体验，"
            f"我们会在24小时内给出补课/换班方案，并同步班主任跟进。"
        )
        alt1 = f"先跟您确认问题节点：是内容听不懂、到课冲突，还是师资匹配？我们按点处理。"
        alt2 = f"若需要，可先安排一次{subject}补课，把缺口补上后再看后续班型。"
    elif "续费" in blob or "到期" in blob or "延期" in blob:
        primary = (
            f"{parent}您好，{student}（{grade}）课程临近节点，"
            f"我帮您梳理剩余课时、续费档位与到课安排，方便您对照选择。"
        )
        alt1 = "续费可保留原班次优先名额；若时间冲突，我们可先调课再谈续费。"
        alt2 = "需要的话我发一份学情小结+续费对照表，您看完再决定。"
    elif "请假" in blob or "补课" in blob or "缺课" in blob:
        primary = (
            f"{parent}您好，已记录{student}请假诉求。我们可协调同进度补课或录播跟进，"
            f"并确认下次到课时间，避免进度掉队。"
        )
        alt1 = "请您告知方便补课的时段，我帮您锁定教室与老师档期。"
        alt2 = "若本周无法到课，也可先完成作业打卡，补课后我再做学情回访。"
    elif "到课" in blob or "签到" in blob or "上课" in blob:
        primary = (
            f"{parent}您好，提醒一下{student}本周到课安排；"
            f"如有冲突请提前说，我们按规则办理请假/补课，不影响后续进度。"
        )
        alt1 = "到课前一天我会再弱提醒一次，您不用额外操心。"
        alt2 = "若路上延误，请先发消息，我们尽量保留座位与讲义。"
    else:
        primary = (
            f"{parent}您好，关于{student}（{grade}）课后服务，"
            f"我这边可协助处理补课、到课确认、学情反馈或续费说明，请告诉我您最关心的一点。"
        )
        alt1 = f"若是{subject}跟不上，优先安排补课与错题回顾，比换班更稳妥。"
        alt2 = "投诉与退费诉求我们会按流程受理，先倾听再给可行方案。"
    if tpl_hint:
        alt2 = f"可参考客服话术「{tpl_hint}」：先安抚确认诉求，再给补课/到课/续费方案。"
    return {
        "primary": primary,
        "alternatives": [alt1, alt2],
        "stage": stage,
        "based_on_asr": based_on[:120] if based_on else None,
        "scene": scene,
    }


def _fake_schedule(
    context: dict[str, Any],
    *,
    blob: str,
    parent: str,
    student: str,
) -> dict[str, Any]:
    """Parse time/intent phrases → schedule draft JSON + optional predictive tip."""
    quote = ""
    for m in reversed(context.get("messages") or []):
        text = str(m.get("asr_text") or m.get("content") or "")
        if any(
            k in text
            for k in ("下周", "周六", "周天", "周日", "试听", "回访", "续费", "补课", "到访")
        ):
            quote = text
            break
    if not quote:
        quote = (blob.split("\n")[-1] if blob else "")[:80]

    title = f"跟进{parent}/{student}"
    time_text = "待定"
    priority = "medium"
    start_at = None

    if "试听" in blob or "体验" in blob:
        title = "试听安排/回访确认"
        priority = "high"
    elif "回访" in blob:
        title = "课后回访"
        priority = "high"
    elif "续费" in blob or "到期" in blob:
        title = "续费沟通"
        priority = "high"
    elif "补课" in blob or "请假" in blob:
        title = "补课协调"
        priority = "medium"
    elif "到访" in blob or "看课" in blob:
        title = "到访看课"

    if "下周六" in blob:
        time_text = "下周六 待定"
    elif "周六" in blob:
        time_text = "本周六 待定"
    elif "下周" in blob:
        time_text = "下周 待定"
    elif "周日" in blob or "周天" in blob:
        time_text = "周日 待定"

    predictive_tip = None
    orders = context.get("orders") or []
    tags = context.get("tags") or context.get("active_tags") or []
    tag_names = {
        (t.get("name") if isinstance(t, dict) else str(t)) for t in tags
    }
    if any("续费" in str(t) for t in tag_names) or any(
        "续费" in str(o.get("title") or "") for o in orders if isinstance(o, dict)
    ):
        predictive_tip = "续费窗口临近，建议提前安排一对一沟通"
    elif any("试听" in str(t) for t in tag_names) or "试听" in blob:
        predictive_tip = "试听后建议 48h 内回访，确认意向与档期"
    elif orders:
        predictive_tip = "已有成交/体验订单，可安排到课提醒或学情回访"
    else:
        predictive_tip = "根据近窗沟通，建议预留一次跟进待办"

    return {
        "title": title,
        "time_text": time_text,
        "start_at": start_at,
        "priority": priority,
        "source_quote": quote[:120] if quote else None,
        "predictive_tip": predictive_tip,
        "remark": predictive_tip,
    }
