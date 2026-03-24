from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.models.agent import Agent, AgentPurchaseRequest, AgentRecommendation
from app.schemas.agent_schema import (
    AgentResponse,
    PurchaseRequestResponse,
    RecommendationResponse,
)


def test_agent_response_validates_sqlmodel_and_serializes_tags_as_array():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        agent = Agent(
            handle="research-bot",
            display_name="Research Bot",
            capability_tags='["analysis", "ranking"]',
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        response = AgentResponse.model_validate(agent)

    assert response.handle == "research-bot"
    assert response.capability_tags == ["analysis", "ranking"]
    assert response.model_dump()["capability_tags"] == ["analysis", "ranking"]


def test_recommendation_response_validates_sqlmodel():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        agent = Agent(handle="rec-bot", display_name="Recommendation Bot")
        session.add(agent)
        session.commit()
        session.refresh(agent)

        recommendation = AgentRecommendation(
            agent_id=agent.id,
            listing_id="listing-123",
            confidence=0.92,
            similarity_score=0.81,
            rationale="Strong topical match",
            pros='["fast", "accurate"]',
            cons='["niche"]',
            suggested_use_cases='["forecasting", "ranking"]',
        )
        session.add(recommendation)
        session.commit()
        session.refresh(recommendation)

        response = RecommendationResponse.model_validate(recommendation)

    assert response.listing_id == "listing-123"
    assert response.pros == ["fast", "accurate"]
    assert response.cons == ["niche"]
    assert response.suggested_use_cases == ["forecasting", "ranking"]


def test_purchase_request_response_validates_sqlmodel():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        agent = Agent(handle="purchase-bot", display_name="Purchase Bot")
        session.add(agent)
        session.commit()
        session.refresh(agent)

        purchase_request = AgentPurchaseRequest(
            agent_id=agent.id,
            listing_id="listing-456",
            requester_address="0x0000000000000000000000000000000000000001",
            reason="Need this dataset for modeling",
        )
        session.add(purchase_request)
        session.commit()
        session.refresh(purchase_request)

        response = PurchaseRequestResponse.model_validate(purchase_request)

    assert response.listing_id == "listing-456"
    assert response.status == "pending"
    assert response.requester_address == "0x0000000000000000000000000000000000000001"
