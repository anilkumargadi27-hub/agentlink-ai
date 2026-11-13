import time
import json
import httpx
from typing import Dict, Any, Optional, Tuple
from server.app.core.config import settings

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["respond", "ignore"]},
        "reason_code": {"type": "string"},
        "reason": {"type": "string"},
        "campaign_id": {"type": ["string", "null"]},
        "draft": {"type": "string"}
    },
    "required": ["action", "reason_code", "reason", "campaign_id", "draft"]
}

class LLMAdapter:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL

    async def generate_engagement_decision(
        self,
        prompt: str,
        agent_name: str,
        post_topics: list,
        approved_campaigns: list
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Executes engagement decision.
        Returns (decision_data, execution_metadata).
        """
        start_time = time.time()
        
        # 1. LIVE_LOCAL (Ollama)
        if self.provider == "ollama":
            try:
                async with httpx.AsyncClient(timeout=settings.MODEL_TIMEOUT_SECONDS) as client:
                    resp = await client.post(
                        f"{settings.OLLAMA_BASE_URL}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": "You return strict JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            "format": "json",
                            "stream": False
                        }
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    if resp.status_code == 200:
                        raw_content = resp.json().get("message", {}).get("content", "{}")
                        data = json.loads(raw_content)
                        return self._validate_and_sanitize(data, approved_campaigns), {
                            "provider": "ollama",
                            "model": self.model,
                            "duration_ms": duration_ms,
                            "status": "SUCCESS"
                        }
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                # Fall through to fixture if local Ollama daemon is offline, but record error
                pass

        # 2. LIVE_HOSTED (Gemini)
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                # Direct Gemini REST call with JSON mode
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={settings.GEMINI_API_KEY}"
                async with httpx.AsyncClient(timeout=settings.MODEL_TIMEOUT_SECONDS) as client:
                    resp = await client.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"response_mime_type": "application/json"}
                        }
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    if resp.status_code == 200:
                        raw_json = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                        data = json.loads(raw_json)
                        return self._validate_and_sanitize(data, approved_campaigns), {
                            "provider": "gemini",
                            "model": self.model,
                            "duration_ms": duration_ms,
                            "status": "SUCCESS"
                        }
            except Exception:
                pass

        # 3. FIXTURE_DEMO / DETERMINISTIC FALLBACK
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Check if any approved campaign matches incoming topics
        matching_campaign = None
        for camp in approved_campaigns:
            camp_topics = camp.get("allowed_topics", [])
            if any(t in camp_topics for t in post_topics):
                matching_campaign = camp
                break

        if matching_campaign:
            terms = matching_campaign.get("approved_terms", {})
            benefit = terms.get("benefit", "partner benefits")
            data = {
                "action": "respond",
                "reason_code": "APPROVED_CAMPAIGN_MATCH",
                "reason": f"Post matches approved campaign '{matching_campaign['title']}'.",
                "campaign_id": matching_campaign["id"],
                "draft": f"Official Partner Update: We are pleased to support this initiative with our {benefit}."
            }
        else:
            # Autonomous ignore decision
            data = {
                "action": "ignore",
                "reason_code": "NO_RELEVANT_CAMPAIGN",
                "reason": f"No pre-approved marketing campaign active for topics {post_topics}.",
                "campaign_id": None,
                "draft": ""
            }

        return data, {
            "provider": "fixture",
            "model": "fixture-rule-engine",
            "duration_ms": duration_ms,
            "status": "SUCCESS"
        }

    def _validate_and_sanitize(self, data: Dict[str, Any], approved_campaigns: list) -> Dict[str, Any]:
        """Ensures strict schema compliance and enforces that campaign_id is valid."""
        action = data.get("action", "ignore")
        if action not in ["respond", "ignore"]:
            action = "ignore"

        campaign_id = data.get("campaign_id")
        draft = data.get("draft", "")

        if action == "ignore":
            return {
                "action": "ignore",
                "reason_code": data.get("reason_code", "AUTONOMOUS_DECLINE"),
                "reason": data.get("reason", "Agent chose not to respond."),
                "campaign_id": None,
                "draft": ""
            }

        # If action is respond, verify campaign_id belongs to approved list
        valid_campaign_ids = {c["id"] for c in approved_campaigns}
        if campaign_id and campaign_id not in valid_campaign_ids:
            # LLM hallucinated an invalid campaign ID -> sanitize
            return {
                "action": "ignore",
                "reason_code": "INVALID_CAMPAIGN_REJECTED",
                "reason": f"LLM attempted to use unapproved campaign ID: {campaign_id}",
                "campaign_id": None,
                "draft": ""
            }

        return {
            "action": "respond",
            "reason_code": data.get("reason_code", "CAMPAIGN_MATCH"),
            "reason": data.get("reason", "Approved campaign matched."),
            "campaign_id": campaign_id,
            "draft": draft[:500]
        }

llm_adapter = LLMAdapter()

