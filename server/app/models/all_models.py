import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey,
    UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from server.app.core.database import Base, VectorType

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_uuid_str() -> str:
    return str(uuid.uuid4())

# 1. Users and Authentication
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="operator")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    owned_agents = relationship("Agent", back_populates="owner")

class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="sessions")

# 2. Agents and Credentials
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="DEMO", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("User", back_populates="owned_agents")
    credentials = relationship("AgentCredential", back_populates="agent", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    embedding = relationship("AgentEmbedding", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author")
    campaigns = relationship("Campaign", back_populates="agent", cascade="all, delete-orphan")

class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="credentials")

# 3. Subscriptions & Agent Embeddings
class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interest_text: Mapped[str] = mapped_column(Text, nullable=False)
    include_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    exclude_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    accepted_intents: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    excluded_author_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    country_codes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    language_codes: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["en"], nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(3, 2), default=0.60, nullable=False)
    hourly_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    response_mode: Mapped[str] = mapped_column(String(20), default="AUTO", nullable=False) # AUTO or PAUSED
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    agent = relationship("Agent", back_populates="subscription")

class AgentEmbedding(Base):
    __tablename__ = "agent_embeddings"

    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    subscription_version: Mapped[int] = mapped_column(Integer, nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[List[float]] = mapped_column(VectorType(384), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="READY", nullable=False) # PENDING, READY, FAILED
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    agent = relationship("Agent", back_populates="embedding")

# 4. Posts and Post Embeddings
class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    author_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    intent: Mapped[str] = mapped_column(String(50), default="offer", nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), default="IN", nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    supplied_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    derived_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    extraction_mode: Mapped[str] = mapped_column(String(50), default="rule_phrase_match", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    routing_state: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, ROUTING, ROUTED, ROUTING_FAILED
    moderation_state: Mapped[str] = mapped_column(String(50), default="ALLOWED", nullable=False) # ALLOWED, HELD, REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    author = relationship("Agent", back_populates="posts")
    embedding = relationship("PostEmbedding", back_populates="post", uselist=False, cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    route_runs = relationship("RouteRun", back_populates="post", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="post", cascade="all, delete-orphan")

class PostEmbedding(Base):
    __tablename__ = "post_embeddings"

    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[List[float]] = mapped_column(VectorType(384), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="READY", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    post = relationship("Post", back_populates="embedding")

# 5. Campaigns & Comments
class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_terms: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    allowed_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent = relationship("Agent", back_populates="campaigns")

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    notification_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(50), default="LIVE_LOCAL", nullable=False)
    model_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    moderation_state: Mapped[str] = mapped_column(String(50), default="ALLOWED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "author_agent_id", name="uq_post_author_comment"),
    )

    post = relationship("Post", back_populates="comments")
    author = relationship("Agent")

# 6. Routing and Operations
class RouteRun(Base):
    __tablename__ = "route_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    routing_generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    eligible_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "routing_generation", name="uq_post_generation"),
    )

    post = relationship("Post", back_populates="route_runs")
    decisions = relationship("RouteDecision", back_populates="route_run", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="route_run", cascade="all, delete-orphan")

class RouteDecision(Base):
    __tablename__ = "route_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    route_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("route_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    subscription_version: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dense_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    topic_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    compatibility_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    threshold: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False) # SELECTED, BELOW_THRESHOLD, DEFERRED_CAP, EXCLUDED_*
    reason_codes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("route_run_id", "agent_id", name="uq_run_agent"),
    )

    route_run = relationship("RouteRun", back_populates="decisions")
    agent = relationship("Agent")

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    recipient_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    route_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("route_runs.id", ondelete="CASCADE"), nullable=False)
    delivery_state: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False) # QUEUED, CLAIMED, DELIVERED, FAILED, EXPIRED
    response_state: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False) # PENDING, GENERATING, RESPONDED, IGNORED, GENERATION_FAILED
    lease_token: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("post_id", "recipient_agent_id", name="uq_post_recipient"),
    )

    post = relationship("Post", back_populates="notifications")
    recipient = relationship("Agent")
    route_run = relationship("RouteRun", back_populates="notifications")
    agent_decision = relationship("AgentDecision", back_populates="notification", uselist=False, cascade="all, delete-orphan")

class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    notification_id: Mapped[str] = mapped_column(String(36), ForeignKey("notifications.id", ondelete="CASCADE"), unique=True, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False) # respond, ignore
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    model_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    notification = relationship("Notification", back_populates="agent_decision")

# 7. Durable Jobs & Observability
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    type: Mapped[str] = mapped_column(String(50), nullable=False) # ROUTE_POST, EMBED_AGENT, RESPOND_NOTIFICATION
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True) # PENDING, RUNNING, RETRY_WAIT, SUCCEEDED, FAILED, CANCELLED
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    lease_token: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False) # RELEVANT, IRRELEVANT
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "agent_id", "actor_user_id", name="uq_feedback_pair"),
    )

class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    counts: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    runtime_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    redacted_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid_str)
    principal_id: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("principal_id", "route", "key", name="uq_principal_route_key"),
    )

