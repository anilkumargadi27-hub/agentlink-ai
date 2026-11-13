import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from server.app.services.routing import compute_hybrid_routing, evaluate_agent_eligibility

def test_t06_food_delivery_scenario():
    """T06: Food-delivery post selects payment profiles and excludes muted topics."""
    post = SimpleNamespace(
        id="post_swiggy_01",
        author_agent_id="agent_swiggy",
        title="5% off food deliveries",
        content="Festive dining discount",
        topics=["food_delivery", "merchant_promotion"],
        intent="offer",
        country_code="IN",
        language_code="en",
        moderation_state="ALLOWED",
        expires_at=datetime.now(timezone.utc) + timedelta(days=5)
    )

    agents_data = [
        # Swiggy (Self)
        {
            "agent": SimpleNamespace(id="agent_swiggy", company_name="Swiggy", active=True, verification_status="DEMO"),
            "subscription": SimpleNamespace(version=1, enabled=True, interest_text="Food delivery", include_topics=["food_delivery"], exclude_topics=[], accepted_intents=[], excluded_author_ids=[], country_codes=[], language_codes=[], threshold=0.60),
            "embedding": [0.8] * 384
        },
        # PhonePe (Interested in food + payments)
        {
            "agent": SimpleNamespace(id="agent_phonepe", company_name="PhonePe", active=True, verification_status="DEMO"),
            "subscription": SimpleNamespace(version=1, enabled=True, interest_text="Merchant payments and food checkout", include_topics=["food_delivery", "merchant_promotion"], exclude_topics=[], accepted_intents=[], excluded_author_ids=[], country_codes=[], language_codes=[], threshold=0.60),
            "embedding": [0.8] * 384
        },
        # Bajaj Auto (Explicitly excludes food_delivery)
        {
            "agent": SimpleNamespace(id="agent_bajaj", company_name="Bajaj Auto", active=True, verification_status="DEMO"),
            "subscription": SimpleNamespace(version=1, enabled=True, interest_text="Vehicles and motorcycles", include_topics=["vehicle_launch"], exclude_topics=["food_delivery"], accepted_intents=[], excluded_author_ids=[], country_codes=[], language_codes=[], threshold=0.60),
            "embedding": [0.1] * 384
        }
    ]

    res = compute_hybrid_routing(post, [0.8] * 384, agents_data)
    decisions = {d["agent_id"]: d for d in res["decisions"]}

    # Swiggy should be EXCLUDED_SELF
    assert decisions["agent_swiggy"]["decision"] == "EXCLUDED_SELF"
    
    # PhonePe should be SELECTED
    assert decisions["agent_phonepe"]["decision"] == "SELECTED"
    assert decisions["agent_phonepe"]["final_score"] >= 0.60

    # Bajaj Auto should be EXCLUDED_TOPIC
    assert decisions["agent_bajaj"]["decision"] == "EXCLUDED_TOPIC"

def test_t08_author_block_overrides_high_similarity():
    """T08: High-scoring candidate with author block is excluded before scoring."""
    post = SimpleNamespace(
        id="post_01",
        author_agent_id="agent_blocked_author",
        title="Exclusive Partnership",
        content="High value offer",
        topics=["merchant_promotion"],
        intent="offer",
        country_code="IN",
        language_code="en",
        moderation_state="ALLOWED",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    agent = SimpleNamespace(id="agent_target", company_name="Target", active=True, verification_status="DEMO")
    sub = SimpleNamespace(
        version=1, enabled=True, interest_text="Merchant promotion",
        include_topics=["merchant_promotion"], exclude_topics=[],
        accepted_intents=[], excluded_author_ids=["agent_blocked_author"],
        country_codes=[], language_codes=[], threshold=0.60
    )

    reason = evaluate_agent_eligibility(post, agent, sub)
    assert reason == "EXCLUDED_AUTHOR_BLOCK"

def test_t09_expired_post_excluded():
    """T09: Expired post is rejected or not routed."""
    post = SimpleNamespace(
        id="post_expired",
        author_agent_id="author_1",
        title="Old Offer",
        content="Expired",
        topics=["food_delivery"],
        intent="offer",
        country_code="IN",
        language_code="en",
        moderation_state="ALLOWED",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )

    agent = SimpleNamespace(id="agent_2", company_name="Agent 2", active=True, verification_status="DEMO")
    sub = SimpleNamespace(version=1, enabled=True, interest_text="Food", include_topics=[], exclude_topics=[], accepted_intents=[], excluded_author_ids=[], country_codes=[], language_codes=[], threshold=0.60)

    reason = evaluate_agent_eligibility(post, agent, sub)
    assert reason == "EXCLUDED_EXPIRED_POST"

