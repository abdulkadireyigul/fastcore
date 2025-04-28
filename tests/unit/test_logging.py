"""
Unit tests for the logging module.

Covers:
- Logger creation and retrieval (get_logger, ensure_logger)
- Logger configuration (setup_logger)
- JSON formatter output (JsonFormatter)
- Edge cases and error handling

Fixtures are used for common setup to avoid duplication.
"""
import logging

import pytest

from fastcore.logging import JsonFormatter, ensure_logger, get_logger, setup_logger


@pytest.fixture
def dummy_settings():
    class DummySettings:
        LOG_LEVEL = "DEBUG"
        LOG_JSON_FORMAT = False

    return DummySettings()


def test_get_logger_returns_logger(dummy_settings):
    logger = get_logger("test.module", dummy_settings)
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_ensure_logger_returns_existing_logger(dummy_settings):
    logger = get_logger("test.ensure", dummy_settings)
    ensured = ensure_logger(logger, "test.ensure", dummy_settings)
    assert ensured is logger


def test_ensure_logger_creates_new_logger(dummy_settings):
    ensured = ensure_logger(None, "test.ensure2", dummy_settings)
    assert isinstance(ensured, logging.Logger)
    assert ensured.name == "test.ensure2"


def test_ensure_logger_raises_without_name():
    with pytest.raises(ValueError):
        ensure_logger()


def test_setup_logger_sets_level_and_format(dummy_settings):
    dummy_settings.LOG_LEVEL = "WARNING"
    dummy_settings.LOG_JSON_FORMAT = False
    logger = setup_logger(
        "test.setup",
        level=dummy_settings.LOG_LEVEL,
        debug=dummy_settings.LOG_LEVEL == "DEBUG",
        json_format=dummy_settings.LOG_JSON_FORMAT,
    )
    assert logger.level == logging.WARNING


def test_setup_logger_removes_existing_handlers():
    logger = logging.getLogger("test.handler")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    assert len(logger.handlers) == 1
    setup_logger("test.handler")
    assert len(logger.handlers) == 1  # Only the new handler remains


def test_setup_logger_invalid_level():
    logger = setup_logger("test.invalid", level="NOTALEVEL")
    assert logger.level == logging.INFO


def test_json_formatter_output():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.json",
        level=logging.INFO,
        pathname=__file__,
        lineno=123,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    assert output.startswith("{") and output.endswith("}")
    assert '"message": "Test message"' in output
