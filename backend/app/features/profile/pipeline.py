"""画像 AI 流水线：加载上下文 → 构造 Prompt → LLM → 解析 → 写入草稿 → SSE 推送。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_log import write_event
from app.core.models import (
    AiJob,
    ChatMessage,
    CsSummary,
    Customer,
    CustomerProfile,
    OrderRecord,
    ProfileDraft,
)
from app.core.sse import sse_hub
from app.core.timeutil import utcnow_naive
from app.features.ai.gateway import get_gateway
from app.features.ai import jobs as job_svc


async def load_context(db: AsyncSession, customer_id: int) -> dict[str, Any]:
    """加载画像生成所需上下文：客户基本信息、已确认画像、近窗聊天、订单与客服摘要。"""
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
            .limit(50)
        )
    ).scalars().all()

    orders = (
        await db.execute(
            select(OrderRecord).where(OrderRecord.customer_id == customer_id)
        )
    ).scalars().all()

    cs = (
        await db.execute(
            select(CsSummary).where(CsSummary.customer_id == customer_id)
        )
    ).scalar_one_or_none()

    return {
        "customer": {
            "id": customer.id if customer else customer_id,
            "parent_name": getattr(customer, "parent_name", None),
            "student_name": getattr(customer, "student_name", None),
            "grade": getattr(customer, "grade", None),
            "school": getattr(customer, "school", None),
            "stage": getattr(customer, "stage", None),
        },
        "confirmed_summary": {
            "basic_info": profile.basic_info if profile else {},
            "study_info": profile.study_info if profile else {},
            "prefer_info": profile.prefer_info if profile else {},
            "timeline": profile.timeline if profile else [],
            "version": profile.version if profile else 0,
        }
        if profile
        else None,
        # DB 按时间倒序取近窗，组装时再翻为正序，便于模型理解对话脉络
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
                "external_order_no": o.external_order_no,
                "title": o.title,
                "amount": float(o.amount) if o.amount is not None else None,
                "status": o.status,
            }
            for o in orders
        ],
        "cs_summary": cs.summary_text if cs else None,
    }


def build_prompt(context: dict[str, Any]) -> str:
    """根据上下文构造画像抽取 Prompt。"""
    return (
        "Extract a K12 customer 360 profile as JSON with keys "
        "basic_info, study_info, prefer_info, timeline, confidence, sources.\n"
        f"Context:\n{context}"
    )


def parse_profile_output(raw: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化 LLM 输出；缺失必填字段时抛出 ValueError。"""
    required = ("basic_info", "study_info", "prefer_info", "timeline")
    for key in required:
        if key not in raw:
            raise ValueError(f"missing field: {key}")
    confidence = raw.get("confidence", 0.7)
    sources = raw.get("sources") or [{"type": "chat", "label": "近窗聊天"}]
    return {
        "basic_info": raw["basic_info"] or {},
        "study_info": raw["study_info"] or {},
        "prefer_info": raw["prefer_info"] or {},
        "timeline": raw["timeline"] or [],
        "confidence": confidence,
        "sources": sources,
        "field_status": {
            "basic_info": "draft",
            "study_info": "draft",
            "prefer_info": "draft",
            "timeline": "draft",
        },
    }


async def run_profile_pipeline(
    db: AsyncSession,
    *,
    job: AiJob,
    customer_id: int,
    user_id: int | None,
) -> ProfileDraft | None:
    """执行画像生成流水线：成功写草稿并推送 SSE，失败标记 job 并推送 job_failed。"""
    await job_svc.mark_running(db, job)
    await db.commit()

    try:
        context = await load_context(db, customer_id)
        prompt = build_prompt(context)
        gateway = get_gateway()
        raw = await gateway.generate("profile", {"prompt": prompt, "context": context})
        try:
            parsed = parse_profile_output(raw)
        except ValueError:
            # 解析失败时重试一次，强调仅返回合法 JSON
            raw = await gateway.generate(
                "profile", {"prompt": prompt + "\nRetry: valid JSON only.", "context": context}
            )
            parsed = parse_profile_output(raw)

        draft = ProfileDraft(
            customer_id=customer_id,
            basic_info=parsed["basic_info"],
            study_info=parsed["study_info"],
            prefer_info=parsed["prefer_info"],
            timeline=parsed["timeline"],
            field_status=parsed["field_status"],
            confidence=Decimal(str(parsed["confidence"])),
            sources=parsed["sources"],
            status="draft",
            ai_job_id=job.id,
            created_by="ai",
        )
        db.add(draft)
        await db.flush()

        await job_svc.mark_success(
            db, job, result_ref_type="profile_draft", result_ref_id=draft.id
        )
        await write_event(
            db,
            user_id=user_id,
            action="profile_generate",
            customer_id=customer_id,
            ref_type="profile_draft",
            ref_id=draft.id,
            meta={"job_id": job.id},
        )
        await db.commit()

        await sse_hub.publish(
            customer_id,
            "profile_draft",
            {
                "customer_id": customer_id,
                "draft_id": draft.id,
                "confidence": float(draft.confidence) if draft.confidence is not None else None,
                "job_id": job.id,
            },
        )
        return draft
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        # rollback 后需重新加载 job，再写入失败状态
        job = await db.get(AiJob, job.id)
        if job:
            await job_svc.mark_failed(db, job, str(exc))
            await db.commit()
        await sse_hub.publish(
            customer_id,
            "job_failed",
            {
                "job_id": job.id if job else None,
                "task_type": "profile",
                "message": "分析暂不可用",
            },
        )
        return None
