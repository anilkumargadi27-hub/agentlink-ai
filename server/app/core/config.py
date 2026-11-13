import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

_default_db = "sqlite+aiosqlite:////tmp/agentlink.db" if os.environ.get("VERCEL") else "sqlite+aiosqlite:///./agentlink.db"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_ENV: str = "development"
    PROJECT_NAME: str = "AgentLink AI"
    VERSION: str = "2.0.0"
    PUBLIC_ORIGIN: str = "http://localhost:5173"
    DEMO_MODE: bool = True

    # Database: Defaults to local SQLite if DATABASE_URL not set or for instant testing
    DATABASE_URL: str = Field(
        default=_default_db,
        description="Database connection string (PostgreSQL+asyncpg or SQLite+aiosqlite)"
    )

    # Security
    SESSION_SECRET: str = "agentlink_dev_session_secret_32_characters_long_min"
    AGENT_KEY_PEPPER: str = "agentlink_dev_pepper_salt_value_min_32_chars"
    SESSION_MAX_AGE_SECONDS: int = 86400 * 7

    # Routing Engine Policy
    ROUTING_POLICY_VERSION: str = "hybrid-v1"
    ROUTING_THRESHOLD: float = 0.60
    MAX_RECIPIENTS: int = 10
    RERANK_ENABLED: bool = False
    TOP_K_CANDIDATES: int = 10

    # Durable Jobs Queue
    MAX_JOB_ATTEMPTS: int = 5
    JOB_LEASE_SECONDS: int = 120
    POST_RATE_LIMIT_PER_HOUR: int = 30
    MAX_GENERATIONS_PER_DAY: int = 1000

    # Model Provider & Embeddings
    # LLM_PROVIDER: "ollama" | "gemini" | "fixture"
    LLM_PROVIDER: str = "fixture"
    LLM_MODEL: str = "llama3:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: Optional[str] = None
    MODEL_TIMEOUT_SECONDS: int = 60

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_REVISION: str = "e4ce9877abf3ed5e10ce38f5777046eab0ced582"
    EMBEDDING_DIM: int = 384

    # Extensions
    EXTERNAL_WEBHOOKS_ENABLED: bool = False

settings = Settings()

