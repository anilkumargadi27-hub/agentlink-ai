from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.core.security import compute_payload_hash
from server.app.models.all_models import (
    Post, Agent, Comment, RouteRun, RouteDecision, Job, IdempotencyRecord, User
)
from server.app.schemas import (
    PostCreateRequest, PostResponse, CommentResponse, RoutingInspectorResponse,
    RouteDecisionItem, PaginatedResponse
)
from server.app.services.taxonomy import extract_canonical_topics
from server.app.api.deps import require_operator_user, get_current_user
from server.app.workers.queue import execute_job

router = APIRouter(tags=["posts"])

@router.get("/posts", response_model=PaginatedResponse[PostResponse])
async def list_posts(
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Post, Agent.company_name, func.count(Comment.id).label("comment_count"))
        .join(Agent, Post.author_agent_id == Agent.id)
        .outerjoin(Comment, Post.id == Comment.post_id)
        .group_by(Post.id, Agent.company_name)
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for post, author_name, comment_count in rows:
        items.append(PostResponse(
            id=post.id,
            author_agent_id=post.author_agent_id,
            author_name=author_name,
            title=post.title,
            content=post.content,
            topics=post.topics,
            intent=post.intent,
            country_code=post.country_code,
            language_code=post.language_code,
            is_demo=post.is_demo,
            expires_at=post.expires_at,
            routing_state=post.routing_state,
            moderation_state=post.moderation_state,
            created_at=post.created_at,
            comment_count=comment_count
        ))

    return PaginatedResponse(data=items, next_cursor=None)

@router.get("/posts/{id}", response_model=PostResponse)
async def get_post(id: str, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})
    agent = await db.get(Agent, post.author_agent_id)
    c_count = (await db.execute(select(func.count(Comment.id)).where(Comment.post_id == post.id))).scalar() or 0

    return PostResponse(
        id=post.id,
        author_agent_id=post.author_agent_id,
        author_name=agent.company_name if agent else "Unknown",
        title=post.title,
        content=post.content,
        topics=post.topics,
        intent=post.intent,
        country_code=post.country_code,
        language_code=post.language_code,
        is_demo=post.is_demo,
        expires_at=post.expires_at,
        routing_state=post.routing_state,
        moderation_state=post.moderation_state,
        created_at=post.created_at,
        comment_count=c_count
    )

@router.post("/agents/{id}/posts", status_code=status.HTTP_202_ACCEPTED)
async def operator_publish_post(
    id: str,
    req: PostCreateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_operator_user),
    db: AsyncSession = Depends(get_db)
):
    agent = await db.get(Agent, id)
    if not agent or not agent.active:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": "Target agent not active."})

    # Validate idempotency
    payload_str = f"{req.title}:{req.content}:{req.intent}:{req.expires_at.isoformat()}"
    payload_hash = compute_payload_hash(payload_str)
    
    if idempotency_key:
        idem_stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == current_user.id,
            IdempotencyRecord.route == f"/agents/{id}/posts",
            IdempotencyRecord.key == idempotency_key
        )
        idem = (await db.execute(idem_stmt)).scalars().first()
        if idem:
            if idem.request_hash == payload_hash:
                return idem.response_body
            else:
                raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "Idempotency key reused with modified payload."})

    # Extract canonical topics
    canonical_topics, derived_topics = extract_canonical_topics(
        text=f"{req.title} {req.content}",
        supplied_topics=req.topics
    )

    # Atomic Post & Job insertion
    post = Post(
        author_agent_id=agent.id,
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
        "message": "Post submitted for semantic routing."
    }

    if idempotency_key:
        idem_rec = IdempotencyRecord(
            principal_id=current_user.id,
            route=f"/agents/{id}/posts",
            key=idempotency_key,
            request_hash=payload_hash,
            response_status=202,
            response_body=response_payload,
            expires_at=datetime.now(timezone.utc)
        )
        db.add(idem_rec)

    await db.commit()

    # In local development mode, execute immediate routing inline for responsive UX
    try:
        await execute_job(job)
    except Exception:
        pass

    return response_payload

@router.get("/posts/{id}/comments", response_model=PaginatedResponse[CommentResponse])
async def list_comments(id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Comment, Agent.company_name)
        .join(Agent, Comment.author_agent_id == Agent.id)
        .where(Comment.post_id == id)
        .order_by(Comment.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    items = []
    for comment, agent_name in rows:
        items.append(CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author_agent_id=comment.author_agent_id,
            author_name=agent_name,
            notification_id=comment.notification_id,
            campaign_id=comment.campaign_id,
            content=comment.content,
            generation_mode=comment.generation_mode,
            created_at=comment.created_at
        ))

    return PaginatedResponse(data=items, next_cursor=None)

@router.get("/posts/{id}/routing", response_model=RoutingInspectorResponse)
async def get_post_routing(id: str, db: AsyncSession = Depends(get_db)):
    """
    Route Inspector endpoint. Returns all candidate decisions, scores, and evidence.
    """
    post = await db.get(Post, id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})

    stmt = select(RouteRun).where(RouteRun.post_id == id).order_by(RouteRun.created_at.desc()) if hasattr(RouteRun, 'created_at') else select(RouteRun).where(RouteRun.post_id == id)
    route_run = (await db.execute(stmt)).scalars().first()

    if not route_run:
        raise HTTPException(status_code=404, detail={"code": "ROUTING_PENDING", "message": "Routing has not run for this post yet."})

    dec_stmt = (
        select(RouteDecision, Agent.company_name)
        .join(Agent, RouteDecision.agent_id == Agent.id)
        .where(RouteDecision.route_run_id == route_run.id)
        .order_by(RouteDecision.final_score.desc().nullslast(), Agent.company_name.asc())
    )
    dec_rows = (await db.execute(dec_stmt)).all()

    decisions = []
    for d, company_name in dec_rows:
        decisions.append(RouteDecisionItem(
            agent_id=d.agent_id,
            agent_name=company_name,
            eligible=d.eligible,
            dense_score=float(d.dense_score) if d.dense_score is not None else None,
            topic_score=float(d.topic_score) if d.topic_score is not None else None,
            compatibility_score=float(d.compatibility_score) if d.compatibility_score is not None else None,
            final_score=float(d.final_score) if d.final_score is not None else None,
            threshold=float(d.threshold),
            decision=d.decision,
            reason_codes=d.reason_codes,
            evidence=d.evidence
        ))

    return RoutingInspectorResponse(
        post_id=post.id,
        route_run_id=route_run.id,
        policy_version=route_run.policy_version,
        model_revision=route_run.model_revision,
        candidate_count=route_run.candidate_count,
        eligible_count=route_run.eligible_count,
        selected_count=route_run.selected_count,
        started_at=route_run.started_at,
        completed_at=route_run.completed_at,
        decisions=decisions
    )

