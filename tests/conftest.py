import pytest


# Example: shared fixture for environment variable cleanup
def pytest_configure(config):
    # Called before any tests are run
    pass


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Automatically clear certain environment variables before each test if needed
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    yield
    # No teardown needed, monkeypatch handles it


# Add more shared fixtures as your test suite grows
