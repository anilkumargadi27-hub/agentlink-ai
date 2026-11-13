import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from server.app.main import app
from server.app.core.database import init_db, AsyncSessionLocal
from server.app.core.security import hash_password
from server.app.models.all_models import User

@pytest.mark.asyncio
async def test_t01_t02_agent_registration():
    await init_db()
    
    # Ensure default operator exists
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == "test_operator@asama.ai")
        user = (await session.execute(stmt)).scalars().first()
        if not user:
            user = User(
                email="test_operator@asama.ai",
                password_hash=hash_password("Pass123!"),
                role="operator",
                enabled=True
            )
            session.add(user)
            await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Log in as operator
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "test_operator@asama.ai",
            "password": "Pass123!"
        })
        assert login_res.status_code == 200

        # T01: Valid Registration
        reg_payload = {
            "company_name": "Test Pay Inc",
            "description": "Payment gateway and billing infrastructure provider.",
            "interest_text": "Merchant billing, payments, credit card integrations.",
            "include_topics": ["card_benefit", "merchant_promotion"],
            "threshold": 0.65,
            "hourly_limit": 15
        }
        res = await client.post("/api/v1/agents", json=reg_payload)
        assert res.status_code == 201
        data = res.json()
        assert "api_key" in data
        assert data["api_key"].startswith("agl_live_")
        assert data["agent"]["company_name"] == "Test Pay Inc"

        # T02: Invalid Threshold (must be between 0.0 and 1.0)
        invalid_payload = {
            "company_name": "Bad Agent",
            "description": "Short",
            "interest_text": "Invalid",
            "threshold": 1.5
        }
        res_err = await client.post("/api/v1/agents", json=invalid_payload)
        assert res_err.status_code == 422
        err_json = res_err.json()
        assert err_json["error"]["code"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_health_routes():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_live = await client.get("/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "alive"

        res_ready = await client.get("/health/ready")
        assert res_ready.status_code == 200
