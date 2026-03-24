from typing import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.database import engine as db_engine
from app.database.engine import get_session
from app.main import app
from app.schemas.agent_schema import AgentCreateRequest
from app.services.agent_repo import create_agent, create_purchase_request


@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(sqlite_engine, monkeypatch):
    monkeypatch.setattr(db_engine, "get_engine", lambda: sqlite_engine)

    def override_get_session() -> Generator[Session, None, None]:
        with Session(sqlite_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_agent(sqlite_engine):
    with Session(sqlite_engine) as session:
        agent = create_agent(
            session,
            AgentCreateRequest(
                handle="research-bot",
                display_name="Research Bot",
                bio="Helps rank datasets",
                capability_tags=["analysis", "ranking"],
                owner_address="0x0000000000000000000000000000000000000002",
            ),
        )
        request = create_purchase_request(
            session,
            agent.id,
            listing_id="listing-123",
            requester_address="0x0000000000000000000000000000000000000001",
            reason="Need a dataset for forecasting",
        )
        return {
            "handle": agent.handle,
            "capability_tags": ["analysis", "ranking"],
            "request_id": str(request.id),
        }


def test_agent_routes_serialize_sqlmodel_fields(client, seeded_agent):
    agent_handle = seeded_agent["handle"]
    capability_tags = seeded_agent["capability_tags"]
    request_id = seeded_agent["request_id"]

    list_response = client.get("/api/v1/agents")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 1
    assert list_payload["total"] == 1
    assert list_payload["agents"][0]["handle"] == agent_handle
    assert list_payload["agents"][0]["capability_tags"] == capability_tags

    detail_response = client.get(f"/api/v1/agents/{agent_handle}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["handle"] == agent_handle
    assert detail_payload["capability_tags"] == capability_tags

    scoped_response = client.get(f"/api/v1/agents/{agent_handle}/purchase-requests")
    assert scoped_response.status_code == 200
    scoped_payload = scoped_response.json()
    assert scoped_payload["count"] == 1
    assert scoped_payload["total"] == 1
    assert scoped_payload["requests"][0]["id"] == request_id
    assert scoped_payload["requests"][0]["status"] == "pending"

    global_response = client.get("/api/v1/purchase-requests")
    assert global_response.status_code == 200
    global_payload = global_response.json()
    assert global_payload["count"] == 1
    assert global_payload["total"] == 1
    assert global_payload["requests"][0]["id"] == request_id
    assert global_payload["requests"][0]["status"] == "pending"


def test_purchase_request_review_route_updates_status(client, seeded_agent, sqlite_engine):
    request_id = seeded_agent["request_id"]

    response = client.post(
        f"/api/v1/purchase-requests/{request_id}/review",
        json={
            "status": "approved",
            "reviewed_by": "0x0000000000000000000000000000000000000009",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["reviewed_by"] == "0x0000000000000000000000000000000000000009"

    with Session(sqlite_engine) as session:
        from app.models.agent import AgentPurchaseRequest

        updated = session.get(AgentPurchaseRequest, UUID(request_id))
        assert updated is not None
        assert updated.status == "approved"
        assert updated.reviewed_by == "0x0000000000000000000000000000000000000009"
