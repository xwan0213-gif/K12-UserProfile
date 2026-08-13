"""日程 AI 流水线：组装上下文 → LLM → Suggestion(type=schedule) → SSE。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_log import write_event
from app.core.models import (
    AiJob,
    ChatMessage,
    Customer,
    CustomerProfile,
    CustomerTag,
    OrderRecord,
    Suggestion,
    TagDef,
)
from app.core.sse import sse_hub
from app.features.ai import jobs as job_svc
from app.features.ai.gateway import get_gateway


async def load_schedule_context(db: AsyncSession, customer_id: int) -> dict[str, Any]:
    """拉取客户画像、近期消息、订单与标签，供日程 LLM 使用。"""
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
            .limit(30)
        )
    ).scalars().all()

    orders = (
        await db.execute(
            select(OrderRecord)
            .where(OrderRecord.customer_id == customer_id)
            .order_by(OrderRecord.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    tag_rows = (
        await db.execute(
            select(CustomerTag, TagDef)
            .join(TagDef, TagDef.id == CustomerTag.tag_id)
            .where(
                CustomerTag.customer_id == customer_id,
                TagDef.deleted_at.is_(None),
            )
        )
    ).all()

    return {
        "customer": {
            "id": customer.id if customer else customer_id,
            "parent_name": getattr(customer, "parent_name", None),
            "student_name": getattr(customer, "student_name", None),
            "grade": getattr(customer, "grade", None),
            "school": getattr(customer, "school", None),
            "stage": getattr(customer, "stage", None),
        },
        "profile": {
            "basic_info": profile.basic_info if profile else {},
            "study_info": profile.study_info if profile else {},
            "prefer_info": profile.prefer_info if profile else {},
        }
        if profile
        else None,
        # 查询按时间倒序，返回前再翻转为时间正序
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
        "orders": [
            {
                "id": o.id,
                "title": o.title,
                "status": o.status,
                "amount": float(o.amount) if o.amount is not None else None,
                "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            }
            for o in orders
        ],
        "active_tags": [
            {"tag_id": tag.id, "name": tag.name}
            for _, tag in tag_rows
        ],
        "tags": [tag.name for _, tag in tag_rows],
    }


def parse_schedule_output(raw: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化 LLM 日程输出；缺 title 则抛错。"""
    title = raw.get("title")
    if not title or not isinstance(title, str):
        raise ValueError("missing title")
    priority = raw.get("priority") or "medium"
    if priority not in ("high", "medium", "low"):
        priority = "medium"
    start_at = raw.get("start_at")
    if start_at is not None and not isinstance(start_at, str):
        start_at = str(start_at)
    return {
        "title": title.strip()[:200],
        "time_text": (raw.get("time_text") or "待定"),
        "start_at": start_at,
        "priority": priority,
        "source_quote": raw.get("source_quote"),
        "predictive_tip": raw.get("predictive_tip"),
        "remark": raw.get("remark") or raw.get("predictive_tip"),
    }


async def run_schedule_pipeline(
    db: AsyncSession,
    *,
    job: AiJob,
    customer_id: int,
    user_id: int | None,
) -> Suggestion | None:
    """执行日程建议任务：成功写 Suggestion 并推 SSE，失败标记 job 并推 job_failed。"""
    await job_svc.fail_stuck_jobs(db, customer_id=customer_id, task_type="schedule")
    await job_svc.mark_running(db, job)
    await db.commit()

    try:
        context = await load_schedule_context(db, customer_id)
        gateway = get_gateway()
        from app.features.ai.providers.fake import FakeLLMProvider

        try:
            raw = await gateway.generate("schedule", {"context": context})
            content = parse_schedule_output(raw)
        except Exception:  # noqa: BLE001 — LLM 结构/超时 → 确定性假数据回退
            raw = await FakeLLMProvider().generate(
                "schedule", {"context": context}
            )
            content = parse_schedule_output(raw)

        suggestion = Suggestion(
            customer_id=customer_id,
            type="schedule",
            scene=None,
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
            action="schedule_suggest",
            customer_id=customer_id,
            ref_type="suggestion",
            ref_id=suggestion.id,
            meta={"job_id": job.id},
        )
        await db.commit()

        await sse_hub.publish(
            customer_id,
            "schedule_draft",
            {
                "customer_id": customer_id,
                "suggestion_id": suggestion.id,
                "job_id": job.id,
                "title": content.get("title"),
                "time_text": content.get("time_text"),
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
                "task_type": "schedule",
                "message": "日程建议暂不可用",
            },
        )
        return None
