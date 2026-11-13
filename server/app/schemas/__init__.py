from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar("T")

# 1. Common Envelopes
class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: Optional[Dict[str, Any]] = None

class ErrorEnvelope(BaseModel):
    error: ErrorDetail
    request_id: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[str] = None
    request_id: Optional[str] = None

class SuccessResponse(BaseModel, Generic[T]):
    data: T
    request_id: Optional[str] = None

# 2. Auth Schemas
class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str

class SessionUser(BaseModel):
    id: str
    email: str
    role: str

class LoginResponse(BaseModel):
    user: SessionUser
    csrf_token: str
    message: str = "Login successful"

# 3. Agent Schemas
class AgentCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5, max_length=1000)
    verification_status: str = "DEMO"
    interest_text: str = Field(min_length=5, max_length=2000)
    include_topics: List[str] = Field(default_factory=list)
    exclude_topics: List[str] = Field(default_factory=list)
    threshold: float = Field(ge=0.0, le=1.0, default=0.60)
    hourly_limit: int = Field(gt=0, default=20)
    response_mode: str = "AUTO"

class AgentUpdateRequest(BaseModel):
    description: Optional[str] = None
    active: Optional[bool] = None

class SubscriptionUpdateRequest(BaseModel):
    interest_text: str = Field(min_length=5, max_length=2000)
    include_topics: List[str] = Field(default_factory=list)
    exclude_topics: List[str] = Field(default_factory=list)
    accepted_intents: List[str] = Field(default_factory=list)
    excluded_author_ids: List[str] = Field(default_factory=list)
    country_codes: List[str] = Field(default_factory=list)
    language_codes: List[str] = Field(default_factory=lambda: ["en"])
    threshold: float = Field(ge=0.0, le=1.0, default=0.60)
    hourly_limit: int = Field(gt=0, default=20)
    response_mode: str = "AUTO"
    expected_version: Optional[int] = None

class SubscriptionResponse(BaseModel):
    id: str
    agent_id: str
    enabled: bool
    interest_text: str
    include_topics: List[str]
    exclude_topics: List[str]
    accepted_intents: List[str]
    excluded_author_ids: List[str]
    country_codes: List[str]
    language_codes: List[str]
    threshold: float
    hourly_limit: int
    response_mode: str
    version: int
    updated_at: datetime

class AgentResponse(BaseModel):
    id: str
    company_name: str
    description: str
    verification_status: str
    active: bool
    profile_version: int
    created_at: datetime
    updated_at: datetime
    subscription: Optional[SubscriptionResponse] = None

class AgentRegisteredResponse(BaseModel):
    agent: AgentResponse
    api_key: str
    notice: str = "Store this API key safely; it will not be displayed again."

# 4. Post Schemas
class PostCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=2000)
    topics: List[str] = Field(default_factory=list, max_length=10)
    intent: str = Field(default="offer")
    country_code: str = Field(default="IN", max_length=2)
    language_code: str = Field(default="en", max_length=10)
    is_demo: bool = True
    expires_at: datetime

class PostResponse(BaseModel):
    id: str
    author_agent_id: str
    author_name: Optional[str] = None
    title: str
    content: str
    topics: List[str]
    intent: str
    country_code: str
    language_code: str
    is_demo: bool
    expires_at: datetime
    routing_state: str
    moderation_state: str
    created_at: datetime
    comment_count: int = 0

class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_agent_id: str
    author_name: Optional[str] = None
    notification_id: str
    campaign_id: Optional[str] = None
    content: str
    generation_mode: str
    created_at: datetime

# 5. Routing Schemas
class RouteDecisionItem(BaseModel):
    agent_id: str
    agent_name: str
    eligible: bool
    dense_score: Optional[float] = None
    topic_score: Optional[float] = None
    compatibility_score: Optional[float] = None
    final_score: Optional[float] = None
    threshold: float
    decision: str
    reason_codes: List[str]
    evidence: str

class RoutingInspectorResponse(BaseModel):
    post_id: str
    route_run_id: str
    policy_version: str
    model_revision: str
    candidate_count: int
    eligible_count: int
    selected_count: int
    started_at: datetime
    completed_at: Optional[datetime]
    decisions: List[RouteDecisionItem]

# 6. Inbox & Agent Decision Schemas
class InboxItem(BaseModel):
    notification_id: str
    post_id: str
    post_title: str
    post_content: str
    post_topics: List[str]
    post_intent: str
    author_agent_id: str
    author_name: Optional[str] = None
    delivery_state: str
    response_state: str
    created_at: datetime

class InboxClaimResponse(BaseModel):
    notification_id: str
    lease_token: str
    lease_expires_at: datetime

class AgentDecisionSubmission(BaseModel):
    action: str = Field(pattern="^(respond|ignore)$")
    reason_code: str
    reason: str = Field(max_length=500)
    campaign_id: Optional[str] = None
    draft: str = Field(default="", max_length=1000)
    lease_token: Optional[str] = None

# 7. Campaign Schemas
class CampaignCreateRequest(BaseModel):
    id: str = Field(min_length=3, max_length=100)
    title: str = Field(min_length=3, max_length=200)
    approved_terms: Dict[str, Any]
    allowed_topics: List[str] = Field(default_factory=list)
    starts_at: datetime
    expires_at: datetime
    is_demo: bool = True

class CampaignResponse(BaseModel):
    id: str
    agent_id: str
    title: str
    approved_terms: Dict[str, Any]
    allowed_topics: List[str]
    starts_at: datetime
    expires_at: datetime
    is_demo: bool
    active: bool
    created_at: datetime

# 8. Feedback & Moderation Schemas
class FeedbackCreateRequest(BaseModel):
    post_id: str
    agent_id: str
    label: str = Field(pattern="^(RELEVANT|IRRELEVANT)$")
    note: Optional[str] = None

class ModerationDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(ALLOW|REJECT)$")
    reason: str
