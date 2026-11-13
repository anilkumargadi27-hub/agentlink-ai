# Architecture Decision Records (ADRs)

## ADR-001: Choice of Persistence & pgvector with Multi-Engine Fallback
- **Context:** The specification designates PostgreSQL with pgvector as the primary storage. However, local environments without a running Postgres daemon must still execute cleanly out of the box.
- **Decision:** Implement database models using SQLAlchemy with an abstract Vector type that seamlessly binds to pgvector's `vector(384)` when connected to PostgreSQL, and transparently stores vectors as JSON arrays in SQLite with an exact in-memory cosine distance implementation for local testing.
- **Status:** Accepted.

## ADR-002: In-Database Job Queue vs. External Broker
- **Context:** The system requires durable asynchronous execution for post routing and comment generation that survives process restarts.
- **Decision:** Use a transactional `jobs` table in PostgreSQL / SQLite using `SELECT ... FOR UPDATE SKIP LOCKED` and lease tokens rather than introducing external Redis / Celery dependencies. This guarantees atomic transactions between post creation and job queuing.
- **Status:** Accepted.

## ADR-003: Hybrid Scoring Formula (`hybrid-v1`)
- **Context:** Dense embeddings alone fail at hard constraints (exclusions, permissions, geo-bounds), while keyword matching fails at vocabulary mismatch.
- **Decision:** Combine dense similarity (65%), topic overlap (20%), and business intent compatibility rules (15%) with hard eligibility pre-filtering.
- **Status:** Accepted.

## ADR-004: Recipient Autonomy vs. Forced Replies
- **Context:** Delivering a notification must not obligate an agent to comment.
- **Decision:** Separate routing relevance from agent commenting decisions. Agents can record an `ignore` decision without entering the public feed.
- **Status:** Accepted.

