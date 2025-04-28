from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Response, status

from fastcore.monitoring.health import (
    HealthCheck,
    HealthCheckRegistry,
    HealthStatus,
    db_health_check,
    health_registry,
    redis_health_check,
    setup_health_endpoint,
)
from fastcore.schemas.response.data import DataResponse
from fastcore.schemas.response.error import ErrorResponse


@pytest.mark.asyncio
async def test_health_check_run_success():
    async def ok():
        return {"status": HealthStatus.HEALTHY, "details": {"foo": "bar"}}

    hc = HealthCheck("ok", ok, tags=["t"])
    result = await hc.run()
    assert result["name"] == "ok"
    assert result["status"] == HealthStatus.HEALTHY
    assert result["details"] == {"foo": "bar"}
    assert result["tags"] == ["t"]


@pytest.mark.asyncio
async def test_health_check_run_exception():
    async def fail():
        raise Exception("fail")

    hc = HealthCheck("fail", fail)
    result = await hc.run()
    assert result["status"] == HealthStatus.UNHEALTHY
    assert "fail" in result["details"]["error"]


@pytest.mark.asyncio
async def test_health_check_registry_run_all():
    reg = HealthCheckRegistry()

    async def ok():
        return {"status": HealthStatus.HEALTHY}

    async def bad():
        return {"status": HealthStatus.UNHEALTHY}

    reg.register(HealthCheck("ok", ok))
    reg.register(HealthCheck("bad", bad))
    result = await reg.run_all()
    assert result["status"] == HealthStatus.UNHEALTHY
    assert len(result["checks"]) == 2


@pytest.mark.asyncio
async def test_health_check_registry_empty():
    reg = HealthCheckRegistry()
    result = await reg.run_all()
    assert result["status"] == HealthStatus.HEALTHY
    assert result["checks"] == []


@pytest.mark.asyncio
async def test_redis_health_check_success(monkeypatch):
    mock_cache = AsyncMock()
    mock_cache.ping.return_value = True

    async def fake_get_cache():
        return mock_cache

    monkeypatch.setattr("fastcore.monitoring.health.get_cache", fake_get_cache)
    result = await redis_health_check()
    assert result["status"] == HealthStatus.HEALTHY
    assert result["details"]["ping"] is True


@pytest.mark.asyncio
async def test_redis_health_check_failure(monkeypatch):
    mock_cache = AsyncMock()
    mock_cache.ping.side_effect = Exception("fail")

    async def fake_get_cache():
        return mock_cache

    monkeypatch.setattr("fastcore.monitoring.health.get_cache", fake_get_cache)
    result = await redis_health_check()
    assert result["status"] == HealthStatus.UNHEALTHY
    assert "fail" in result["details"]["error"]


@pytest.mark.asyncio
async def test_db_health_check_success(monkeypatch):
    mock_db = AsyncMock()
    mock_db.execute.return_value = 1

    async def fake_get_db():
        yield mock_db

    monkeypatch.setattr("fastcore.monitoring.health.get_db", fake_get_db)
    result = await db_health_check()
    assert result["status"] == HealthStatus.HEALTHY
    assert result["details"]["connected"] is True


@pytest.mark.asyncio
async def test_db_health_check_failure(monkeypatch):
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("fail")

    async def fake_get_db():
        yield mock_db

    monkeypatch.setattr("fastcore.monitoring.health.get_db", fake_get_db)
    result = await db_health_check()
    assert result["status"] == HealthStatus.UNHEALTHY
    assert result["details"]["connected"] is False
    assert "fail" in result["details"]["error"]


@pytest.mark.asyncio
async def test_db_health_check_exception(monkeypatch):
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("db fail")

    async def fake_get_db():
        yield mock_db

    monkeypatch.setattr("fastcore.monitoring.health.get_db", fake_get_db)
    result = await db_health_check()
    assert result["status"] == HealthStatus.UNHEALTHY
    assert result["details"]["connected"] is False
    assert "db fail" in result["details"]["error"]


@pytest.mark.asyncio
async def test_health_check_route_branches(monkeypatch):
    # Setup FastAPI app and settings
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    settings.HEALTH_PATH = "/health"
    settings.HEALTH_INCLUDE_DETAILS = True
    logger = MagicMock()
    # Patch health_registry to control run_all output
    monkeypatch.setattr(
        "fastcore.monitoring.health.health_registry", HealthCheckRegistry()
    )
    # Set HEALTH_INCLUDE_DETAILS = False before endpoint setup
    settings.HEALTH_INCLUDE_DETAILS = False
    setup_health_endpoint(app, settings, logger)
    # Get the route handler
    route_handler = app.include_router.call_args[0][0].routes[0].endpoint
    # Mock response
    response = MagicMock()
    # Healthy
    monkeypatch.setattr(
        "fastcore.monitoring.health.health_registry.run_all",
        AsyncMock(return_value={"status": HealthStatus.HEALTHY, "checks": []}),
    )
    result = await route_handler(response)
    assert isinstance(result, DataResponse)
    # Unhealthy
    monkeypatch.setattr(
        "fastcore.monitoring.health.health_registry.run_all",
        AsyncMock(return_value={"status": HealthStatus.UNHEALTHY, "checks": []}),
    )
    result = await route_handler(response)
    assert isinstance(result, ErrorResponse)
    # Degraded
    monkeypatch.setattr(
        "fastcore.monitoring.health.health_registry.run_all",
        AsyncMock(return_value={"status": HealthStatus.DEGRADED, "checks": []}),
    )
    result = await route_handler(response)
    assert isinstance(result, DataResponse)
    # No details
    monkeypatch.setattr(
        "fastcore.monitoring.health.health_registry.run_all",
        AsyncMock(
            return_value={
                "status": HealthStatus.HEALTHY,
                "checks": [{"details": {"foo": "bar"}}],
            }
        ),
    )
    result = await route_handler(response)
    assert isinstance(result, DataResponse)
    # Details should be removed
    assert "details" not in result.data["checks"][0]


def test_setup_health_endpoint_registers(monkeypatch):
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    settings.HEALTH_PATH = "/health"
    settings.HEALTH_INCLUDE_DETAILS = True
    logger = MagicMock()
    monkeypatch.setattr(
        "fastcore.monitoring.health.health_registry", HealthCheckRegistry()
    )
    setup_health_endpoint(app, settings, logger)
    app.include_router.assert_called_once()
    logger.info.assert_called()


def test_setup_monitoring(monkeypatch):
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    called = {}
    monkeypatch.setattr(
        "fastcore.monitoring.manager.setup_health_endpoint",
        lambda *a, **kw: called.setdefault("health", True),
    )
    monkeypatch.setattr(
        "fastcore.monitoring.manager.setup_metrics_endpoint",
        lambda *a, **kw: called.setdefault("metrics", True),
    )
    from fastcore.monitoring.manager import setup_monitoring

    setup_monitoring(app, settings, logger)
    assert called["health"]
    assert called["metrics"]
    logger.info.assert_called()


# --- metrics.py tests ---
# import types
from fastcore.monitoring.metrics import PrometheusMiddleware, setup_metrics_endpoint

# from prometheus_client import REGISTRY


@pytest.mark.asyncio
async def test_prometheus_middleware_excluded_path():
    app = MagicMock(spec=FastAPI)
    middleware = PrometheusMiddleware(app, exclude_paths=["/skip"])
    request = MagicMock()
    request.url.path = "/skip"
    request.method = "GET"
    call_next = AsyncMock(return_value="resp")
    result = await middleware.dispatch(request, call_next)
    assert result == "resp"


@pytest.mark.asyncio
async def test_prometheus_middleware_normal(monkeypatch):
    app = MagicMock(spec=FastAPI)
    middleware = PrometheusMiddleware(app)
    request = MagicMock()
    request.url.path = "/foo"
    request.method = "GET"
    call_next = AsyncMock(return_value=MagicMock(status_code=200))
    # Patch prometheus metrics to avoid side effects
    monkeypatch.setattr("fastcore.monitoring.metrics.REQUEST_IN_PROGRESS", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.REQUEST_LATENCY", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.REQUEST_COUNT", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.EXCEPTIONS_COUNT", MagicMock())
    result = await middleware.dispatch(request, call_next)
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_prometheus_middleware_exception(monkeypatch):
    app = MagicMock(spec=FastAPI)
    middleware = PrometheusMiddleware(app)
    request = MagicMock()
    request.url.path = "/foo"
    request.method = "GET"

    def raise_exc(*a, **kw):
        raise ValueError("fail")

    call_next = AsyncMock(side_effect=raise_exc)
    monkeypatch.setattr("fastcore.monitoring.metrics.REQUEST_IN_PROGRESS", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.REQUEST_LATENCY", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.REQUEST_COUNT", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.EXCEPTIONS_COUNT", MagicMock())
    with pytest.raises(ValueError):
        await middleware.dispatch(request, call_next)


def test_setup_metrics_endpoint(monkeypatch):
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    settings.METRICS_PATH = "/metrics"
    settings.METRICS_EXCLUDE_PATHS = ["/metrics", "/health"]
    logger = MagicMock()
    monkeypatch.setattr("fastcore.monitoring.metrics.PrometheusMiddleware", MagicMock())
    monkeypatch.setattr("fastcore.monitoring.metrics.Gauge", MagicMock())
    setup_metrics_endpoint(app, settings, logger)
    app.add_middleware.assert_called()
    app.include_router.assert_called()
    logger.info.assert_called()
