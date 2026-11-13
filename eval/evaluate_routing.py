import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from types import SimpleNamespace
from typing import Dict, Any, List
from server.app.services.routing import compute_hybrid_routing
from server.app.services.embeddings import embed_text
from server.app.seed_demo import DEMO_AGENTS

def run_evaluation():
    fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures.json")
    with open(fixtures_path, "r") as f:
        fixtures = json.load(f)

    # Prepare demo agents objects
    agents_data = []
    for a in DEMO_AGENTS:
        ag = SimpleNamespace(
            id=f"agent_{a['company_name'].lower().replace(' ', '_')}",
            company_name=a["company_name"],
            active=True,
            verification_status="DEMO"
        )
        sub = SimpleNamespace(
            version=1,
            enabled=True,
            interest_text=a["interest_text"],
            include_topics=a["include_topics"],
            exclude_topics=a["exclude_topics"],
            accepted_intents=a["accepted_intents"],
            excluded_author_ids=[],
            country_codes=[],
            language_codes=[],
            threshold=a["threshold"]
        )
        vec = embed_text(f"{ag.company_name} {sub.interest_text}")
        agents_data.append({"agent": ag, "subscription": sub, "embedding": vec})

    # Evaluate Hybrid Routing vs Keyword Matching
    metrics = {
        "hybrid": {"tp": 0, "fp": 0, "fn": 0},
        "keyword": {"tp": 0, "fp": 0, "fn": 0}
    }

    for case in fixtures:
        post = SimpleNamespace(
            id=case["case_id"],
            author_agent_id="external_author",
            title=case["title"],
            content=case["content"],
            topics=case["topics"],
            intent=case["intent"],
            country_code="IN",
            language_code="en",
            moderation_state="ALLOWED",
            expires_at=SimpleNamespace(tzinfo=None, replace=lambda tzinfo: SimpleNamespace(tzinfo=tzinfo))
        )
        # Mock post expiry
        from datetime import datetime, timezone, timedelta
        post.expires_at = datetime.now(timezone.utc) + timedelta(days=10)

        post_vec = embed_text(f"{post.title} {post.content} {' '.join(post.topics)}")

        # 1. Hybrid Routing
        res = compute_hybrid_routing(post, post_vec, agents_data)
        hybrid_selected = {
            d["agent_name"] for d in res["decisions"] if d["decision"] == "SELECTED"
        }

        # 2. Keyword baseline (matches only if text contains exact keywords)
        keyword_selected = set()
        for item in agents_data:
            ag_name = item["agent"].company_name
            sub = item["subscription"]
            if any(t in sub.exclude_topics for t in post.topics):
                continue
            if any(t in sub.include_topics for t in post.topics):
                keyword_selected.add(ag_name)

        expected = set(case["expected_positive"])

        # Calculate TP, FP, FN for hybrid
        for ag in hybrid_selected:
            if ag in expected:
                metrics["hybrid"]["tp"] += 1
            else:
                metrics["hybrid"]["fp"] += 1
        for ag in expected:
            if ag not in hybrid_selected:
                metrics["hybrid"]["fn"] += 1

        # Calculate TP, FP, FN for keyword
        for ag in keyword_selected:
            if ag in expected:
                metrics["keyword"]["tp"] += 1
            else:
                metrics["keyword"]["fp"] += 1
        for ag in expected:
            if ag not in keyword_selected:
                metrics["keyword"]["fn"] += 1

    def calc_scores(m):
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        return round(prec, 4), round(rec, 4), round(f1, 4)

    h_prec, h_rec, h_f1 = calc_scores(metrics["hybrid"])
    k_prec, k_rec, k_f1 = calc_scores(metrics["keyword"])

    print("\n=======================================================")
    print("      AGENTLINK AI ROUTING EVALUATION REPORT          ")
    print("=======================================================")
    print(f"Total Test Cases: {len(fixtures)}")
    print(f"{'Method':<16} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10} | {'TP':<4} | {'FP':<4} | {'FN':<4}")
    print("-------------------------------------------------------------------------")
    print(f"{'Keyword Baseline':<16} | {k_prec:<10.2%} | {k_rec:<10.2%} | {k_f1:<10.4f} | {metrics['keyword']['tp']:<4} | {metrics['keyword']['fp']:<4} | {metrics['keyword']['fn']:<4}")
    print(f"{'Hybrid-v1':<16} | {h_prec:<10.2%} | {h_rec:<10.2%} | {h_f1:<10.4f} | {metrics['hybrid']['tp']:<4} | {metrics['hybrid']['fp']:<4} | {metrics['hybrid']['fn']:<4}")
    print("=======================================================\n")

if __name__ == "__main__":
    run_evaluation()

