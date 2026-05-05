import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main as main_module


def test_root_returns_service_info_and_request_id(
    client, override_settings, settings_factory, caplog
):
    settings = settings_factory(
        APP_NAME="TheDataBay Test API",
        APP_VERSION="9.9.9",
        ENVIRONMENT="test",
    )
    override_settings(settings=settings)
    caplog.clear()

    with caplog.at_level(logging.INFO, logger=main_module.logger.name):
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {
        "service": "TheDataBay Test API",
        "version": "9.9.9",
        "environment": "test",
        "links": {
            "docs": "/api/v1/docs",
            "redoc": "/api/v1/redoc",
            "health": "/health",
            "config": "/config",
        },
    }
    assert any(
        "request.start method=GET path=/" in record.getMessage()
        for record in caplog.records
    )
    assert any(
        "request.done method=GET path=/ status=200" in record.getMessage()
        for record in caplog.records
    )


def test_root_echoes_incoming_request_id(client):
    response = client.get("/", headers={"x-request-id": "req-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"


def test_request_logging_middleware_logs_errors(caplog):
    test_app = FastAPI()
    test_app.middleware("http")(main_module.request_logging_middleware)

    @test_app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    with TestClient(test_app, raise_server_exceptions=False) as test_client:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger=main_module.logger.name):
            response = test_client.get("/boom", headers={"x-request-id": "req-boom"})

    assert response.status_code == 500
    assert "x-request-id" not in response.headers
    assert any(
        "request.error method=GET path=/boom" in record.getMessage()
        and getattr(record, "request_id", None) == "req-boom"
        for record in caplog.records
    )
