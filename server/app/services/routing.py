import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from server.app.core.config import settings
from server.app.services.embeddings import cosine_similarity

# Load business compatibility rules
try:
    with open("specs/routing-policy.json", "r") as f:
        ROUTING_CONFIG = json.load(f)
except Exception:
    ROUTING_CONFIG = {
        "policy_version": "hybrid-v1",
        "weights": {"dense_semantic": 0.65, "topic_overlap": 0.20, "business_compatibility": 0.15},
        "default_threshold": 0.60,
        "recipient_cap": 10,
        "business_compatibility_rules": [
            {"id": "RULE_FOOD_PAYMENTS", "post_topic": "food_delivery", "agent_interest_keyword": "payment"},
            {"id": "RULE_RETAIL_CARDS", "post_topic": "retail_checkout", "agent_interest_keyword": "card"},
            {"id": "RULE_VEHICLE_FINANCE", "post_topic": "vehicle_launch", "agent_interest_keyword": "financing"}
        ]
    }

def check_business_compatibility(post_topics: List[str], post_intent: str, interest_text: str) -> Tuple[float, Optional[str]]:
    rules = ROUTING_CONFIG.get("business_compatibility_rules", [])
    lower_interest = interest_text.lower()
    for rule in rules:
        target_topic = rule.get("post_topic")
        kw = rule.get("agent_interest_keyword", "")
        if target_topic in post_topics and kw in lower_interest:
            return 1.0, rule.get("id")
    return 0.0, None

def evaluate_agent_eligibility(
    post: Any,
    agent: Any,
    subscription: Any
) -> Optional[str]:
    """
    Stage A: Determines whether the agent is eligible to receive the post.
    Returns exclusion reason string if excluded; None if eligible.
    """
    # 1. Author self-notification
    if agent.id == post.author_agent_id:
        return "EXCLUDED_SELF"
    
    # 2. Inactive or suspended agent
    if not agent.active or agent.verification_status == "SUSPENDED":
        return "EXCLUDED_INACTIVE"

    # 3. Disabled subscription
    if not subscription.enabled:
        return "EXCLUDED_SUBSCRIPTION_DISABLED"

    # 4. Explicit author block
    if post.author_agent_id in subscription.excluded_author_ids:
        return "EXCLUDED_AUTHOR_BLOCK"

    # 5. Topic exclusions (Hard constraint)
    for excluded_topic in subscription.exclude_topics:
        if excluded_topic in post.topics:
            return "EXCLUDED_TOPIC"

    # 6. Post expiry check
    now = datetime.now(timezone.utc)
    post_exp = post.expires_at if post.expires_at.tzinfo else post.expires_at.replace(tzinfo=timezone.utc)
    if post_exp < now:
        return "EXCLUDED_EXPIRED_POST"

    # 7. Moderation status
    if post.moderation_state != "ALLOWED":
        return "EXCLUDED_POST_NOT_ALLOWED"

    # 8. Country and Language compatibility
    if subscription.country_codes and post.country_code not in subscription.country_codes:
        return "EXCLUDED_GEO"
    if subscription.language_codes and post.language_code not in subscription.language_codes:
        return "EXCLUDED_LANG"

    # 9. Intent compatibility
    if subscription.accepted_intents and post.intent not in subscription.accepted_intents:
        return "EXCLUDED_INTENT"

    return None

def compute_hybrid_routing(
    post: Any,
    post_vec: List[float],
    agents_data: List[Dict[str, Any]],
    threshold: Optional[float] = None,
    cap: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes Stages A, B, C, and D of the routing engine.
    """
    thresh = threshold if threshold is not None else settings.ROUTING_THRESHOLD
    max_cap = cap if cap is not None else settings.MAX_RECIPIENTS
    policy_version = ROUTING_CONFIG.get("policy_version", "hybrid-v1")
    weights = ROUTING_CONFIG.get("weights", {"dense_semantic": 0.65, "topic_overlap": 0.20, "business_compatibility": 0.15})

    decisions: List[Dict[str, Any]] = []
    ranked_candidates: List[Dict[str, Any]] = []

    for item in agents_data:
        agent = item["agent"]
        sub = item["subscription"]
        agent_vec = item.get("embedding", [])

        # Stage A: Eligibility
        exclusion_reason = evaluate_agent_eligibility(post, agent, sub)
        if exclusion_reason:
            decisions.append({
                "agent_id": agent.id,
                "agent_name": agent.company_name,
                "subscription_version": sub.version,
                "eligible": False,
                "dense_score": None,
                "topic_score": None,
                "compatibility_score": None,
                "final_score": None,
                "threshold": float(sub.threshold or thresh),
                "decision": exclusion_reason,
                "reason_codes": [exclusion_reason],
                "evidence": f"Candidate excluded during pre-scoring eligibility checks: {exclusion_reason}"
            })
            continue

        # Stage C: Feature Calculation
        # 1. Dense Semantic Similarity D
        raw_cosine = cosine_similarity(post_vec, agent_vec)
        dense_score = max(0.0, raw_cosine)

        # 2. Topic Overlap Ratio T
        include_topics = sub.include_topics or []
        if include_topics:
            matched_topics = [t for t in post.topics if t in include_topics]
            topic_score = len(matched_topics) / len(include_topics)
        else:
            topic_score = 0.0

        # 3. Business Intent Compatibility B
        compat_score, matched_rule_id = check_business_compatibility(
            post.topics, post.intent, sub.interest_text
        )

        # Composite Score S
        final_score = (
            weights["dense_semantic"] * dense_score +
            weights["topic_overlap"] * topic_score +
            weights["business_compatibility"] * compat_score
        )

        candidate_info = {
            "agent_id": agent.id,
            "agent_name": agent.company_name,
            "subscription_version": sub.version,
            "eligible": True,
            "dense_score": round(dense_score, 4),
            "topic_score": round(topic_score, 4),
            "compatibility_score": round(compat_score, 4),
            "final_score": round(final_score, 4),
            "threshold": float(sub.threshold or thresh),
            "matched_rule_id": matched_rule_id,
            "reason_codes": [],
            "evidence": ""
        }
        ranked_candidates.append(candidate_info)

    # Sort descending by final score, tie-break ascending by agent_id
    ranked_candidates.sort(key=lambda x: (-x["final_score"], x["agent_id"]))

    # Stage D: Thresholding and Cap Allocation
    selected_count = 0
    for cand in ranked_candidates:
        c_thresh = cand["threshold"]
        c_score = cand["final_score"]

        if c_score < c_thresh:
            cand["decision"] = "BELOW_THRESHOLD"
            cand["reason_codes"].append("BELOW_THRESHOLD")
            cand["evidence"] = (
                f"Candidate score {c_score:.4f} is below agent cutoff threshold of {c_thresh:.2f}."
            )
        elif selected_count >= max_cap:
            cand["decision"] = "DEFERRED_CAP"
            cand["reason_codes"].append("DEFERRED_CAP")
            cand["evidence"] = (
                f"Candidate qualified with score {c_score:.4f} >= {c_thresh:.2f}, but recipient cap of {max_cap} was reached."
            )
        else:
            cand["decision"] = "SELECTED"
            cand["reason_codes"].append("HYBRID_SCORE_MATCH")
            rule_str = f" [Rule: {cand['matched_rule_id']}]" if cand.get("matched_rule_id") else ""
            cand["evidence"] = (
                f"Selected via hybrid-v1 (dense={cand['dense_score']:.2f}, "
                f"topic={cand['topic_score']:.2f}, "
                f"compat={cand['compatibility_score']:.2f}{rule_str}) -> Composite {c_score:.4f} >= {c_thresh:.2f}."
            )
            selected_count += 1

        decisions.append(cand)

    return {
        "policy_version": policy_version,
        "candidate_count": len(agents_data),
        "eligible_count": len(ranked_candidates),
        "selected_count": selected_count,
        "decisions": decisions
    }
