"""
Seed data for agent-related tables.
"""

import json
import uuid
from datetime import datetime, timezone
from sqlmodel import Session, select
from ..agents.models import Agent, AgentRecommendation, AgentPurchaseRequest
from .mock_marketplace_items import load_mock_marketplace_items

# Use fixed UUIDs so seeds are idempotent
QUALITY_AUDITOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
FINANCE_SCOUT_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
NLP_RECOMMENDER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def seed_agents(session: Session) -> None:
    """Seed demo agent data. Idempotent — skips if agents already exist."""

    # Check if already seeded
    existing = session.exec(
        select(Agent).where(Agent.handle == "quality-auditor")
    ).first()
    if existing:
        return

    now = datetime.now(timezone.utc)
    mock_items = load_mock_marketplace_items()
    demo_listing_1 = mock_items[0].listing_id
    demo_listing_2 = mock_items[1].listing_id

    # Demo Agent 1: quality-auditor (platform_verified)
    agent1 = Agent(
        id=QUALITY_AUDITOR_ID,
        handle="quality-auditor",
        display_name="Quality Auditor",
        bio="I evaluate dataset quality, completeness, and metadata accuracy for marketplace listings.",
        capability_tags=json.dumps(["data-quality", "audit", "metadata"]),
        verification_status="platform_verified",
        owner_address="0x1234567890123456789012345678901234567890",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    # Demo Agent 2: finance-scout (self_attested)
    agent2 = Agent(
        id=FINANCE_SCOUT_ID,
        handle="finance-scout",
        display_name="Finance Scout",
        bio="Specialized in discovering financial datasets for quantitative research and algorithmic trading.",
        capability_tags=json.dumps(["finance", "trading", "quant", "time-series"]),
        verification_status="self_attested",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    # Demo Agent 3: nlp-recommender (unverified)
    agent3 = Agent(
        id=NLP_RECOMMENDER_ID,
        handle="nlp-recommender",
        display_name="NLP Recommender",
        bio="Uses semantic similarity to match datasets to NLP research tasks.",
        capability_tags=json.dumps(["nlp", "text", "embeddings", "semantic-search"]),
        verification_status="unverified",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    session.add_all([agent1, agent2, agent3])
    session.commit()

    # Demo Recommendation 1: finance-scout recommends listing 1
    rec1 = AgentRecommendation(
        agent_id=FINANCE_SCOUT_ID,
        listing_id=demo_listing_1,
        confidence=0.87,
        similarity_score=0.87,
        rationale="Strong semantic match for financial time-series data needs.",
        pros=json.dumps(["High relevance score", "Contains structured financial data"]),
        cons=json.dumps(["May require normalization"]),
        suggested_use_cases=json.dumps(["Quantitative trading", "Risk modeling"]),
        is_retracted=False,
        created_at=now,
        updated_at=now,
    )

    # Demo Recommendation 2: nlp-recommender recommends listing 2
    rec2 = AgentRecommendation(
        agent_id=NLP_RECOMMENDER_ID,
        listing_id=demo_listing_2,
        confidence=0.72,
        similarity_score=0.72,
        rationale="Good match for NLP classification and text analysis tasks.",
        pros=json.dumps(["Diverse text samples", "Pre-labeled categories"]),
        cons=json.dumps(["Smaller dataset size", "English-only"]),
        suggested_use_cases=json.dumps(["Text classification", "Sentiment analysis"]),
        is_retracted=False,
        created_at=now,
        updated_at=now,
    )

    session.add_all([rec1, rec2])
    session.commit()

    # Demo Purchase Request: quality-auditor requests listing 1
    req1 = AgentPurchaseRequest(
        agent_id=QUALITY_AUDITOR_ID,
        listing_id=demo_listing_1,
        requester_address="0x9999999999999999999999999999999999999999",
        status="pending",
        reason="Need to audit dataset quality before certifying for marketplace.",
        created_at=now,
        updated_at=now,
    )

    session.add(req1)
    session.commit()
