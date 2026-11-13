import pytest
from server.app.agents.adapter import llm_adapter

@pytest.mark.asyncio
async def test_t11_t12_t13_agent_autonomy():
    """T11, T12, T13: Autonomous response matching approved campaign vs ignore on unapproved terms."""
    approved_campaigns = [
        {
            "id": "demo_phonepe_food_01",
            "title": "Diwali Food Cashback",
            "approved_terms": {"benefit": "10% instant cashback via PhonePe UPI"},
            "allowed_topics": ["food_delivery", "merchant_promotion"]
        }
    ]

    # Matching case -> Should respond with campaign terms
    res_match, meta_match = await llm_adapter.generate_engagement_decision(
        prompt="Test prompt",
        agent_name="PhonePe",
        post_topics=["food_delivery", "merchant_promotion"],
        approved_campaigns=approved_campaigns
    )
    assert res_match["action"] == "respond"
    assert res_match["campaign_id"] == "demo_phonepe_food_01"
    assert "10% instant cashback" in res_match["draft"]

    # Non-matching case -> Should autonomously ignore
    res_ignore, meta_ignore = await llm_adapter.generate_engagement_decision(
        prompt="Test prompt",
        agent_name="PhonePe",
        post_topics=["vehicle_launch"],
        approved_campaigns=approved_campaigns
    )
    assert res_ignore["action"] == "ignore"
    assert res_ignore["campaign_id"] is None
    assert res_ignore["draft"] == ""

    # T13: Attempt to inject unapproved campaign ID
    sanitized = llm_adapter._validate_and_sanitize(
        {
            "action": "respond",
            "reason_code": "PROMOTIONAL_CLAIM",
            "reason": "Offering 99% cashback",
            "campaign_id": "unapproved_fabricated_campaign_99",
            "draft": "We offer 99% discount"
        },
        approved_campaigns=approved_campaigns
    )
    assert sanitized["action"] == "ignore"
    assert sanitized["campaign_id"] is None
    assert sanitized["draft"] == ""

