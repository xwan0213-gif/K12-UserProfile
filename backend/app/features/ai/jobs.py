"""ai_job helpers: queued → running → success/failed."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AiJob


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
