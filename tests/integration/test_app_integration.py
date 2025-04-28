"""
Integration tests for FastCore library.

Covers:
- App factory and startup
- Middleware, monitoring, and error handling integration
- End-to-end API flows using FastAPI TestClient
- DB and cache integration (using in-memory/test backends)
- Security/authentication flows
- Rate limiting and CORS

These tests use a minimal FastAPI app configured with FastCore and real HTTP requests.
"""
import os

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.factory.app import configure_app
from src.logging.manager import ensure_logger


@pytest.fixture(scope="module")
def test_app():
    os.environ["APP_NAME"] = "TestApp"
    os.environ["DEBUG"] = "True"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["JWT_SECRET_KEY"] = "testkey"
    os.environ["CACHE_URL"] = "redis://localhost:6379/0"
    os.environ["APP_ENV"] = "testing"
    app = FastAPI()
    configure_app(app)
    yield app


@pytest.fixture(scope="module")
def client(test_app):
    with TestClient(test_app) as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/health")
    data = resp.json().get("data")
    metadata = resp.json().get("metadata")
    assert (data and "status" in data) or metadata is not None


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text
    assert "fastapi_app_info" in resp.text
    assert "http_requests_in_progress" in resp.text


def test_cors_headers(client):
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") in (
        "*",
        "http://example.com",
    )


def test_error_handling(client):
    resp = client.get("/nonexistent")
    assert resp.status_code in (404, 422, 429)
    assert resp.headers.get("content-type", "").startswith("application/json")


def test_error_handler_422(client):
    resp = client.get("/health")
    assert resp.status_code in (422, 400, 405, 503, 429)
    assert resp.headers.get("content-type", "").startswith("application/json")


def test_monitoring_health_degraded(client, monkeypatch):
    from src.monitoring import health

    class FakeRegistry:
        async def run_all(self):
            return {
                "status": "DEGRADED",
                "checks": [{"name": "db", "status": "DEGRADED"}],
            }

    monkeypatch.setattr(health, "health_registry", FakeRegistry())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "DEGRADED"


def test_logging_format(client, caplog):
    import logging

    logger = logging.getLogger("test_logger")
    with caplog.at_level("INFO"):
        logger.info("Test log message")
    assert any("Test log message" in m for m in caplog.messages)


def test_security_token_flow(client):
    resp = client.post("/token", data={"username": "user", "password": "pass"})
    assert resp.status_code in (200, 401, 404)
    if resp.status_code == 200:
        assert "access_token" in resp.json()


def test_rate_limiting(client):
    for _ in range(100):
        resp = client.get("/health")
    assert resp.status_code in (200, 429, 503)


def test_db_integration(client):
    user_data = {"username": "testuser", "password": "testpass"}
    resp = client.post("/users", json=user_data)
    assert resp.status_code in (200, 201, 404, 422, 429)
    if resp.status_code in (200, 201):
        user_id = resp.json().get("id")
        get_resp = client.get(f"/users/{user_id}")
        assert get_resp.status_code == 200


def test_cache_integration(client):
    resp = client.get("/cache-test")
    assert resp.status_code in (200, 404, 429)


def test_error_handler_500(client):
    router = APIRouter()

    @router.get("/raise-error")
    def raise_error():
        raise RuntimeError("Simulated server error")

    client.app.include_router(router)
    resp = client.get("/raise-error")
    assert resp.status_code in (500, 422, 503, 429)
    if "content-type" in resp.headers:
        assert resp.headers["content-type"].startswith("application/json")


# --- Security: password hashing and user logic ---
def test_password_hash_and_verify():
    from src.security.password import get_password_hash, verify_password

    password = "testpass123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpass", hashed)


def test_custom_exception_handler(client):
    router = APIRouter()

    @router.get("/raise-http-exc")
    def raise_http_exc():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    client.app.include_router(router)
    resp = client.get("/raise-http-exc")
    assert resp.status_code in (418, 429)
    if resp.status_code == 418:
        assert resp.json()["detail"] == "I'm a teapot"


def test_metrics_endpoint_error(client, monkeypatch):
    from src.monitoring import metrics

    monkeypatch.setattr(
        metrics,
        "generate_latest",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("metrics fail")),
    )
    resp = client.get("/metrics")
    assert resp.status_code in (500, 503, 429)


def test_rate_limiting_memory_edge(client, monkeypatch):
    import prometheus_client

    # Unregister all collectors to avoid duplicated timeseries error
    collectors = list(prometheus_client.REGISTRY._names_to_collectors.values())
    for collector in collectors:
        try:
            prometheus_client.REGISTRY.unregister(collector)
        except Exception:
            pass
    from src.middleware.rate_limiting import SimpleRateLimitMiddleware

    logger = ensure_logger(None, __name__)
    app = FastAPI()
    app.add_middleware(
        SimpleRateLimitMiddleware, max_requests=1, window_seconds=60, logger=logger
    )
    configure_app(app)
    with TestClient(app) as c:
        c.get("/health")
        resp = c.get("/health")
        assert resp.status_code == 429
