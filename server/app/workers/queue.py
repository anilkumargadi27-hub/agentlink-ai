import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.config import settings
from server.app.core.database import AsyncSessionLocal
from server.app.models.all_models import (
    Job, Post, PostEmbedding, Agent, Subscription, AgentEmbedding,
    RouteRun, RouteDecision, Notification, AgentDecision, Comment,
    Campaign, ModelRun
)
from server.app.services.embeddings import embed_text
from server.app.services.routing import compute_hybrid_routing
from server.app.agents.prompts.decision import build_decision_prompt
from server.app.agents.adapter import llm_adapter

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

async def claim_next_job(session: AsyncSession) -> Optional[Job]:
    """
    Atomically claims the oldest pending/due job using a lease token.
    Uses SKIP LOCKED semantics.
    """
    now = utc_now()
    lease_token = str(uuid.uuid4())
    lease_expires_at = now + timedelta(seconds=settings.JOB_LEASE_SECONDS)

    # 1. Query candidate job
    stmt = (
        select(Job)
        .where(
            or_(
                Job.state == "PENDING",
                and_(Job.state == "RUNNING", Job.lease_expires_at < now),
                and_(Job.state == "RETRY_WAIT", Job.available_at <= now)
            )
        )
        .order_by(Job.available_at.asc(), Job.created_at.asc())
        .limit(1)
    )

    if session.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)

    result = await session.execute(stmt)
    job = result.scalars().first()

    if not job:
        return None

    job.state = "RUNNING"
    job.lease_token = lease_token
    job.lease_expires_at = lease_expires_at
    job.attempts += 1
    await session.commit()
    await session.refresh(job)
    return job

async def process_route_post_job(session: AsyncSession, job: Job) -> None:
    post_id = job.payload.get("post_id")
    post = await session.get(Post, post_id)
    if not post:
        job.state = "FAILED"
        job.last_error_code = "POST_NOT_FOUND"
        await session.commit()
        return

    # Update post state
    post.routing_state = "ROUTING"
    await session.commit()

    # 1. Ensure Post Embedding exists
    post_emb_stmt = select(PostEmbedding).where(PostEmbedding.post_id == post_id)
    post_emb_res = await session.execute(post_emb_stmt)
    post_emb = post_emb_res.scalars().first()

    if not post_emb:
        embed_text_content = f"{post.title} {post.content} {' '.join(post.topics)}"
        vector = embed_text(embed_text_content)
        post_emb = PostEmbedding(
            post_id=post.id,
            model_id=settings.EMBEDDING_MODEL,
            model_revision=settings.EMBEDDING_REVISION,
            input_hash=str(uuid.uuid4()),
            embedding=vector,
            status="READY"
        )
        session.add(post_emb)
        await session.commit()

    # 2. Retrieve all active candidate agents & subscriptions
    agents_stmt = select(Agent).where(Agent.active == True)
    agents_res = await session.execute(agents_stmt)
    agents = agents_res.scalars().all()

    agents_data = []
    for ag in agents:
        sub_stmt = select(Subscription).where(Subscription.agent_id == ag.id)
        sub_res = await session.execute(sub_stmt)
        sub = sub_res.scalars().first()
        if not sub:
            continue

        emb_stmt = select(AgentEmbedding).where(AgentEmbedding.agent_id == ag.id)
        emb_res = await session.execute(emb_stmt)
        emb = emb_res.scalars().first()
        
        agent_vec = emb.embedding if (emb and emb.status == "READY") else embed_text(f"{ag.company_name} {sub.interest_text}")
        agents_data.append({
            "agent": ag,
            "subscription": sub,
            "embedding": agent_vec
        })

    # 3. Compute Routing Decisions
    routing_result = compute_hybrid_routing(
        post=post,
        post_vec=post_emb.embedding,
        agents_data=agents_data
    )

    # 4. Atomic persistence of route run and decisions
    route_run = RouteRun(
        post_id=post.id,
        policy_version=routing_result["policy_version"],
        model_revision=settings.EMBEDDING_REVISION,
        candidate_count=routing_result["candidate_count"],
        eligible_count=routing_result["eligible_count"],
        selected_count=routing_result["selected_count"],
        status="COMPLETED",
        completed_at=utc_now()
    )
    session.add(route_run)
    await session.flush()

    resp_jobs = []
    for d in routing_result["decisions"]:
        r_decision = RouteDecision(
            route_run_id=route_run.id,
            agent_id=d["agent_id"],
            subscription_version=d["subscription_version"],
            eligible=d["eligible"],
            dense_score=d["dense_score"],
            topic_score=d["topic_score"],
            compatibility_score=d["compatibility_score"],
            final_score=d["final_score"],
            threshold=d["threshold"],
            decision=d["decision"],
            reason_codes=d["reason_codes"],
            evidence=d["evidence"]
        )
        session.add(r_decision)

        # If SELECTED, create a persistent notification in the agent's inbox
        if d["decision"] == "SELECTED":
            notif = Notification(
                post_id=post.id,
                recipient_agent_id=d["agent_id"],
                route_run_id=route_run.id,
                delivery_state="QUEUED",
                response_state="PENDING"
            )
            session.add(notif)
            await session.flush()

            # For integrated demo agents, enqueue response job automatically
            resp_job = Job(
                type="RESPOND_NOTIFICATION",
                dedupe_key=f"respond_{notif.id}",
                payload={"notification_id": notif.id}
            )
            session.add(resp_job)
            resp_jobs.append(resp_job)

    post.routing_state = "ROUTED"
    job.state = "SUCCEEDED"
    await session.commit()

    # In DEMO_MODE, process response jobs immediately for real-time UI interactivity
    if settings.DEMO_MODE:
        for rj in resp_jobs:
            try:
                await process_respond_notification_job(session, rj)
            except Exception:
                pass

async def process_respond_notification_job(session: AsyncSession, job: Job) -> None:
    notif_id = job.payload.get("notification_id")
    notif = await session.get(Notification, notif_id)
    if not notif:
        job.state = "FAILED"
        job.last_error_code = "NOTIFICATION_NOT_FOUND"
        await session.commit()
        return

    # Check if already processed
    if notif.response_state in ["RESPONDED", "IGNORED"]:
        job.state = "SUCCEEDED"
        await session.commit()
        return

    agent = await session.get(Agent, notif.recipient_agent_id)
    sub_stmt = select(Subscription).where(Subscription.agent_id == agent.id)
    sub_res = await session.execute(sub_stmt)
    sub = sub_res.scalars().first()

    post = await session.get(Post, notif.post_id)

    # If agent paused, defer response
    if sub and sub.response_mode == "PAUSED":
        job.state = "PENDING"
        job.available_at = utc_now() + timedelta(seconds=60)
        await session.commit()
        return

    # Fetch active campaigns for agent
    camp_stmt = select(Campaign).where(Campaign.agent_id == agent.id, Campaign.active == True)
    camp_res = await session.execute(camp_stmt)
    campaigns = camp_res.scalars().all()
    campaigns_data = [
        {"id": c.id, "title": c.title, "approved_terms": c.approved_terms, "allowed_topics": c.allowed_topics}
        for c in campaigns
    ]

    prompt = build_decision_prompt(
        agent_name=agent.company_name,
        interest_text=sub.interest_text if sub else "",
        post_title=post.title,
        post_content=post.content,
        post_topics=post.topics,
        post_intent=post.intent,
        approved_campaigns=campaigns_data
    )

    notif.response_state = "GENERATING"
    await session.commit()

    decision_data, meta = await llm_adapter.generate_engagement_decision(
        prompt=prompt,
        agent_name=agent.company_name,
        post_topics=post.topics,
        approved_campaigns=campaigns_data
    )

    # Record model run
    model_run = ModelRun(
        purpose="recipient_decision",
        provider=meta["provider"],
        model=meta["model"],
        prompt_version="v2.0",
        status=meta["status"],
        input_hash=str(uuid.uuid4()),
        duration_ms=meta["duration_ms"]
    )
    session.add(model_run)
    await session.flush()

    # Record agent decision
    agent_decision = AgentDecision(
        notification_id=notif.id,
        action=decision_data["action"],
        reason_code=decision_data["reason_code"],
        reason=decision_data["reason"],
        model_run_id=model_run.id
    )
    session.add(agent_decision)

    notif.delivery_state = "DELIVERED"
    notif.delivered_at = utc_now()

    if decision_data["action"] == "respond":
        notif.response_state = "RESPONDED"
        # Check uniqueness constraint before inserting comment
        chk_stmt = select(Comment).where(Comment.post_id == post.id, Comment.author_agent_id == agent.id)
        existing_comment = (await session.execute(chk_stmt)).scalars().first()
        if not existing_comment:
            comment = Comment(
                post_id=post.id,
                author_agent_id=agent.id,
                notification_id=notif.id,
                campaign_id=decision_data.get("campaign_id"),
                content=decision_data.get("draft") or f"Acknowledged by {agent.company_name}",
                generation_mode=settings.LLM_PROVIDER.upper(),
                model_run_id=model_run.id
            )
            session.add(comment)
    else:
        notif.response_state = "IGNORED"

    job.state = "SUCCEEDED"
    await session.commit()

async def process_embed_agent_job(session: AsyncSession, job: Job) -> None:
    agent_id = job.payload.get("agent_id")
    agent = await session.get(Agent, agent_id)
    if not agent:
        job.state = "FAILED"
        await session.commit()
        return

    sub_stmt = select(Subscription).where(Subscription.agent_id == agent.id)
    sub = (await session.execute(sub_stmt)).scalars().first()
    if not sub:
        job.state = "FAILED"
        await session.commit()
        return

    text_to_embed = f"{agent.company_name}: {agent.description}. Interests: {sub.interest_text}"
    vector = embed_text(text_to_embed)

    emb_stmt = select(AgentEmbedding).where(AgentEmbedding.agent_id == agent.id)
    emb = (await session.execute(emb_stmt)).scalars().first()
    if not emb:
        emb = AgentEmbedding(
            agent_id=agent.id,
            subscription_version=sub.version,
            model_id=settings.EMBEDDING_MODEL,
            model_revision=settings.EMBEDDING_REVISION,
            input_hash=str(uuid.uuid4()),
            embedding=vector,
            status="READY"
        )
        session.add(emb)
    else:
        emb.subscription_version = sub.version
        emb.embedding = vector
        emb.status = "READY"
        emb.updated_at = utc_now()

    job.state = "SUCCEEDED"
    await session.commit()

async def execute_job(job: Job) -> None:
    async with AsyncSessionLocal() as session:
        try:
            if job.type == "ROUTE_POST":
                await process_route_post_job(session, job)
            elif job.type == "RESPOND_NOTIFICATION":
                await process_respond_notification_job(session, job)
            elif job.type == "EMBED_AGENT":
                await process_embed_agent_job(session, job)
            else:
                job.state = "FAILED"
                job.last_error_code = "UNKNOWN_JOB_TYPE"
                await session.commit()
        except Exception as e:
            await session.rollback()
            job.attempts += 1
            if job.attempts >= settings.MAX_JOB_ATTEMPTS:
                job.state = "FAILED"
            else:
                job.state = "RETRY_WAIT"
                job.available_at = utc_now() + timedelta(seconds=10 * (2 ** job.attempts))
            job.last_error_code = str(e)[:100]
            async with AsyncSessionLocal() as err_sess:
                err_sess.add(job)
                await err_sess.commit()

