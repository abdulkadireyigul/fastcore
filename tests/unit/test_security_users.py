"""
Unit tests for security.users module.
Covers: user authentication protocol, base class, and error handling.
"""
import pytest

from src.security.users import (
    AuthenticationError,
    BaseUserAuthentication,
    UserAuthentication,
)

# Use shared dummy_session fixture from conftest.py


class DummyUser:
    def __init__(self, user_id):
        self.id = user_id


class DummyAuth(BaseUserAuthentication[DummyUser]):
    async def authenticate(self, credentials):
        if (
            credentials.get("username") == "user"
            and credentials.get("password") == "pass"
        ):
            return DummyUser("123")
        return None

    async def get_user_by_id(self, user_id):
        if user_id == "123":
            return DummyUser("123")
        return None

    def get_user_id(self, user):
        return user.id


def test_authentication_error_inheritance():
    err = AuthenticationError("fail", code="ERR", details={"x": 1})
    assert isinstance(err, Exception)
    assert err.code == "ERR"
    assert err.details == {"x": 1}
    assert err.status_code == 401


@pytest.mark.asyncio
async def test_dummy_auth_success(dummy_session):
    auth = DummyAuth(session=dummy_session)
    user = await auth.authenticate({"username": "user", "password": "pass"})
    assert isinstance(user, DummyUser)
    assert auth.get_user_id(user) == "123"
    user2 = await auth.get_user_by_id("123")
    assert isinstance(user2, DummyUser)


@pytest.mark.asyncio
async def test_dummy_auth_failure(dummy_session):
    auth = DummyAuth(session=dummy_session)
    user = await auth.authenticate({"username": "bad", "password": "wrong"})
    assert user is None
    user2 = await auth.get_user_by_id("notfound")
    assert user2 is None
