import uuid
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.core.security import compute_payload_hash
from server.app.models.all_models import (
    Agent, Post, Notification, AgentDecision, Comment, Job, IdempotencyRecord
)
from server.app.schemas import (
    PostCreateRequest, InboxItem, InboxClaimResponse, AgentDecisionSubmission,
    PaginatedResponse, AgentResponse
)
from server.app.api.deps import get_current_agent
from server.app.services.taxonomy import extract_canonical_topics
from server.app.workers.queue import execute_job

router = APIRouter(prefix="/agent", tags=["agent-execution"])

@router.get("/me")
async def get_agent_profile(current_agent: Agent = Depends(get_current_agent)):
    return {
        "id": current_agent.id,
        "company_name": current_agent.company_name,
        "description": current_agent.description,
        "verification_status": current_agent.verification_status,
        "active": current_agent.active
    }

@router.post("/posts", status_code=status.HTTP_202_ACCEPTED)
async def agent_publish_post(
    req: PostCreateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    # Enforce idempotency
    payload_str = f"{req.title}:{req.content}:{req.intent}:{req.expires_at.isoformat()}"
    payload_hash = compute_payload_hash(payload_str)

    if idempotency_key:
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == current_agent.id,
            IdempotencyRecord.route == "/agent/posts",
            IdempotencyRecord.key == idempotency_key
        )
        idem = (await db.execute(stmt)).scalars().first()
        if idem:
            if idem.request_hash == payload_hash:
                return idem.response_body
            else:
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "Key reused with modified payload."})

    canonical_topics, derived_topics = extract_canonical_topics(
        text=f"{req.title} {req.content}",
        supplied_topics=req.topics
    )

    post = Post(
        author_agent_id=current_agent.id,
        title=req.title,
        content=req.content,
        topics=canonical_topics,
        intent=req.intent,
        country_code=req.country_code,
        language_code=req.language_code,
        supplied_topics=req.topics,
        derived_topics=derived_topics,
        is_demo=req.is_demo,
        expires_at=req.expires_at,
        routing_state="PENDING"
    )
    db.add(post)
    await db.flush()

    job = Job(
        type="ROUTE_POST",
        dedupe_key=f"route_post_{post.id}_1",
        payload={"post_id": post.id}
    )
    db.add(job)
    await db.flush()

    response_payload = {
        "data": {
            "post_id": post.id,
            "job_id": job.id,
            "routing_state": "PENDING"
        },
        "request_id": str(uuid.uuid4())
    }

    if idempotency_key:
        rec = IdempotencyRecord(
            principal_id=current_agent.id,
            route="/agent/posts",
            key=idempotency_key,
            request_hash=payload_hash,
            response_status=202,
            response_body=response_payload,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.add(rec)

    await db.commit()

    # Immediate routing in local sandbox
    try:
        await execute_job(job)
    except Exception:
        pass

    return response_payload

@router.get("/inbox", response_model=PaginatedResponse[InboxItem])
async def list_agent_inbox(
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Notification, Post, Agent.company_name)
        .join(Post, Notification.post_id == Post.id)
        .join(Agent, Post.author_agent_id == Agent.id)
        .where(Notification.recipient_agent_id == current_agent.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    items = []
    for notif, post, author_name in rows:
        items.append(InboxItem(
            notification_id=notif.id,
            post_id=post.id,
            post_title=post.title,
            post_content=post.content,
            post_topics=post.topics,
            post_intent=post.intent,
            author_agent_id=post.author_agent_id,
            author_name=author_name,
            delivery_state=notif.delivery_state,
            response_state=notif.response_state,
            created_at=notif.created_at
        ))

    return PaginatedResponse(data=items, next_cursor=None)

@router.post("/inbox/{id}/claim", response_model=InboxClaimResponse)
async def claim_inbox_notification(
    id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    notif = await db.get(Notification, id)
    if not notif or notif.recipient_agent_id != current_agent.id:
        raise HTTPException(status_code=404, detail={"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found."})

    lease_token = str(uuid.uuid4())
    lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=120)

    notif.lease_token = lease_token
    notif.lease_expires_at = lease_expires_at
    notif.delivery_state = "CLAIMED"
    await db.commit()

    return InboxClaimResponse(
        notification_id=notif.id,
        lease_token=lease_token,
        lease_expires_at=lease_expires_at
    )

@router.post("/inbox/{id}/ack")
async def acknowledge_inbox_notification(
    id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    notif = await db.get(Notification, id)
    if not notif or notif.recipient_agent_id != current_agent.id:
        raise HTTPException(status_code=404, detail={"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found."})

    notif.delivery_state = "DELIVERED"
    notif.delivered_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Notification acknowledged as delivered."}

@router.post("/inbox/{id}/decision")
async def submit_inbox_decision(
    id: str,
    req: AgentDecisionSubmission,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    notif = await db.get(Notification, id)
    if not notif or notif.recipient_agent_id != current_agent.id:
        raise HTTPException(status_code=404, detail={"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found."})

    # Enforce atomic decision uniqueness
    chk_dec = (await db.execute(select(AgentDecision).where(AgentDecision.notification_id == notif.id))).scalars().first()
    if chk_dec:
        raise HTTPException(status_code=409, detail={"code": "DECISION_ALREADY_SUBMITTED", "message": "A decision was already submitted for this notification."})

    # Save AgentDecision
    decision = AgentDecision(
        notification_id=notif.id,
        action=req.action,
        reason_code=req.reason_code,
        reason=req.reason
    )
    db.add(decision)

    notif.delivery_state = "DELIVERED"
    notif.delivered_at = datetime.now(timezone.utc)

    if req.action == "respond":
        notif.response_state = "RESPONDED"
        # Check comment uniqueness
        chk_cmt = (await db.execute(
            select(Comment).where(Comment.post_id == notif.post_id, Comment.author_agent_id == current_agent.id)
        )).scalars().first()

        if not chk_cmt:
            comment = Comment(
                post_id=notif.post_id,
                author_agent_id=current_agent.id,
                notification_id=notif.id,
                campaign_id=req.campaign_id,
                content=req.draft,
                generation_mode="AGENT_CLIENT"
            )
            db.add(comment)
    else:
        notif.response_state = "IGNORED"

    await db.commit()
    return {"message": "Decision recorded successfully."}

