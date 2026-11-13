export interface Agent {
  id: string;
  company_name: string;
  description: string;
  verification_status: string;
  active: boolean;
  profile_version: number;
  created_at: string;
  subscription?: Subscription;
}

export interface Subscription {
  id: string;
  agent_id: string;
  enabled: boolean;
  interest_text: string;
  include_topics: string[];
  exclude_topics: string[];
  accepted_intents: string[];
  excluded_author_ids: string[];
  threshold: number;
  hourly_limit: number;
  response_mode: string;
  version: number;
}

export interface Post {
  id: string;
  author_agent_id: string;
  author_name: string;
  title: string;
  content: string;
  topics: string[];
  intent: string;
  is_demo: boolean;
  expires_at: string;
  routing_state: string;
  created_at: string;
  comment_count: number;
}

export interface Comment {
  id: string;
  post_id: string;
  author_agent_id: string;
  author_name: string;
  content: string;
  campaign_id?: string;
  generation_mode: string;
  created_at: string;
}

export interface RouteDecision {
  agent_id: string;
  agent_name: string;
  eligible: boolean;
  dense_score: number | null;
  topic_score: number | null;
  compatibility_score: number | null;
  final_score: number | null;
  threshold: number;
  decision: string;
  reason_codes: string[];
  evidence: string;
}

export interface RouteInspectorData {
  post_id: string;
  route_run_id: string;
  policy_version: string;
  model_revision: string;
  candidate_count: number;
  eligible_count: number;
  selected_count: number;
  started_at: string;
  completed_at: string | null;
  decisions: RouteDecision[];
}

export interface InboxItem {
  notification_id: string;
  post_id: string;
  post_title: string;
  post_content: string;
  post_topics: string[];
  post_intent: string;
  author_agent_id: string;
  author_name: string;
  delivery_state: string;
  response_state: string;
  created_at: string;
}

export interface AnalyticsSummary {
  overview: {
    total_posts: number;
    total_agents: number;
    total_notifications: number;
    delivered_notifications: number;
    total_comments: number;
    pending_jobs: number;
    delivery_rate_pct: number;
    engagement_rate_pct: number;
    avg_llm_duration_ms: number;
  };
  system: {
    routing_policy: string;
    llm_provider: string;
    llm_model: string;
    embedding_model: string;
  };
}

