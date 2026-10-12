import uuid
from datetime import datetime, timezone

import pytest
from eth_account import Account

from app.agents.models import Agent, AgentPurchaseRequest, AgentRecommendation
from app.agents import router as agent_router


def make_agent(handle: str, **overrides) -> Agent:
    payload = {
        "id": uuid.uuid4(),
        "handle": handle,
        "display_name": f"{handle.title()} Agent",
        "bio": f"{handle} bio",
        "avatar_url": f"https://example.com/{handle}.png",
        "homepage_url": f"https://example.com/{handle}",
        "capability_tags": '["search","analysis"]',
        "verification_status": "unverified",
        "owner_address": "0x0000000000000000000000000000000000000001",
        "is_active": True,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return Agent(**payload)


def make_recommendation(
    agent_id: uuid.UUID, listing_id: str = "listing-1", **overrides
):
    payload = {
        "id": uuid.uuid4(),
        "agent_id": agent_id,
        "listing_id": listing_id,
        "confidence": 0.88,
        "similarity_score": 0.81,
        "rationale": "Best semantic match for the query",
        "pros": '["Strong match"]',
        "cons": '["Review suggested"]',
        "suggested_use_cases": '["prototype search"]',
        "is_retracted": False,
        "created_at": datetime(2024, 2, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 2, 1, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return AgentRecommendation(**payload)


def make_purchase_request(
    agent_id: uuid.UUID, listing_id: str = "listing-1", **overrides
):
    payload = {
        "id": uuid.uuid4(),
        "agent_id": agent_id,
        "listing_id": listing_id,
        "requester_address": "0x00000000000000000000000000000000000000ab",
        "status": "pending",
        "reason": "Need benchmark data",
        "reviewed_at": None,
        "reviewed_by": None,
        "created_at": datetime(2024, 3, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 1, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return AgentPurchaseRequest(**payload)


@pytest.fixture(autouse=True)
def override_agent_dependencies(client, db_session):
    client.app.dependency_overrides[agent_router.get_session] = lambda: db_session
    client.app.dependency_overrides[agent_router.agent_write_rate_limiter] = (
        lambda: None
    )
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(agent_router.get_session, None)
        client.app.dependency_overrides.pop(agent_router.agent_write_rate_limiter, None)
        client.app.dependency_overrides.pop(agent_router.get_ai_service, None)


def test_register_agent_returns_created_agent(client, monkeypatch):
    created = make_agent("climate-bot", display_name="Climate Bot")
    captured = {}

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: None
    )

    def fake_create_agent(session, data):
        captured["session"] = session
        captured["data"] = data
        return created

    monkeypatch.setattr(agent_router, "create_agent", fake_create_agent)

    response = client.post(
        "/api/v1/agents/",
        json={
            "handle": "climate-bot",
            "display_name": "Climate Bot",
            "bio": "Finds climate data",
            "capability_tags": ["climate", "analysis"],
        },
    )

    assert response.status_code == 201
    assert response.json()["handle"] == "climate-bot"
    assert response.json()["display_name"] == "Climate Bot"
    assert response.json()["capability_tags"] == ["search", "analysis"]
    assert captured["data"].handle == "climate-bot"
    assert captured["data"].display_name == "Climate Bot"
    assert captured["data"].capability_tags == ["climate", "analysis"]


def test_register_agent_returns_409_for_duplicate_handle(client, monkeypatch):
    monkeypatch.setattr(
        agent_router,
        "get_agent_by_handle",
        lambda session, handle: make_agent(handle),
    )
    monkeypatch.setattr(
        agent_router,
        "create_agent",
        lambda session, data: (_ for _ in ()).throw(
            AssertionError("create_agent should not be called for duplicate handles")
        ),
    )

    response = client.post(
        "/api/v1/agents/",
        json={"handle": "climate-bot", "display_name": "Climate Bot"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Handle already taken"}


def test_list_agents_returns_paginated_response(client, monkeypatch):
    agents = [
        make_agent("climate-bot"),
        make_agent("retail-helper", capability_tags='["retail"]'),
    ]
    captured = {}

    def fake_list_agents(
        session, search=None, tag=None, status=None, offset=0, limit=20
    ):
        captured["args"] = {
            "session": session,
            "search": search,
            "tag": tag,
            "status": status,
            "offset": offset,
            "limit": limit,
        }
        return agents, 5

    monkeypatch.setattr(agent_router, "list_agents", fake_list_agents)

    response = client.get(
        "/api/v1/agents/",
        params={
            "search": "climate",
            "tag": "analysis",
            "status": "unverified",
            "offset": 2,
            "limit": 2,
        },
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["total"] == 5
    assert [item["handle"] for item in response.json()["agents"]] == [
        "climate-bot",
        "retail-helper",
    ]
    assert captured["args"]["search"] == "climate"
    assert captured["args"]["tag"] == "analysis"
    assert captured["args"]["status"] == "unverified"
    assert captured["args"]["offset"] == 2
    assert captured["args"]["limit"] == 2


def test_get_agent_returns_agent(client, monkeypatch):
    monkeypatch.setattr(
        agent_router,
        "get_agent_by_handle",
        lambda session, handle: make_agent(handle, display_name="Climate Bot"),
    )

    response = client.get("/api/v1/agents/climate-bot")

    assert response.status_code == 200
    assert response.json()["handle"] == "climate-bot"
    assert response.json()["display_name"] == "Climate Bot"


def test_get_agent_returns_404_when_missing(client, monkeypatch):
    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: None
    )

    response = client.get("/api/v1/agents/missing-bot")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}


def test_update_agent_returns_updated_agent(client, monkeypatch):
    existing = make_agent("climate-bot", display_name="Old Name")
    updated = make_agent(
        "climate-bot",
        display_name="New Name",
        bio="Updated bio",
        capability_tags='["climate","ranker"]',
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    captured = {}

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: existing
    )

    def fake_update_agent(session, agent, data):
        captured["agent"] = agent
        captured["data"] = data
        return updated

    monkeypatch.setattr(agent_router, "update_agent", fake_update_agent)

    response = client.patch(
        "/api/v1/agents/climate-bot",
        json={
            "display_name": "New Name",
            "bio": "Updated bio",
            "capability_tags": ["climate", "ranker"],
        },
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"
    assert response.json()["bio"] == "Updated bio"
    assert response.json()["capability_tags"] == ["climate", "ranker"]
    assert captured["agent"].id == existing.id
    assert captured["data"].display_name == "New Name"
    assert captured["data"].capability_tags == ["climate", "ranker"]


def test_update_agent_returns_404_when_missing(client, monkeypatch):
    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: None
    )

    response = client.patch("/api/v1/agents/missing-bot", json={"bio": "Updated bio"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}


def test_generate_recommendation_returns_recommendation(client, monkeypatch):
    agent = make_agent("climate-bot")
    recommendation = make_recommendation(agent.id)
    captured = {}
    ai_service = object()

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: agent
    )

    async def fake_generate(agent_id, query, session, resolved_ai_service):
        captured["args"] = {
            "agent_id": agent_id,
            "query": query,
            "session": session,
            "ai_service": resolved_ai_service,
        }
        return recommendation

    monkeypatch.setattr(agent_router, "generate_recommendation_service", fake_generate)
    client.app.dependency_overrides[agent_router.get_ai_service] = lambda: ai_service

    response = client.post(
        "/api/v1/agents/climate-bot/recommend",
        json={"query": "  find climate datasets  "},
    )

    assert response.status_code == 200
    assert response.json()["listing_id"] == "listing-1"
    assert response.json()["pros"] == ["Strong match"]
    assert response.json()["cons"] == ["Review suggested"]
    assert response.json()["suggested_use_cases"] == ["prototype search"]
    assert captured["args"]["agent_id"] == agent.id
    assert captured["args"]["query"] == "find climate datasets"
    assert captured["args"]["ai_service"] is ai_service


def test_generate_recommendation_returns_404_when_no_results(client, monkeypatch):
    agent = make_agent("climate-bot")
    ai_service = object()

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: agent
    )

    async def fake_generate(agent_id, query, session, resolved_ai_service):
        return None

    monkeypatch.setattr(agent_router, "generate_recommendation_service", fake_generate)
    client.app.dependency_overrides[agent_router.get_ai_service] = lambda: ai_service

    response = client.post(
        "/api/v1/agents/climate-bot/recommend",
        json={"query": "no matches"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No matching datasets found for query"}


def test_retract_recommendation_returns_updated_record(client, monkeypatch):
    agent = make_agent("climate-bot")
    original = make_recommendation(agent.id)
    retracted = make_recommendation(
        agent.id,
        is_retracted=True,
        id=original.id,
        updated_at=datetime(2024, 2, 2, tzinfo=timezone.utc),
    )
    captured = {}

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: agent
    )
    monkeypatch.setattr(
        agent_router, "get_recommendation_by_id", lambda session, rec_id: original
    )

    def fake_retract(session, rec):
        captured["rec"] = rec
        return retracted

    monkeypatch.setattr(agent_router, "retract_recommendation_repo", fake_retract)

    response = client.post(
        f"/api/v1/agents/climate-bot/recommendations/{original.id}/retract"
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(original.id)
    assert response.json()["is_retracted"] is True
    assert captured["rec"].id == original.id


def test_submit_purchase_request_returns_created_request(client, monkeypatch):
    agent = make_agent("buyer-bot")
    created = make_purchase_request(agent.id, listing_id="listing-9")
    captured = {}

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: agent
    )

    def fake_create_request(session, agent_id, listing_id, requester_address, reason):
        captured["args"] = {
            "agent_id": agent_id,
            "listing_id": listing_id,
            "requester_address": requester_address,
            "reason": reason,
        }
        return created

    monkeypatch.setattr(agent_router, "create_purchase_request", fake_create_request)

    response = client.post(
        "/api/v1/agents/buyer-bot/purchase-requests",
        json={
            "listing_id": "listing-9",
            "requester_address": "0x00000000000000000000000000000000000000ab",
            "reason": "Need benchmark data",
        },
    )

    assert response.status_code == 201
    assert response.json()["listing_id"] == "listing-9"
    assert response.json()["status"] == "pending"
    assert captured["args"] == {
        "agent_id": agent.id,
        "listing_id": "listing-9",
        # Stored in EIP-55 checksum form.
        "requester_address": "0x00000000000000000000000000000000000000AB",
        "reason": "Need benchmark data",
    }


def test_submit_purchase_request_rejects_invalid_requester_address(
    client, monkeypatch
):
    monkeypatch.setattr(
        agent_router,
        "get_agent_by_handle",
        lambda session, handle: make_agent(handle),
    )
    monkeypatch.setattr(
        agent_router,
        "create_purchase_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("create_purchase_request should not be called")
        ),
    )

    response = client.post(
        "/api/v1/agents/buyer-bot/purchase-requests",
        json={
            "listing_id": "listing-9",
            "requester_address": "not-an-address",
            "reason": "Need benchmark data",
        },
    )

    assert response.status_code == 422


def test_list_agent_purchase_requests_returns_filtered_requests(client, monkeypatch):
    agent = make_agent("buyer-bot")
    requests = [
        make_purchase_request(agent.id, listing_id="listing-1"),
        make_purchase_request(agent.id, listing_id="listing-2"),
    ]
    captured = {}

    monkeypatch.setattr(
        agent_router, "get_agent_by_handle", lambda session, handle: agent
    )

    def fake_list_requests(session, agent_id=None, status=None, offset=0, limit=20):
        captured["args"] = {
            "agent_id": agent_id,
            "status": status,
            "offset": offset,
            "limit": limit,
        }
        return requests, 4

    monkeypatch.setattr(agent_router, "list_purchase_requests", fake_list_requests)

    response = client.get(
        "/api/v1/agents/buyer-bot/purchase-requests",
        params={"status": "pending", "offset": 1, "limit": 2},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["total"] == 4
    assert [item["listing_id"] for item in response.json()["requests"]] == [
        "listing-1",
        "listing-2",
    ]
    assert captured["args"] == {
        "agent_id": agent.id,
        "status": "pending",
        "offset": 1,
        "limit": 2,
    }


def test_list_all_purchase_requests_defaults_to_pending(client, monkeypatch):
    requests = [make_purchase_request(uuid.uuid4(), listing_id="listing-3")]
    captured = {}

    def fake_list_requests(session, agent_id=None, status=None, offset=0, limit=20):
        captured["args"] = {
            "agent_id": agent_id,
            "status": status,
            "offset": offset,
            "limit": limit,
        }
        return requests, 1

    monkeypatch.setattr(agent_router, "list_purchase_requests", fake_list_requests)

    response = client.get("/api/v1/purchase-requests/")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["requests"][0]["listing_id"] == "listing-3"
    assert captured["args"] == {
        "agent_id": None,
        "status": "pending",
        "offset": 0,
        "limit": 20,
    }


REQUESTER = Account.create().address
STRANGER = Account.create().address


@pytest.fixture
def pending_request(db_session):
    """A pending purchase request persisted in the test database.

    requester_address is stored lowercase to prove the ownership check is
    case-insensitive against the checksummed address in the token.
    """
    agent = make_agent("buyer-bot")
    db_session.add(agent)
    db_session.commit()
    req = make_purchase_request(
        agent.id, listing_id="listing-7", requester_address=REQUESTER.lower()
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def _review(client, request_id, status="approved", headers=None, **extra):
    return client.post(
        f"/api/v1/purchase-requests/{request_id}/review",
        json={"status": status, **extra},
        headers=headers or {},
    )


def test_review_without_token_returns_401(client, db_session, pending_request):
    response = _review(client, pending_request.id)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    db_session.refresh(pending_request)
    assert pending_request.status == "pending"
    assert pending_request.reviewed_by is None


def test_review_with_admin_scope_token_returns_401(
    client, db_session, pending_request, auth_headers
):
    response = _review(
        client, pending_request.id, headers=auth_headers(REQUESTER, scope="admin")
    )

    assert response.status_code == 401
    db_session.refresh(pending_request)
    assert pending_request.status == "pending"


def test_review_by_other_wallet_returns_403(
    client, db_session, pending_request, auth_headers
):
    response = _review(
        client,
        pending_request.id,
        headers=auth_headers(STRANGER),
        # A forged reviewed_by naming the requester must not help.
        reviewed_by=REQUESTER,
    )

    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"
    db_session.refresh(pending_request)
    assert pending_request.status == "pending"
    assert pending_request.reviewed_by is None


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_review_by_requester_records_token_wallet(
    client, db_session, pending_request, auth_headers, decision
):
    response = _review(
        client,
        pending_request.id,
        status=decision,
        headers=auth_headers(REQUESTER),
        # Older clients still send reviewed_by; it is ignored.
        reviewed_by=STRANGER,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(pending_request.id)
    assert body["status"] == decision
    assert body["reviewed_by"] == REQUESTER
    assert body["reviewed_at"] is not None
    db_session.refresh(pending_request)
    assert pending_request.status == decision
    assert pending_request.reviewed_by == REQUESTER


def test_second_review_returns_409_and_keeps_first_decision(
    client, db_session, pending_request, auth_headers
):
    headers = auth_headers(REQUESTER)
    first = _review(client, pending_request.id, status="approved", headers=headers)
    second = _review(client, pending_request.id, status="rejected", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"] == "already_reviewed"
    assert second.json()["details"] == {"status": "approved"}
    db_session.refresh(pending_request)
    assert pending_request.status == "approved"


def test_review_missing_request_returns_404(client, auth_headers):
    response = _review(client, uuid.uuid4(), headers=auth_headers(REQUESTER))

    assert response.status_code == 404


def test_review_rejects_unknown_status(client, pending_request, auth_headers):
    response = _review(
        client, pending_request.id, status="completed", headers=auth_headers(REQUESTER)
    )

    assert response.status_code == 422


def test_review_returns_409_when_concurrent_review_wins(
    client, pending_request, auth_headers, monkeypatch
):
    # The route saw "pending", but the conditional UPDATE matched no row.
    monkeypatch.setattr(
        agent_router,
        "review_purchase_request_repo",
        lambda session, req, status, reviewed_by: None,
    )

    response = _review(client, pending_request.id, headers=auth_headers(REQUESTER))

    assert response.status_code == 409
    assert response.json()["error"] == "already_reviewed"


def test_review_route_documents_auth_errors(client):
    schema = client.get("/openapi.json").json()
    review = schema["paths"]["/api/v1/purchase-requests/{request_id}/review"]["post"]
    body_ref = review["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    body_schema = schema["components"]["schemas"][body_ref.rsplit("/", 1)[-1]]

    assert {"401", "403", "404", "409"} <= set(review["responses"])
    assert "reviewed_by" not in body_schema["properties"]
