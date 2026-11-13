from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.core.database import get_db
from server.app.core.security import (
    verify_password, generate_session_token, hash_session_token
)
from server.app.models.all_models import User, UserSession
from server.app.schemas import LoginRequest, LoginResponse, SessionUser, ErrorEnvelope
from server.app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."}
        )

    raw_token, token_digest, csrf_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    session = UserSession(
        user_id=user.id,
        token_digest=token_digest,
        csrf_token=csrf_token,
        expires_at=expires_at
    )
    db.add(session)
    await db.commit()

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=raw_token,
        httponly=True,
        secure=False, # True in prod
        samesite="lax",
        max_age=86400 * 7
    )

    return LoginResponse(
        user=SessionUser(id=user.id, email=user.email, role=user.role),
        csrf_token=csrf_token,
        message="Login successful"
    )

@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Not authenticated."})
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role
        }
    }

