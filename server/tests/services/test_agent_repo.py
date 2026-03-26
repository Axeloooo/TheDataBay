import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session

from app.schemas.agent_schema import AgentCreateRequest, AgentUpdateRequest
from app.services import agent_repo


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def make_create_request(handle: str, **overrides) -> AgentCreateRequest:
    payload = {
        "handle": handle,
        "display_name": f"{handle.title()} Agent",
        "bio": f"{handle} bio",
        "avatar_url": f"https://example.com/{handle}.png",
        "homepage_url": f"https://example.com/{handle}",
        "capability_tags": ["search", "analysis"],
        "owner_address": "0x0000000000000000000000000000000000000001",
    }
    payload.update(overrides)
    return AgentCreateRequest(**payload)


def test_create_agent_and_get_by_handle_persists_across_sessions(db_engine):
    with Session(db_engine) as session:
        created = agent_repo.create_agent(
            session,
            make_create_request(
                "climate-bot",
                display_name="Climate Bot",
                capability_tags=["climate", "forecasting"],
            ),
        )

        assert created.handle == "climate-bot"
        assert json.loads(created.capability_tags) == ["climate", "forecasting"]
        assert created.created_at is not None
        assert created.updated_at is not None

    with Session(db_engine) as session:
        fetched = agent_repo.get_agent_by_handle(session, "climate-bot")

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.display_name == "Climate Bot"
        assert json.loads(fetched.capability_tags) == ["climate", "forecasting"]
        assert fetched.owner_address == "0x0000000000000000000000000000000000000001"


def test_list_agents_filters_by_search_tag_status_and_paginates(db_engine):
    with Session(db_engine) as session:
        climate = agent_repo.create_agent(
            session,
            make_create_request(
                "climate-bot",
                display_name="Climate Curator",
                capability_tags=["climate", "analysis"],
            ),
        )
        agent_repo.create_agent(
            session,
            make_create_request(
                "retail-helper",
                display_name="Retail Helper",
                capability_tags=["retail"],
            ),
        )
        verified = agent_repo.create_agent(
            session,
            make_create_request(
                "verified-climate",
                display_name="Verified Climate",
                capability_tags=["climate"],
            ),
        )

        climate.verification_status = "self_attested"
        verified.verification_status = "platform_verified"
        session.add(climate)
        session.add(verified)
        session.commit()

        search_results, search_total = agent_repo.list_agents(session, search="CLIMATE")
        tag_results, tag_total = agent_repo.list_agents(session, tag="climate")
        status_results, status_total = agent_repo.list_agents(
            session, status="platform_verified"
        )
        paged_results, paged_total = agent_repo.list_agents(session, offset=1, limit=1)

    assert {agent.handle for agent in search_results} == {
        "climate-bot",
        "verified-climate",
    }
    assert search_total == 2
    assert {agent.handle for agent in tag_results} == {
        "climate-bot",
        "verified-climate",
    }
    assert tag_total == 2
    assert [agent.handle for agent in status_results] == ["verified-climate"]
    assert status_total == 1
    assert len(paged_results) == 1
    assert paged_total == 3


def test_update_and_deactivate_agent_persist_changes(db_engine, monkeypatch):
    class FakeDateTime:
        current = datetime(2024, 1, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(agent_repo, "datetime", FakeDateTime)

    with Session(db_engine) as session:
        agent = agent_repo.create_agent(
            session,
            make_create_request(
                "buyer-bot",
                display_name="Buyer Bot",
                homepage_url="https://example.com/original",
                capability_tags=["buy"],
            ),
        )

        FakeDateTime.current = datetime(2024, 1, 2, tzinfo=timezone.utc)
        updated = agent_repo.update_agent(
            session,
            agent,
            AgentUpdateRequest(
                bio="Updated bio",
                capability_tags=["buy", "compare"],
            ),
        )

        assert updated.display_name == "Buyer Bot"
        assert updated.bio == "Updated bio"
        assert updated.homepage_url == "https://example.com/original"
        assert json.loads(updated.capability_tags) == ["buy", "compare"]
        assert updated.updated_at == datetime(2024, 1, 2)

        FakeDateTime.current = datetime(2024, 1, 3, tzinfo=timezone.utc)
        deactivated = agent_repo.deactivate_agent(session, updated)

        assert deactivated.is_active is False
        assert deactivated.updated_at == datetime(2024, 1, 3)

    with Session(db_engine) as session:
        persisted = agent_repo.get_agent_by_handle(session, "buyer-bot")

        assert persisted is not None
        assert persisted.bio == "Updated bio"
        assert json.loads(persisted.capability_tags) == ["buy", "compare"]
        assert persisted.is_active is False


def test_recommendation_crud_filtering_and_retraction_persist(db_engine, monkeypatch):
    class FakeDateTime:
        current = datetime(2024, 2, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(agent_repo, "datetime", FakeDateTime)

    with Session(db_engine) as session:
        agent = agent_repo.create_agent(session, make_create_request("rec-agent"))
        other_agent = agent_repo.create_agent(
            session, make_create_request("other-agent")
        )

        rec = agent_repo.create_recommendation(
            session=session,
            agent_id=agent.id,
            listing_id="listing-1",
            confidence=0.91,
            similarity_score=0.87,
            rationale="Strong match for climate analysis",
            pros=["High relevance"],
            cons=["Requires preprocessing"],
            suggested_use_cases=["portfolio research"],
        )
        agent_repo.create_recommendation(
            session=session,
            agent_id=other_agent.id,
            listing_id="listing-2",
            confidence=0.62,
            similarity_score=0.55,
            rationale="Useful but broader fit",
            pros=["Broad coverage"],
            cons=["Lower precision"],
            suggested_use_cases=["benchmarking"],
        )

        fetched = agent_repo.get_recommendation_by_id(session, rec.id)
        by_agent, by_agent_total = agent_repo.list_recommendations(
            session, agent_id=agent.id
        )
        by_listing, by_listing_total = agent_repo.list_recommendations(
            session, listing_id="listing-1"
        )

        FakeDateTime.current = datetime(2024, 2, 2, tzinfo=timezone.utc)
        retracted = agent_repo.retract_recommendation(session, rec)

    assert fetched is not None
    assert fetched.id == rec.id
    assert [item.id for item in by_agent] == [rec.id]
    assert by_agent_total == 1
    assert [item.id for item in by_listing] == [rec.id]
    assert by_listing_total == 1
    assert retracted.is_retracted is True
    assert retracted.updated_at == datetime(2024, 2, 2)

    with Session(db_engine) as session:
        persisted = agent_repo.get_recommendation_by_id(session, rec.id)

        assert persisted is not None
        assert persisted.is_retracted is True
        assert json.loads(persisted.pros) == ["High relevance"]
        assert json.loads(persisted.cons) == ["Requires preprocessing"]
        assert json.loads(persisted.suggested_use_cases) == ["portfolio research"]


def test_purchase_request_create_list_get_and_review_persist(db_engine, monkeypatch):
    class FakeDateTime:
        current = datetime(2024, 3, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current

    monkeypatch.setattr(agent_repo, "datetime", FakeDateTime)

    with Session(db_engine) as session:
        agent = agent_repo.create_agent(session, make_create_request("request-agent"))
        other_agent = agent_repo.create_agent(
            session, make_create_request("second-agent")
        )

        request = agent_repo.create_purchase_request(
            session,
            agent_id=agent.id,
            listing_id="listing-9",
            requester_address="0x0000000000000000000000000000000000000009",
            reason="Need training data for evaluation",
        )
        agent_repo.create_purchase_request(
            session,
            agent_id=other_agent.id,
            listing_id="listing-10",
            requester_address="0x0000000000000000000000000000000000000010",
            reason="Need a separate benchmark",
        )

        fetched = agent_repo.get_purchase_request_by_id(session, request.id)
        by_agent, by_agent_total = agent_repo.list_purchase_requests(
            session, agent_id=agent.id
        )
        by_requester, by_requester_total = agent_repo.list_purchase_requests(
            session,
            requester_address="0x0000000000000000000000000000000000000009",
        )

        FakeDateTime.current = datetime(2024, 3, 2, tzinfo=timezone.utc)
        reviewed = agent_repo.review_purchase_request(
            session,
            request,
            status="approved",
            reviewed_by="0x00000000000000000000000000000000000000aa",
        )
        approved, approved_total = agent_repo.list_purchase_requests(
            session, status="approved"
        )

    assert fetched is not None
    assert fetched.id == request.id
    assert [item.id for item in by_agent] == [request.id]
    assert by_agent_total == 1
    assert [item.id for item in by_requester] == [request.id]
    assert by_requester_total == 1
    assert reviewed.status == "approved"
    assert reviewed.reviewed_by == "0x00000000000000000000000000000000000000aa"
    assert reviewed.reviewed_at == datetime(2024, 3, 2)
    assert reviewed.updated_at == datetime(2024, 3, 2)
    assert [item.id for item in approved] == [request.id]
    assert approved_total == 1

    with Session(db_engine) as session:
        persisted = agent_repo.get_purchase_request_by_id(session, request.id)

        assert persisted is not None
        assert persisted.status == "approved"
        assert persisted.reviewed_by == "0x00000000000000000000000000000000000000aa"
        assert persisted.reviewed_at == datetime(2024, 3, 2)
        assert agent_repo.get_purchase_request_by_id(session, uuid.uuid4()) is None
