from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.models.all_models import Job, User
from server.app.api.deps import require_operator_user
from server.app.workers.queue import execute_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/{id}")
async def get_job_status(id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found."})
    return {
        "id": job.id,
        "type": job.type,
        "state": job.state,
        "attempts": job.attempts,
        "last_error_code": job.last_error_code,
        "available_at": job.available_at,
        "created_at": job.created_at
    }

@router.post("/{id}/retry")
async def retry_failed_job(
    id: str,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(Job, id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found."})

    job.state = "PENDING"
    job.available_at = datetime.now(timezone.utc)
    job.last_error_code = None
    await db.commit()

    try:
        await execute_job(job)
    except Exception:
        pass

    return {"message": "Job re-queued successfully."}

