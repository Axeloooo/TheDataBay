import pytest
from pydantic import ValidationError

from .conftest import make_settings


def test_auth_ttl_defaults(settings):
    assert settings.auth_token_ttl_seconds == 3600
    assert settings.auth_admin_token_ttl_seconds == 300
    assert settings.auth_nonce_ttl_seconds == 300


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AUTH_TOKEN_TTL_SECONDS", 59),
        ("AUTH_TOKEN_TTL_SECONDS", 86401),
        ("AUTH_NONCE_TTL_SECONDS", 29),
        ("AUTH_NONCE_TTL_SECONDS", 901),
        ("AUTH_ADMIN_TOKEN_TTL_SECONDS", 29),
        ("AUTH_ADMIN_TOKEN_TTL_SECONDS", 301),
    ],
)
def test_auth_ttl_out_of_bounds_is_rejected(name, value):
    with pytest.raises(ValidationError):
        make_settings(**{name: value})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AUTH_TOKEN_TTL_SECONDS", 60),
        ("AUTH_TOKEN_TTL_SECONDS", 86400),
        ("AUTH_NONCE_TTL_SECONDS", 30),
        ("AUTH_NONCE_TTL_SECONDS", 900),
        ("AUTH_ADMIN_TOKEN_TTL_SECONDS", 30),
        ("AUTH_ADMIN_TOKEN_TTL_SECONDS", 300),
    ],
)
def test_auth_ttl_bounds_are_inclusive(name, value):
    make_settings(**{name: value})
