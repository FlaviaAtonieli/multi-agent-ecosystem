import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings, settings
from app.core.rate_limit import resolve_client_ip


def _make_request(client_host: str, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "client": (client_host, 12345),
        "headers": [
            (key.lower().encode(), value.encode()) for key, value in (headers or {}).items()
        ],
    }
    return Request(scope)


def test_production_without_cookie_secure_is_rejected() -> None:
    with pytest.raises(ValueError, match="COOKIE_SECURE=true"):
        Settings(_env_file=None, environment="production", cookie_secure=False)


def test_production_with_cookie_secure_is_accepted() -> None:
    settings = Settings(_env_file=None, environment="production", cookie_secure=True)
    assert settings.is_production is True


def test_development_without_cookie_secure_is_accepted() -> None:
    dev_settings = Settings(_env_file=None, environment="development", cookie_secure=False)
    assert dev_settings.is_production is False


def test_resolve_client_ip_uses_direct_ip_by_default() -> None:
    request = _make_request("203.0.113.9", {"X-Forwarded-For": "198.51.100.1"})
    assert resolve_client_ip(request) == "203.0.113.9"


def test_resolve_client_ip_trusts_forwarded_header_from_configured_proxy(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_ips", "172.18.0.5")
    request = _make_request("172.18.0.5", {"X-Forwarded-For": "198.51.100.1, 172.18.0.5"})
    assert resolve_client_ip(request) == "198.51.100.1"


def test_resolve_client_ip_ignores_forwarded_header_from_untrusted_peer(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_ips", "172.18.0.5")
    # A request that connects directly (not via the trusted proxy) cannot spoof
    # its way past the rate limit just by sending its own X-Forwarded-For.
    request = _make_request("203.0.113.9", {"X-Forwarded-For": "198.51.100.1"})
    assert resolve_client_ip(request) == "203.0.113.9"


def test_oversized_body_is_rejected_before_reaching_the_route(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "max_request_body_bytes", 1024)
    response = client.post("/api/v1/auth/login", content=b"x" * 2048)
    assert response.status_code == 413
    assert response.json()["error"] == "PAYLOAD_TOO_LARGE"


def test_body_within_limit_reaches_normal_validation(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "not-real", "password": "x"})
    # Rejected by request validation (bad payload shape), not by the size guard.
    assert response.status_code in (400, 401, 403, 422)
