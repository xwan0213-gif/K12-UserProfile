"""标签推荐 AI 流水线：当前标签 + 标签目录 + 聊天 → Suggestion(type=tag) → SSE。"""

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
    Suggestion,
    TagDef,
)
from app.core.sse import sse_hub
from app.features.ai import jobs as job_svc
from app.features.ai.gateway import get_gateway


async def load_tag_context(db: AsyncSession, customer_id: int) -> dict[str, Any]:
    """加载标签推荐上下文：客户、画像、已挂标签、启用标签目录与近窗聊天。"""
    customer = await db.get(Customer, customer_id)
    profile = (
        await db.execute(
            select(CustomerProfile).where(CustomerProfile.customer_id == customer_id)
        )
    ).scalar_one_or_none()

    active_rows = (
        await db.execute(
            select(CustomerTag, TagDef)
            .join(TagDef, TagDef.id == CustomerTag.tag_id)
            .where(
                CustomerTag.customer_id == customer_id,
                TagDef.deleted_at.is_(None),
            )
        )
    ).all()

    catalog = (
        await db.execute(
            select(TagDef)
            .where(TagDef.deleted_at.is_(None), TagDef.enabled.is_(True))
            .order_by(TagDef.sort_order, TagDef.id)
        )
    ).scalars().all()

    msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.customer_id == customer_id)
            .order_by(ChatMessage.msg_time.desc())
            .limit(30)
        )
    ).scalars().all()

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
        "active_tags": [
            {"tag_id": tag.id, "name": tag.name, "customer_tag_id": ct.id}
            for ct, tag in active_rows
        ],
        "tag_catalog": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "sop_text": t.sop_text,
            }
            for t in catalog
        ],
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
    }


def parse_tag_output(raw: dict[str, Any]) -> dict[str, Any]:
    """规范化 LLM 标签推荐输出为 {add, remove}，每项含 tag_name/reason。"""
    add_raw = raw.get("add") or []
    remove_raw = raw.get("remove") or []
    if not isinstance(add_raw, list) or not isinstance(remove_raw, list):
        raise ValueError("add/remove must be lists")

    def _norm(items: list[Any]) -> list[dict[str, str]]:
        """兼容字符串或 dict 两种推荐项格式。"""
        out: list[dict[str, str]] = []
        for item in items:
            if isinstance(item, str):
                out.append({"tag_name": item, "reason": ""})
            elif isinstance(item, dict) and item.get("tag_name"):
                out.append(
                    {
                        "tag_name": str(item["tag_name"]),
                        "reason": str(item.get("reason") or ""),
                    }
                )
        return out

    return {"add": _norm(add_raw), "remove": _norm(remove_raw)}


async def run_tag_recommend_pipeline(
    db: AsyncSession,
    *,
    job: AiJob,
    customer_id: int,
    user_id: int | None,
) -> Suggestion | None:
    """执行标签推荐流水线；空推荐或 LLM 失败时回退 FakeLLM，再失败则推送 job_failed。"""
    await job_svc.fail_stuck_jobs(
        db, customer_id=customer_id, task_type="tag_recommend"
    )
    await job_svc.mark_running(db, job)
    await db.commit()

    try:
        context = await load_tag_context(db, customer_id)
        gateway = get_gateway()
        from app.features.ai.providers.fake import FakeLLMProvider

        try:
            raw = await gateway.generate("tag_recommend", {"context": context})
            content = parse_tag_output(raw)
            # 增删皆空视为无效输出，触发下方兜底
            if not content["add"] and not content["remove"]:
                raise ValueError("empty recommendations")
        except Exception:  # noqa: BLE001
            raw = await FakeLLMProvider().generate(
                "tag_recommend", {"context": context}
            )
            content = parse_tag_output(raw)

        suggestion = Suggestion(
            customer_id=customer_id,
            type="tag",
            scene=None,
            content=content,
            status="pending",
            ai_job_id=job.id,
            created_by_user=user_id,
        )
        db.add(suggestion)
        await db.flush()

        old_rows = (
            await db.execute(
                select(Suggestion).where(
                    Suggestion.customer_id == customer_id,
                    Suggestion.type == "tag",
                    Suggestion.id != suggestion.id,
                    Suggestion.status.in_(("pending", "shown")),
                )
            )
        ).scalars().all()
        for old in old_rows:
            old.status = "superseded"

        await job_svc.mark_success(
            db, job, result_ref_type="suggestion", result_ref_id=suggestion.id
        )
        await write_event(
            db,
            user_id=user_id,
            action="tag_recommend",
            customer_id=customer_id,
            ref_type="suggestion",
            ref_id=suggestion.id,
            meta={"job_id": job.id},
        )
        await db.commit()

        await sse_hub.publish(
            customer_id,
            "tag_recommend",
            {
                "customer_id": customer_id,
                "suggestion_id": suggestion.id,
                "job_id": job.id,
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
                "task_type": "tag_recommend",
                "message": "标签推荐暂不可用",
            },
        )
        return None
