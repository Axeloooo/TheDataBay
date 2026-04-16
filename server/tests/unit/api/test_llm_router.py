from app.routers import llm_router
from app.schemas.job_schema import JobResponse, JobStatusResponse


def test_create_batch_embeddings_returns_accepted_job(client, monkeypatch):
    captured = {}

    async def fake_enqueue_batch_job(**kwargs):
        captured.update(kwargs)
        return JobResponse(
            job_id="job-123",
            status="queued",
            listing_id="listing-123",
        )

    monkeypatch.setattr(llm_router, "enqueue_batch_job", fake_enqueue_batch_job)

    response = client.post(
        "/api/v1/llm/embed/batch",
        data={
            "title": "Retail Data",
            "description": "Point of sale records",
            "seller": "0x0000000000000000000000000000000000000001",
            "price_atomic": "250",
        },
        files={"file": ("retail.csv", b"id,total\n1,20\n", "text/csv")},
    )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "job-123",
        "status": "queued",
        "listing_id": "listing-123",
    }
    assert captured["file"].filename == "retail.csv"
    assert captured["title"] == "Retail Data"
    assert captured["description"] == "Point of sale records"
    assert captured["seller"] == "0x0000000000000000000000000000000000000001"
    assert captured["price"] == 250
    assert captured["seller_wallet_type"] == "evm"


def test_create_batch_embeddings_requires_price(client, monkeypatch):
    async def fail_enqueue_batch_job(**kwargs):
        raise AssertionError("enqueue_batch_job should not be called without a price")

    monkeypatch.setattr(llm_router, "enqueue_batch_job", fail_enqueue_batch_job)

    response = client.post(
        "/api/v1/llm/embed/batch",
        data={
            "title": "Retail Data",
            "description": "Point of sale records",
            "seller": "0x0000000000000000000000000000000000000001",
        },
        files={"file": ("retail.csv", b"id,total\n1,20\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "price_atomic is required."}


def test_create_batch_embeddings_rejects_non_usdc_settlement(client, monkeypatch):
    async def fail_enqueue_batch_job(**kwargs):
        raise AssertionError(
            "enqueue_batch_job should not be called for unsupported settlement currency"
        )

    monkeypatch.setattr(llm_router, "enqueue_batch_job", fail_enqueue_batch_job)

    response = client.post(
        "/api/v1/llm/embed/batch",
        data={
            "title": "Retail Data",
            "description": "Point of sale records",
            "seller": "0x0000000000000000000000000000000000000001",
            "price_atomic": "250",
            "settlement_currency": "ETH",
        },
        files={"file": ("retail.csv", b"id,total\n1,20\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only USDC settlement is supported."}


def test_create_batch_embeddings_rejects_invalid_settlement_decimals(
    client, monkeypatch
):
    async def fail_enqueue_batch_job(**kwargs):
        raise AssertionError(
            "enqueue_batch_job should not be called for invalid settlement decimals"
        )

    monkeypatch.setattr(llm_router, "enqueue_batch_job", fail_enqueue_batch_job)

    response = client.post(
        "/api/v1/llm/embed/batch",
        data={
            "title": "Retail Data",
            "description": "Point of sale records",
            "seller": "0x0000000000000000000000000000000000000001",
            "price_atomic": "250",
            "settlement_decimals": "18",
        },
        files={"file": ("retail.csv", b"id,total\n1,20\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Settlement decimals must equal 6 for USDC."}


def test_embed_query_returns_vector_payload(client, monkeypatch, settings):
    monkeypatch.setattr(
        llm_router,
        "generate_single_embedding",
        lambda query, resolved_settings: ([0.25, 0.75], 2),
    )

    response = client.post(
        "/api/v1/llm/embed/query",
        json={"query": "weekly revenue"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_query": "weekly revenue",
        "query_embedding": [0.25, 0.75],
        "vector_spec": {
            "model": settings.embedding_model,
            "dimension": 2,
        },
    }


def test_embed_query_validates_non_empty_query(client, monkeypatch):
    monkeypatch.setattr(
        llm_router,
        "generate_single_embedding",
        lambda query, settings: (_ for _ in ()).throw(
            AssertionError("generate_single_embedding should not be called")
        ),
    )

    response = client.post("/api/v1/llm/embed/query", json={"query": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    errors = body["details"]["errors"]
    assert any(error["loc"][-1] == "query" for error in errors)


def test_get_job_status_returns_router_response(client, monkeypatch):
    def fake_get_job_status(job_id, job_manager):
        return JobStatusResponse(
            job_id=job_id,
            status="completed",
            listing_id="listing-123",
            created_at="2026-03-26T12:00:00Z",
            started_at="2026-03-26T12:00:01Z",
            completed_at="2026-03-26T12:00:05Z",
            error=None,
            vector_spec={"model": "nomic-embed-text", "dimension": 2},
            stats={
                "total_rows": 2,
                "total_columns": 2,
                "empty_rows_skipped": 0,
                "has_header": True,
            },
            signature={
                "signature_url": "ipfs://signature",
                "signature_hash": "0xsignature",
            },
            dataset_url="ipfs://dataset",
            dataset_hash="0xdataset",
            filename="retail.csv",
        )

    monkeypatch.setattr(llm_router, "get_job_status_service", fake_get_job_status)

    response = client.get("/api/v1/llm/jobs/job-123")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-123"
    assert response.json()["status"] == "completed"
    assert response.json()["listing_id"] == "listing-123"
    assert response.json()["filename"] == "retail.csv"
