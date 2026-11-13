from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.core.security import generate_agent_api_key
from server.app.models.all_models import Agent, AgentCredential, Subscription, Job, User
from server.app.schemas import (
    AgentCreateRequest, AgentUpdateRequest, AgentResponse, AgentRegisteredResponse,
    SubscriptionUpdateRequest, SubscriptionResponse, PaginatedResponse
)
from server.app.api.deps import get_current_user, require_operator_user

router = APIRouter(prefix="/agents", tags=["agents"])

def map_agent_response(ag: Agent, sub: Optional[Subscription] = None) -> AgentResponse:
    sub_resp = None
    if sub or ag.subscription:
        s = sub or ag.subscription
        sub_resp = SubscriptionResponse(
            id=s.id,
            agent_id=s.agent_id,
            enabled=s.enabled,
            interest_text=s.interest_text,
            include_topics=s.include_topics,
            exclude_topics=s.exclude_topics,
            accepted_intents=s.accepted_intents,
            excluded_author_ids=s.excluded_author_ids,
            country_codes=s.country_codes,
            language_codes=s.language_codes,
            threshold=float(s.threshold),
            hourly_limit=s.hourly_limit,
            response_mode=s.response_mode,
            version=s.version,
            updated_at=s.updated_at
        )
    return AgentResponse(
        id=ag.id,
        company_name=ag.company_name,
        description=ag.description,
        verification_status=ag.verification_status,
        active=ag.active,
        profile_version=ag.profile_version,
        created_at=ag.created_at,
        updated_at=ag.updated_at,
        subscription=sub_resp
    )

@router.get("", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Agent).order_by(Agent.created_at.asc()).limit(limit)
    res = await db.execute(stmt)
    agents = res.scalars().all()

    items = []
    for ag in agents:
        sub_stmt = select(Subscription).where(Subscription.agent_id == ag.id)
        sub = (await db.execute(sub_stmt)).scalars().first()
        items.append(map_agent_response(ag, sub))

    return PaginatedResponse(data=items, next_cursor=None)

@router.post("", response_model=AgentRegisteredResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    req: AgentCreateRequest,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    agent = Agent(
        owner_user_id=current_user.id,
        company_name=req.company_name,
        description=req.description,
        verification_status=req.verification_status,
        active=True
    )
    db.add(agent)
    await db.flush()

    raw_key, prefix, key_digest = generate_agent_api_key()
    cred = AgentCredential(
        agent_id=agent.id,
        key_prefix=prefix,
        key_digest=key_digest
    )
    db.add(cred)

    sub = Subscription(
        agent_id=agent.id,
        interest_text=req.interest_text,
        include_topics=req.include_topics,
        exclude_topics=req.exclude_topics,
        threshold=req.threshold,
        hourly_limit=req.hourly_limit,
        response_mode=req.response_mode
    )
    db.add(sub)
    await db.flush()

    # Enqueue embedding job
    job = Job(
        type="EMBED_AGENT",
        dedupe_key=f"embed_agent_{agent.id}_{sub.version}",
        payload={"agent_id": agent.id}
    )
    db.add(job)
    await db.commit()

    return AgentRegisteredResponse(
        agent=map_agent_response(agent, sub),
        api_key=raw_key
    )

@router.get("/{id}", response_model=AgentResponse)
async def get_agent(id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, id)
    if not agent:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": "Agent does not exist."})
    sub_stmt = select(Subscription).where(Subscription.agent_id == agent.id)
    sub = (await db.execute(sub_stmt)).scalars().first()
    return map_agent_response(agent, sub)

@router.patch("/{id}", response_model=AgentResponse)
async def update_agent(
    id: str,
    req: AgentUpdateRequest,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    agent = await db.get(Agent, id)
    if not agent:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": "Agent not found."})

    if req.description is not None:
        agent.description = req.description
    if req.active is not None:
        agent.active = req.active
    agent.updated_at = datetime.now(timezone.utc)
    agent.profile_version += 1

    await db.commit()
    sub_stmt = select(Subscription).where(Subscription.agent_id == agent.id)
    sub = (await db.execute(sub_stmt)).scalars().first()
    return map_agent_response(agent, sub)

@router.post("/{id}/keys/rotate")
async def rotate_keys(
    id: str,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    agent = await db.get(Agent, id)
    if not agent:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": "Agent not found."})

    # Revoke existing
    stmt = update(AgentCredential).where(
        AgentCredential.agent_id == id,
        AgentCredential.revoked_at.is_(None)
    ).values(revoked_at=datetime.now(timezone.utc))
    await db.execute(stmt)

    raw_key, prefix, key_digest = generate_agent_api_key()
    new_cred = AgentCredential(
        agent_id=id,
        key_prefix=prefix,
        key_digest=key_digest
    )
    db.add(new_cred)
    await db.commit()

    return {
        "api_key": raw_key,
        "prefix": prefix,
        "message": "Key rotated successfully. Prior keys have been revoked."
    }

@router.get("/{id}/subscription", response_model=SubscriptionResponse)
async def get_subscription(id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Subscription).where(Subscription.agent_id == id)
    sub = (await db.execute(stmt)).scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail={"code": "SUBSCRIPTION_NOT_FOUND", "message": "Subscription not found."})
    return SubscriptionResponse(
        id=sub.id,
        agent_id=sub.agent_id,
        enabled=sub.enabled,
        interest_text=sub.interest_text,
        include_topics=sub.include_topics,
        exclude_topics=sub.exclude_topics,
        accepted_intents=sub.accepted_intents,
        excluded_author_ids=sub.excluded_author_ids,
        country_codes=sub.country_codes,
        language_codes=sub.language_codes,
        threshold=float(sub.threshold),
        hourly_limit=sub.hourly_limit,
        response_mode=sub.response_mode,
        version=sub.version,
        updated_at=sub.updated_at
    )

@router.put("/{id}/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    id: str,
    req: SubscriptionUpdateRequest,
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Subscription).where(Subscription.agent_id == id)
    sub = (await db.execute(stmt)).scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail={"code": "SUBSCRIPTION_NOT_FOUND", "message": "Subscription not found."})

    if req.expected_version is not None and req.expected_version != sub.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": "Subscription was modified concurrently."})

    sub.interest_text = req.interest_text
    sub.include_topics = req.include_topics
    sub.exclude_topics = req.exclude_topics
    sub.accepted_intents = req.accepted_intents
    sub.excluded_author_ids = req.excluded_author_ids
    sub.country_codes = req.country_codes
    sub.language_codes = req.language_codes
    sub.threshold = req.threshold
    sub.hourly_limit = req.hourly_limit
    sub.response_mode = req.response_mode
    sub.version += 1
    sub.updated_at = datetime.now(timezone.utc)

    # Enqueue re-embedding job
    job = Job(
        type="EMBED_AGENT",
        dedupe_key=f"embed_agent_{id}_{sub.version}",
        payload={"agent_id": id}
    )
    db.add(job)
    await db.commit()

    return SubscriptionResponse(
        id=sub.id,
        agent_id=sub.agent_id,
        enabled=sub.enabled,
        interest_text=sub.interest_text,
        include_topics=sub.include_topics,
        exclude_topics=sub.exclude_topics,
        accepted_intents=sub.accepted_intents,
        excluded_author_ids=sub.excluded_author_ids,
        country_codes=sub.country_codes,
        language_codes=sub.language_codes,
        threshold=float(sub.threshold),
        hourly_limit=sub.hourly_limit,
        response_mode=sub.response_mode,
        version=sub.version,
        updated_at=sub.updated_at
    )

