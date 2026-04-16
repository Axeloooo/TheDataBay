"""
Business logic service for agentic layer operations.
"""

import asyncio
import uuid
from typing import Optional

from sqlmodel import Session

from ..models.agent import AgentRecommendation
from ..services.agent_repo import create_recommendation
from ..services.ai_service import AIService

MIN_SIMILARITY_SCORE = 0.1


async def generate_recommendation(
    agent_id: uuid.UUID,
    query: str,
    session: Session,
    ai_service: AIService,
) -> Optional[AgentRecommendation]:
    """Generate an agent recommendation for the best-matching dataset.

    Uses AIService to semantically rank marketplace datasets against *query*
    and persists the top result as an AgentRecommendation.

    Args:
        agent_id: UUID of the agent issuing the recommendation.
        query: Natural-language query describing the desired dataset.
        session: Database session for persisting the recommendation.
        ai_service: AIService instance used for semantic ranking.

    Returns:
        Optional[AgentRecommendation]: The newly created recommendation record,
        or None if no matching datasets are found or score is below threshold.
    """
    results = await ai_service.rank_datasets(query)

    if not results:
        return None

    top = results[0]

    if top.score < MIN_SIMILARITY_SCORE:
        return None

    # top.score is already clamped to [0.0, 1.0] by AIService
    confidence = float(top.score)
    similarity_score = confidence

    rationale = f"Top semantic match for query: '{query}'. Dataset: {top.title}"
    pros = [
        f"High semantic similarity score: {top.score:.3f}",
        f"Dataset: {top.title}",
    ]
    cons = ["Recommendation is based on semantic similarity only, not manual curation"]
    suggested_use_cases = [query]

    return create_recommendation(
        session=session,
        agent_id=agent_id,
        listing_id=top.listing_id,
        confidence=confidence,
        similarity_score=similarity_score,
        rationale=rationale,
        pros=pros,
        cons=cons,
        suggested_use_cases=suggested_use_cases,
    )
