"""ai_job helpers: queued → running → success/failed."""

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
    """Mark queued/running jobs stuck longer than older_than as failed."""
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
    job.status = "success"
    job.result_ref_type = result_ref_type
    job.result_ref_id = result_ref_id
    job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()


async def mark_failed(db: AsyncSession, job: AiJob, message: str) -> None:
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()
