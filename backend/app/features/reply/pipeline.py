"""话术建议 AI 流水线：上下文 → LLM → Suggestion → SSE。绝不主动发送企微消息。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_log import write_event
from app.core.models import (
    AiJob,
    ChatMessage,
    Customer,
    CustomerProfile,
    ScriptTemplate,
    Suggestion,
)
from app.core.sse import sse_hub
from app.features.ai import jobs as job_svc
from app.features.ai.gateway import get_gateway


async def load_reply_context(
    db: AsyncSession, customer_id: int, scene: str
) -> dict[str, Any]:
    """加载话术生成上下文：客户、画像摘要、近窗聊天与匹配场景/阶段的话术模板。"""
    customer = await db.get(Customer, customer_id)
    profile = (
        await db.execute(
            select(CustomerProfile).where(CustomerProfile.customer_id == customer_id)
        )
    ).scalar_one_or_none()

    msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.customer_id == customer_id)
            .order_by(ChatMessage.msg_time.desc())
            .limit(10)
        )
    ).scalars().all()

    stage = getattr(customer, "stage", None) if customer else None
    # 启用模板：场景匹配，且阶段相等或模板未限定阶段
    templates = (
        await db.execute(
            select(ScriptTemplate)
            .where(
                ScriptTemplate.enabled.is_(True),
                ScriptTemplate.scene == scene,
                or_(ScriptTemplate.stage == stage, ScriptTemplate.stage.is_(None)),
            )
            .order_by(ScriptTemplate.id)
            .limit(3)
        )
    ).scalars().all()

    return {
        "scene": scene,
        "customer": {
            "id": customer.id if customer else customer_id,
            "parent_name": getattr(customer, "parent_name", None),
            "student_name": getattr(customer, "student_name", None),
            "grade": getattr(customer, "grade", None),
            "school": getattr(customer, "school", None),
            "stage": stage,
        },
        "profile": {
            "basic_info": profile.basic_info if profile else {},
            "study_info": profile.study_info if profile else {},
            "prefer_info": profile.prefer_info if profile else {},
        }
        if profile
        else None,
        "messages": [
            {
                "direction": m.direction,
                "msg_type": m.msg_type,
                "content": m.content,
                "asr_text": m.asr_text,
                "msg_time": m.msg_time.isoformat() if m.msg_time else None,
            }
            for m in reversed(list(msgs))
        ],
        "templates": [
            {
                "id": t.id,
                "title": t.title,
                "stage": t.stage,
                "content": t.content,
            }
            for t in templates
        ],
    }


def parse_reply_output(raw: dict[str, Any], *, stage: str | None) -> dict[str, Any]:
    """规范化 LLM 话术输出：主句必填，备选补齐至 2 条。"""
    primary = raw.get("primary")
    if not primary or not isinstance(primary, str):
        raise ValueError("missing primary")
    alternatives = raw.get("alternatives") or []
    if not isinstance(alternatives, list):
        alternatives = []
    alternatives = [str(a) for a in alternatives if a][:2]
    # 不足 2 条时用占位备选补齐，保证前端结构稳定
    while len(alternatives) < 2:
        alternatives.append(f"备选{len(alternatives) + 2}：可基于同上要点换个语气再发。")
    return {
        "primary": primary.strip(),
        "alternatives": alternatives,
        "stage": raw.get("stage") or stage,
        "based_on_asr": raw.get("based_on_asr"),
    }


async def run_reply_pipeline(
    db: AsyncSession,
    *,
    job: AiJob,
    customer_id: int,
    scene: str,
    user_id: int | None,
) -> Suggestion | None:
    """执行话术建议流水线；LLM 失败时回退 FakeLLM，再失败则标记 job 并推送 SSE。"""
    await job_svc.fail_stuck_jobs(db, customer_id=customer_id, task_type="reply")
    await job_svc.mark_running(db, job)
    await db.commit()

    try:
        context = await load_reply_context(db, customer_id, scene)
        gateway = get_gateway()
        from app.features.ai.providers.fake import FakeLLMProvider

        try:
            raw = await gateway.generate("reply", {"context": context})
            content = parse_reply_output(raw, stage=context["customer"].get("stage"))
        except Exception:  # noqa: BLE001 — LLM schema/timeout → deterministic fallback
            # 结构/超时等问题时用确定性假数据兜底，避免前端空态
            raw = await FakeLLMProvider().generate(
                "reply", {"context": {**context, "scene": scene}}
            )
            content = parse_reply_output(raw, stage=context["customer"].get("stage"))

        suggestion = Suggestion(
            customer_id=customer_id,
            type="reply",
            scene=scene,
            content=content,
            status="pending",
            ai_job_id=job.id,
            created_by_user=user_id,
        )
        db.add(suggestion)
        await db.flush()

        await job_svc.mark_success(
            db, job, result_ref_type="suggestion", result_ref_id=suggestion.id
        )
        await write_event(
            db,
            user_id=user_id,
            action="reply_suggest",
            customer_id=customer_id,
            ref_type="suggestion",
            ref_id=suggestion.id,
            meta={"job_id": job.id, "scene": scene},
        )
        await db.commit()

        await sse_hub.publish(
            customer_id,
            "reply_ready",
            {
                "customer_id": customer_id,
                "suggestion_id": suggestion.id,
                "job_id": job.id,
                "scene": scene,
            },
        )
        return suggestion
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        job = await db.get(AiJob, job.id)
        if job:
            await job_svc.mark_failed(db, job, str(exc))
            await db.commit()
        await sse_hub.publish(
            customer_id,
            "job_failed",
            {
                "job_id": job.id if job else None,
                "task_type": "reply",
                "message": "话术建议暂不可用",
            },
        )
        return None
