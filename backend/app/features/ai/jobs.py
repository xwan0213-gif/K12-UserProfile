"""AI 异步任务状态辅助：queued → running → success/failed，及卡住超时清理。"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AiJob
from app.core.timeutil import utcnow_naive

STUCK_TIMEOUT = timedelta(minutes=5)


async def create_job(
    db: AsyncSession,
    *,
    customer_id: int,
    task_type: str,
    created_by: int | None,
    request: dict[str, Any] | None = None,
) -> AiJob:
    """创建 queued 状态的 AiJob 并 flush，返回已分配主键的实体。

    参数:
        db: 异步会话
        customer_id: 关联客户
        task_type: 任务类型（如 profile / reply）
        created_by: 发起人用户 id，可为 None
        request: 请求快照 JSON，默认空 dict
    副作用:
        向会话 add + flush（未 commit）
    """
    job = AiJob(
        customer_id=customer_id,
        task_type=task_type,
        status="queued",
        request=request or {},
        created_by=created_by,
    )
    db.add(job)
    await db.flush()
    return job


async def fail_stuck_jobs(
    db: AsyncSession,
    *,
    customer_id: int,
    task_type: str,
    older_than: timedelta = STUCK_TIMEOUT,
) -> int:
    """将超时仍处于 queued/running 的任务标为 failed。

    参数:
        older_than: 相对创建时间的超时阈值，默认 5 分钟
    返回:
        被标记失败的条数
    副作用:
        更新 status / error_message / finished_at，有变更时 flush
    """
    cutoff = utcnow_naive() - older_than
    rows = (
        await db.execute(
            select(AiJob).where(
                AiJob.customer_id == customer_id,
                AiJob.task_type == task_type,
                AiJob.status.in_(("queued", "running")),
                AiJob.created_at < cutoff,
            )
        )
    ).scalars().all()
    for job in rows:
        job.status = "failed"
        job.error_message = "timeout: stuck >5min"
        job.finished_at = utcnow_naive()
    if rows:
        await db.flush()
    return len(rows)


async def mark_running(db: AsyncSession, job: AiJob) -> None:
    """将任务标为 running，记录开始时间（UTC naive）并 flush。"""
    job.status = "running"
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()


async def mark_success(
    db: AsyncSession,
    job: AiJob,
    *,
    result_ref_type: str,
    result_ref_id: int,
) -> None:
    """将任务标为 success，写入结果引用类型/id 与结束时间并 flush。

    参数:
        result_ref_type: 结果实体类型（如 draft）
        result_ref_id: 结果实体主键
    """
    job.status = "success"
    job.result_ref_type = result_ref_type
    job.result_ref_id = result_ref_id
    job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()


async def mark_failed(db: AsyncSession, job: AiJob, message: str) -> None:
    """将任务标为 failed，写入错误信息与结束时间并 flush。"""
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()
