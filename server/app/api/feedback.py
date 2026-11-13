from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.models.all_models import Feedback, User
from server.app.schemas import FeedbackCreateRequest
from server.app.api.deps import require_operator_user

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    req: FeedbackCreateRequest,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Feedback).where(
        Feedback.post_id == req.post_id,
        Feedback.agent_id == req.agent_id,
        Feedback.actor_user_id == current_user.id
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        existing.label = req.label
        existing.note = req.note
    else:
        fb = Feedback(
            post_id=req.post_id,
            agent_id=req.agent_id,
            actor_user_id=current_user.id,
            label=req.label,
            note=req.note
        )
        db.add(fb)
    await db.commit()
    return {"message": "Relevance feedback recorded successfully."}

