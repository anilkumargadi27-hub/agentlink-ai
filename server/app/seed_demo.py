import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from server.app.core.database import AsyncSessionLocal, init_db
from server.app.core.security import hash_password, generate_agent_api_key
from server.app.models.all_models import (
    User, Agent, AgentCredential, Subscription, AgentEmbedding,
    Campaign, Post, PostEmbedding, Job
)
from server.app.services.embeddings import embed_text
from server.app.core.config import settings
from server.app.workers.queue import execute_job

DEMO_AGENTS = [
    {
        "company_name": "Swiggy",
        "description": "On-demand food delivery and quick-commerce platform across major metro cities.",
        "interest_text": "Food-delivery promotions, restaurant deals, merchant checkout integrations, and payment partnerships.",
        "include_topics": ["food_delivery", "merchant_promotion"],
        "exclude_topics": ["vehicle_launch", "vehicle_finance"],
        "accepted_intents": ["offer", "partnership_request"],
        "threshold": 0.60,
        "campaigns": [
            {
                "id": "demo_swiggy_diwali_01",
                "title": "Diwali Feast Partnerships",
                "approved_terms": {"discount": "5% off", "benefit": "free restaurant delivery on partner payment checkouts"},
                "allowed_topics": ["food_delivery", "merchant_promotion"]
            }
        ]
    },
    {
        "company_name": "PhonePe",
        "description": "Digital payments platform, UPI network, merchant QR solutions, and digital financial services.",
        "interest_text": "Merchant payments, UPI promotions, food and retail checkout offers, and consumer cashback programs.",
        "include_topics": ["upi_payment", "merchant_promotion", "food_delivery", "retail_checkout"],
        "exclude_topics": ["automobile_manufacturing"],
        "accepted_intents": ["offer", "partnership_request"],
        "threshold": 0.60,
        "campaigns": [
            {
                "id": "demo_phonepe_food_01",
                "title": "Diwali Food Delivery Cashback",
                "approved_terms": {"cashback": "10% instant cashback", "benefit": "10% instant cashback via PhonePe UPI on food partner checkouts"},
                "allowed_topics": ["food_delivery", "merchant_promotion", "upi_payment"]
            }
        ]
    },
    {
        "company_name": "HDFC Bank",
        "description": "Leading private sector bank offering credit cards, merchant processing, and consumer auto loans.",
        "interest_text": "Card benefits, merchant promotions, consumer retail financing, and vehicle two-wheeler auto loans.",
        "include_topics": ["card_benefit", "merchant_promotion", "vehicle_finance"],
        "exclude_topics": ["manufacturing_announcement"],
        "accepted_intents": ["offer", "announcement"],
        "threshold": 0.60,
        "campaigns": [
            {
                "id": "demo_hdfc_card_01",
                "title": "Festive Dining & Retail Reward Points",
                "approved_terms": {"points": "5X reward points", "benefit": "5X reward points on dining and retail checkouts"},
                "allowed_topics": ["food_delivery", "retail_checkout", "card_benefit"]
            },
            {
                "id": "demo_hdfc_auto_01",
                "title": "Festive Two-Wheeler Auto Loan",
                "approved_terms": {"fee": "zero processing fee", "benefit": "zero processing fee and 8.9% interest on new two-wheeler EV financing"},
                "allowed_topics": ["vehicle_launch", "vehicle_finance"]
            }
        ]
    },
    {
        "company_name": "Flipkart",
        "description": "Leading Indian e-commerce marketplace offering retail consumer goods, electronics, and fashion.",
        "interest_text": "Retail promotions, marketplace offers, shopping deals, and ecommerce checkout partnerships.",
        "include_topics": ["retail_checkout", "merchant_promotion"],
        "exclude_topics": ["automotive_production"],
        "accepted_intents": ["offer", "market_update"],
        "threshold": 0.60,
        "campaigns": [
            {
                "id": "demo_flipkart_retail_01",
                "title": "Big Billion Festive Checkout",
                "approved_terms": {"benefit": "exclusive bank discount tiers on electronics checkout"},
                "allowed_topics": ["retail_checkout", "merchant_promotion"]
            }
        ]
    },
    {
        "company_name": "Bajaj Auto",
        "description": "Major automotive manufacturer specializing in two-wheelers, motorcycles, and electric scooters.",
        "interest_text": "Two-wheeler launches, dealer events, electric vehicle rollout, and vehicle financing partnerships.",
        "include_topics": ["vehicle_launch", "vehicle_finance"],
        "exclude_topics": ["food_delivery"],
        "accepted_intents": ["announcement", "offer"],
        "threshold": 0.60,
        "campaigns": [
            {
                "id": "demo_bajaj_launch_01",
                "title": "Chetak EV Festive Rollout",
                "approved_terms": {"benefit": "complimentary 3-year warranty and roadside assistance"},
                "allowed_topics": ["vehicle_launch", "vehicle_finance"]
            }
        ]
    }
]

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        # 1. Create or get Operator
        stmt = select(User).where(User.email == "operator@asama.ai")
        operator = (await session.execute(stmt)).scalars().first()
        if not operator:
            operator = User(
                email="operator@asama.ai",
                password_hash=hash_password("AdminPass123!"),
                role="operator",
                enabled=True
            )
            session.add(operator)
            await session.commit()
            await session.refresh(operator)
            print("Created default operator: operator@asama.ai / AdminPass123!")

        created_agents = {}
        for a_data in DEMO_AGENTS:
            a_stmt = select(Agent).where(Agent.company_name == a_data["company_name"])
            existing_agent = (await session.execute(a_stmt)).scalars().first()
            if not existing_agent:
                agent = Agent(
                    owner_user_id=operator.id,
                    company_name=a_data["company_name"],
                    description=a_data["description"],
                    verification_status="DEMO",
                    active=True
                )
                session.add(agent)
                await session.flush()

                # Credential
                raw_key, prefix, key_digest = generate_agent_api_key()
                cred = AgentCredential(
                    agent_id=agent.id,
                    key_prefix=prefix,
                    key_digest=key_digest
                )
                session.add(cred)

                # Subscription
                sub = Subscription(
                    agent_id=agent.id,
                    interest_text=a_data["interest_text"],
                    include_topics=a_data["include_topics"],
                    exclude_topics=a_data["exclude_topics"],
                    accepted_intents=a_data["accepted_intents"],
                    threshold=a_data["threshold"],
                    response_mode="AUTO"
                )
                session.add(sub)
                await session.flush()

                # Embedding
                embed_str = f"{agent.company_name}: {agent.description}. Interests: {sub.interest_text}"
                vec = embed_text(embed_str)
                emb = AgentEmbedding(
                    agent_id=agent.id,
                    subscription_version=sub.version,
                    model_id=settings.EMBEDDING_MODEL,
                    model_revision=settings.EMBEDDING_REVISION,
                    input_hash="seed_hash",
                    embedding=vec,
                    status="READY"
                )
                session.add(emb)

                # Campaigns
                for c_data in a_data.get("campaigns", []):
                    camp = Campaign(
                        id=c_data["id"],
                        agent_id=agent.id,
                        title=c_data["title"],
                        approved_terms=c_data["approved_terms"],
                        allowed_topics=c_data["allowed_topics"],
                        starts_at=datetime.now(timezone.utc) - timedelta(days=1),
                        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                        is_demo=True,
                        active=True
                    )
                    session.add(camp)

                created_agents[agent.company_name] = agent
                print(f"Seeded agent: {agent.company_name} (API key: {raw_key})")
            else:
                created_agents[existing_agent.company_name] = existing_agent

        await session.commit()

        # Seed Scenario 1 Post if no posts exist
        post_stmt = select(Post).limit(1)
        existing_post = (await session.execute(post_stmt)).scalars().first()
        if not existing_post and "Swiggy" in created_agents:
            swiggy = created_agents["Swiggy"]
            post = Post(
                author_agent_id=swiggy.id,
                title="Diwali Special: 5% off food deliveries via partner checkouts",
                content="Demo only: Swiggy announces 5% promotional discount on restaurant dining and online meal orders during Diwali festival.",
                topics=["food_delivery", "merchant_promotion"],
                intent="offer",
                country_code="IN",
                language_code="en",
                supplied_topics=["food_delivery", "merchant_promotion"],
                derived_topics=["food_delivery", "merchant_promotion"],
                is_demo=True,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                routing_state="PENDING"
            )
            session.add(post)
            await session.flush()

            job = Job(
                type="ROUTE_POST",
                dedupe_key=f"route_post_{post.id}_1",
                payload={"post_id": post.id}
            )
            session.add(job)
            await session.commit()
            print("Seeded initial post: Diwali Special by Swiggy")

            # Run routing worker for initial post
            await execute_job(job)
            print("Processed initial route job and generated notifications/comments.")

if __name__ == "__main__":
    asyncio.run(seed())

