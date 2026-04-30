def test_health_check_returns_service_metadata(
    client, override_settings, settings_factory
):
    settings = settings_factory(APP_NAME="Ulenor Health", APP_VERSION="1.2.3")
    override_settings(settings=settings)

    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "version": "1.2.3",
        "service": "Ulenor Health",
    }


def test_readiness_check_returns_expected_dependencies(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "ready": True,
        "dependencies": {
            "ollama": "available",
            "database": "not_configured",
        },
    }
