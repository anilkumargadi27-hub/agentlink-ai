import hashlib
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, Header, Cookie, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.core.security import hash_session_token, verify_agent_api_key
from server.app.models.all_models import User, UserSession, Agent, AgentCredential, IdempotencyRecord
from server.app.core.config import settings

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Retrieves authenticated operator from cookie session or header."""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Session "):
        token = auth_header.split(" ", 1)[1]
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")

    if not token:
        # In DEMO_MODE, return or auto-create default operator if none provided
        if settings.DEMO_MODE:
            res = await db.execute(select(User).limit(1))
            user = res.scalars().first()
            if user:
                return user
        return None

    token_digest = hash_session_token(token)
    stmt = select(UserSession).where(
        UserSession.token_digest == token_digest,
        UserSession.revoked_at.is_(None)
    )
    res = await db.execute(stmt)
    sess = res.scalars().first()
    if not sess:
        return None

    user = await db.get(User, sess.user_id)
    return user

async def require_operator_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Operator authentication required."}
        )
    return user

async def get_current_agent(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    """Verifies agent Bearer token and returns the corresponding Agent record."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED_AGENT", "message": "Missing or malformed Authorization header."}
        )
    
    raw_key = authorization.split(" ", 1)[1].strip()
    if not raw_key.startswith("agl_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED_AGENT", "message": "Invalid key format."}
        )

    prefix = raw_key[:12]
    stmt = select(AgentCredential).where(
        AgentCredential.key_prefix == prefix,
        AgentCredential.revoked_at.is_(None)
    )
    res = await db.execute(stmt)
    credentials = res.scalars().all()

    matched_cred = None
    for cred in credentials:
        if verify_agent_api_key(raw_key, cred.key_digest):
            matched_cred = cred
            break

    if not matched_cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED_AGENT", "message": "Agent API key rejected or revoked."}
        )

    agent = await db.get(Agent, matched_cred.agent_id)
    if not agent or not agent.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN_RESOURCE", "message": "Agent is deactivated or suspended."}
        )

    return agent

