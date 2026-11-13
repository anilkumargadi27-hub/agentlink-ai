import hashlib
import hmac
import secrets
from typing import Tuple, Optional
from server.app.core.config import settings

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{pwd_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or ":" not in hashed_password:
        return False
    salt, expected_hash = hashed_password.split(":", 1)
    actual_hash = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual_hash, expected_hash)

def generate_session_token() -> Tuple[str, str, str]:
    """Generates (raw_token, token_digest, csrf_token)."""
    raw_token = secrets.token_urlsafe(32)
    token_digest = hashlib.sha256((raw_token + settings.SESSION_SECRET).encode("utf-8")).hexdigest()
    csrf_token = secrets.token_urlsafe(32)
    return raw_token, token_digest, csrf_token

def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token + settings.SESSION_SECRET).encode("utf-8")).hexdigest()

def generate_agent_api_key() -> Tuple[str, str, str]:
    """
    Generates an unguessable agent API key.
    Returns (raw_key, prefix, key_digest).
    """
    random_part = secrets.token_urlsafe(32)
    raw_key = f"agl_live_{random_part}"
    prefix = raw_key[:12]
    key_digest = hmac.new(
        settings.AGENT_KEY_PEPPER.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return raw_key, prefix, key_digest

def verify_agent_api_key(raw_key: str, expected_digest: str) -> bool:
    if not raw_key or not expected_digest:
        return False
    actual_digest = hmac.new(
        settings.AGENT_KEY_PEPPER.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(actual_digest, expected_digest)

def compute_payload_hash(payload_str: str) -> str:
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

