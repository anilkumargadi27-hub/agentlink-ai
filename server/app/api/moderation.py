from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.models.all_models import Post, Job, User
from server.app.schemas import ModerationDecisionRequest
from server.app.api.deps import require_operator_user
from server.app.workers.queue import execute_job

router = APIRouter(prefix="/moderation", tags=["moderation"])

@router.get("")
async def list_held_posts(
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Post).where(Post.moderation_state == "HELD").order_by(Post.created_at.desc())
    res = await db.execute(stmt)
    posts = res.scalars().all()
    return posts

@router.post("/{post_id}/decision")
async def decide_post_moderation(
    post_id: str,
    req: ModerationDecisionRequest,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})

    post.moderation_state = "ALLOWED" if req.decision == "ALLOW" else "REJECTED"
    
    if req.decision == "ALLOW":
        job = Job(
            type="ROUTE_POST",
            dedupe_key=f"route_post_{post.id}_moderated",
            payload={"post_id": post.id}
        )
        db.add(job)
        await db.commit()
        try:
            await execute_job(job)
        except Exception:
            pass
    else:
        await db.commit()

    return {"message": f"Post moderation state set to {post.moderation_state}."}

