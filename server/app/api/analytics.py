from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.models.all_models import (
    Post, Agent, Notification, Comment, Job, RouteRun, ModelRun
)
from server.app.core.config import settings

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    total_posts = (await db.execute(select(func.count(Post.id)))).scalar() or 0
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar() or 0
    total_notifications = (await db.execute(select(func.count(Notification.id)))).scalar() or 0
    delivered_notifications = (await db.execute(
        select(func.count(Notification.id)).where(Notification.delivery_state == "DELIVERED")
    )).scalar() or 0
    total_comments = (await db.execute(select(func.count(Comment.id)))).scalar() or 0
    pending_jobs = (await db.execute(
        select(func.count(Job.id)).where(Job.state == "PENDING")
    )).scalar() or 0

    avg_model_duration = (await db.execute(
        select(func.avg(ModelRun.duration_ms)).where(ModelRun.status == "SUCCESS")
    )).scalar() or 0.0

    delivery_rate = (delivered_notifications / total_notifications * 100) if total_notifications > 0 else 100.0
    engagement_rate = (total_comments / delivered_notifications * 100) if delivered_notifications > 0 else 0.0

    return {
        "overview": {
            "total_posts": total_posts,
            "total_agents": total_agents,
            "total_notifications": total_notifications,
            "delivered_notifications": delivered_notifications,
            "total_comments": total_comments,
            "pending_jobs": pending_jobs,
            "delivery_rate_pct": round(delivery_rate, 2),
            "engagement_rate_pct": round(engagement_rate, 2),
            "avg_llm_duration_ms": round(float(avg_model_duration), 1)
        },
        "system": {
            "routing_policy": settings.ROUTING_POLICY_VERSION,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL
        }
    }

