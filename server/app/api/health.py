from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.core.config import settings

router = APIRouter(tags=["health"])

@router.get("/health/live")
async def health_live():
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@router.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return {
        "status": "ready" if db_status == "connected" else "degraded",
        "database": db_status,
        "provider_mode": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "routing_policy": settings.ROUTING_POLICY_VERSION
    }

