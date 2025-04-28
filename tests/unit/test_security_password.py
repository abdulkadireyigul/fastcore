"""
Unit tests for security.password module.
Covers: password hashing and verification.
"""
import pytest

from fastcore.security import password


def test_get_password_hash_and_verify():
    plain = "mysecretpassword"
    hashed = password.get_password_hash(plain)
    assert isinstance(hashed, str)
    assert hashed != plain
    assert password.verify_password(plain, hashed)


def test_verify_password_wrong():
    plain = "mysecretpassword"
    wrong = "notmysecret"
    hashed = password.get_password_hash(plain)
    assert not password.verify_password(wrong, hashed)


def test_verify_password_invalid_hash():
    # Should not raise, just return False
    assert not password.verify_password("any", "invalidhash")
