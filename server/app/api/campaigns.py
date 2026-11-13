from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.models.all_models import Campaign, Agent, User
from server.app.schemas import CampaignCreateRequest, CampaignResponse
from server.app.api.deps import require_operator_user, get_current_user

router = APIRouter(tags=["campaigns"])

@router.get("/agents/{id}/campaigns", response_model=List[CampaignResponse])
async def list_agent_campaigns(id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Campaign).where(Campaign.agent_id == id).order_by(Campaign.created_at.desc())
    res = await db.execute(stmt)
    campaigns = res.scalars().all()
    return [
        CampaignResponse(
            id=c.id,
            agent_id=c.agent_id,
            title=c.title,
            approved_terms=c.approved_terms,
            allowed_topics=c.allowed_topics,
            starts_at=c.starts_at,
            expires_at=c.expires_at,
            is_demo=c.is_demo,
            active=c.active,
            created_at=c.created_at
        )
        for c in campaigns
    ]

@router.post("/agents/{id}/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_campaign(
    id: str,
    req: CampaignCreateRequest,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    agent = await db.get(Agent, id)
    if not agent:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": "Agent not found."})

    existing = await db.get(Campaign, req.id)
    if existing:
        raise HTTPException(status_code=409, detail={"code": "CAMPAIGN_EXISTS", "message": "Campaign ID already exists."})

    campaign = Campaign(
        id=req.id,
        agent_id=agent.id,
        title=req.title,
        approved_terms=req.approved_terms,
        allowed_topics=req.allowed_topics,
        starts_at=req.starts_at,
        expires_at=req.expires_at,
        is_demo=req.is_demo,
        active=True
    )
    db.add(campaign)
    await db.commit()

    return CampaignResponse(
        id=campaign.id,
        agent_id=campaign.agent_id,
        title=campaign.title,
        approved_terms=campaign.approved_terms,
        allowed_topics=campaign.allowed_topics,
        starts_at=campaign.starts_at,
        expires_at=campaign.expires_at,
        is_demo=campaign.is_demo,
        active=campaign.active,
        created_at=campaign.created_at
    )

