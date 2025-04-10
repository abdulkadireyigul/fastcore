"""
Tests for custom logging handlers.
"""

import logging
import os
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from fastcore.logging.handlers import (
    BufferedHandler,
    RequestContextHandler,
    SafeRotatingFileHandler,
)


class TestBufferedHandler:
    """Tests for the BufferedHandler class."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        self.handler = BufferedHandler(capacity=5)
        self.logger = logging.getLogger("test_buffer")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)
        # Ensure no other handlers affect our tests
        self.logger.propagate = False

    def test_init(self):
        """Test initialization of BufferedHandler."""
        handler = BufferedHandler(capacity=100, level=logging.ERROR)
        assert handler.capacity == 100
        assert handler.level == logging.ERROR
        assert handler.buffer == []

    def test_emit(self):
        """Test that records are properly emitted to the buffer."""
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")

        assert len(self.handler.buffer) == 3
        assert self.handler.buffer[0].levelname == "DEBUG"
        assert self.handler.buffer[0].msg == "Debug message"
        assert self.handler.buffer[1].levelname == "INFO"
        assert self.handler.buffer[1].msg == "Info message"
        assert self.handler.buffer[2].levelname == "WARNING"
        assert self.handler.buffer[2].msg == "Warning message"

    def test_capacity_limit(self):
        """Test that buffer respects capacity limit."""
        # Log more messages than the capacity
        for i in range(10):
            self.logger.info(f"Message {i}")

        # Buffer should only contain the 5 most recent messages
        assert len(self.handler.buffer) == 5
        assert self.handler.buffer[0].msg == "Message 5"
        assert self.handler.buffer[-1].msg == "Message 9"

    def test_get_records_all(self):
        """Test retrieving all records from the buffer."""
        messages = ["Message 1", "Message 2", "Message 3"]
        for msg in messages:
            self.logger.info(msg)

        # By default, get_records returns all records in reverse order (newest first)
        records = self.handler.get_records()
        assert len(records) == 3
        assert records[0].msg == "Message 3"
        assert records[1].msg == "Message 2"
        assert records[2].msg == "Message 1"

    def test_get_records_limit(self):
        """Test retrieving limited records from the buffer."""
        messages = ["Message 1", "Message 2", "Message 3", "Message 4"]
        for msg in messages:
            self.logger.info(msg)

        # Get only the 2 most recent records
        records = self.handler.get_records(limit=2)
        assert len(records) == 2
        assert records[0].msg == "Message 4"
        assert records[1].msg == "Message 3"

        # Limit larger than buffer should return all records
        records = self.handler.get_records(limit=10)
        assert len(records) == 4

    def test_clear(self):
        """Test clearing the buffer."""
        self.logger.info("Test message")
        assert len(self.handler.buffer) == 1

        self.handler.clear()
        assert len(self.handler.buffer) == 0


class TestSafeRotatingFileHandler:
    """Tests for the SafeRotatingFileHandler class."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        # Create a temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.temp_dir, "logs", "test.log")
        self.logger = logging.getLogger("test_rotating")
        self.logger.setLevel(logging.DEBUG)
        # Ensure no other handlers affect our tests
        self.logger.propagate = False

    def teardown_method(self):
        """Clean up test fixtures after each test."""
        # Remove any handlers from the logger
        self.logger.handlers = []
        # Clean up temp files
        try:
            if os.path.exists(self.log_path):
                os.remove(self.log_path)
            log_dir = os.path.dirname(self.log_path)
            if os.path.exists(log_dir):
                os.rmdir(log_dir)
            os.rmdir(self.temp_dir)
        except (PermissionError, OSError):
            # On Windows, sometimes files can't be deleted immediately
            pass

    def test_auto_create_directory(self):
        """Test that log directory is created automatically."""
        # The logs directory shouldn't exist yet
        log_dir = os.path.dirname(self.log_path)
        assert not os.path.exists(log_dir)

        # Creating the handler should create the directory
        handler = SafeRotatingFileHandler(
            filename=self.log_path,
            maxBytes=1024,
            backupCount=3,
        )
        self.logger.addHandler(handler)

        # Directory should have been created
        assert os.path.exists(log_dir)

        # Test that logging works
        self.logger.info("Test log message")
        assert os.path.exists(self.log_path)

        # Close handler
        handler.close()

    def test_rotation(self):
        """Test that log rotation works correctly."""
        # Create a handler with a very small max size to trigger rotation
        handler = SafeRotatingFileHandler(
            filename=self.log_path,
            maxBytes=50,  # Very small to trigger rotation quickly
            backupCount=2,
        )
        self.logger.addHandler(handler)

        # Write enough logs to trigger rotation multiple times
        for i in range(10):
            self.logger.info(
                f"Test log message {i} with some padding to make it longer"
            )

        # Check that the main log file exists
        assert os.path.exists(self.log_path)

        # Check that backup files were created (up to backupCount)
        assert os.path.exists(f"{self.log_path}.1")
        assert os.path.exists(f"{self.log_path}.2")

        # There should not be a .3 file since backupCount is 2
        assert not os.path.exists(f"{self.log_path}.3")

        # Close handler
        handler.close()

    def test_with_existing_directory(self):
        """Test handler with already existing directory."""
        # Create the directory first
        log_dir = os.path.dirname(self.log_path)
        os.makedirs(log_dir, exist_ok=True)

        # Create the handler - should not raise an exception
        handler = SafeRotatingFileHandler(self.log_path)
        self.logger.addHandler(handler)

        # Test logging
        self.logger.info("Test existing directory")
        assert os.path.exists(self.log_path)

        # Close handler
        handler.close()

    @patch("os.makedirs")
    def test_makedirs_error(self, mock_makedirs):
        """Test handler when directory creation fails."""
        # Simulate mkdir failure
        mock_makedirs.side_effect = PermissionError("Permission denied")

        # This should not raise an exception, but try to create the file anyway
        with pytest.raises(PermissionError):
            handler = SafeRotatingFileHandler(self.log_path)

        # Verify makedirs was called
        mock_makedirs.assert_called_once()


class TestRequestContextHandler:
    """Tests for the RequestContextHandler class."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        # Clear any existing context
        RequestContextHandler.clear_context()

        self.handler = RequestContextHandler()
        self.logger = logging.getLogger("test_context")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)
        # Ensure no other handlers affect our tests
        self.logger.propagate = False

    def test_init(self):
        """Test initialization of RequestContextHandler."""
        handler = RequestContextHandler(level=logging.WARNING)
        assert handler.level == logging.WARNING

    def test_set_get_context(self):
        """Test setting and getting context values."""
        # Initially context should be empty
        context = RequestContextHandler.get_context()
        assert context == {}

        # Set some context values
        RequestContextHandler.set_context(request_id="123", user_id="user456")

        # Verify context was set
        context = RequestContextHandler.get_context()
        assert context == {"request_id": "123", "user_id": "user456"}

        # Add more context
        RequestContextHandler.set_context(client_ip="127.0.0.1")

        # Verify context was updated
        context = RequestContextHandler.get_context()
        assert context == {
            "request_id": "123",
            "user_id": "user456",
            "client_ip": "127.0.0.1",
        }

    def test_clear_context(self):
        """Test clearing context values."""
        # Set some context
        RequestContextHandler.set_context(request_id="123")
        assert RequestContextHandler.get_context() == {"request_id": "123"}

        # Clear the context
        RequestContextHandler.clear_context()

        # Context should be empty again
        assert RequestContextHandler.get_context() == {}

    def test_emit_with_context(self):
        """Test that context is added to log records."""
        # Set context values
        RequestContextHandler.set_context(
            request_id="req-123", user_id="user-456", session_id="sess-789"
        )

        # Create a mock formatter to inspect the record
        mock_formatter = MagicMock()
        mock_formatter.format = lambda record: str(record.__dict__)
        self.handler.setFormatter(mock_formatter)

        # Add a test handler to capture the formatted output
        test_handler = MagicMock()
        test_handler.level = (
            logging.NOTSET
        )  # Ensure the mock has a valid level attribute
        self.logger.addHandler(test_handler)

        # Log a message
        self.logger.info("Test message with context")

        # Get the record that was passed to the test handler
        args, _ = test_handler.handle.call_args
        record = args[0]

        # Verify context values were added to the record
        assert record.request_id == "req-123"
        assert record.user_id == "user-456"
        assert record.session_id == "sess-789"
        assert record.msg == "Test message with context"

    def test_thread_isolation(self):
        """Test that context is isolated between threads."""
        # Set context in the main thread
        RequestContextHandler.set_context(thread="main")

        # Use an event to synchronize threads
        event = threading.Event()
        thread_context = {}

        def thread_func():
            # This should be empty since context is thread-local
            thread_context["initial"] = RequestContextHandler.get_context().copy()

            # Set context in the thread
            RequestContextHandler.set_context(thread="worker")

            # Signal the main thread
            event.set()

            # Wait a moment to ensure the main thread has time to check its context
            time.sleep(0.1)

            # Save the thread's final context
            thread_context["final"] = RequestContextHandler.get_context().copy()

        # Start a thread that sets its own context
        thread = threading.Thread(target=thread_func)
        thread.start()

        # Wait for the thread to set its context
        event.wait()

        # Check that the main thread's context is unchanged
        main_context = RequestContextHandler.get_context()
        assert main_context == {"thread": "main"}

        # Wait for the thread to finish
        thread.join()

        # Verify thread isolation
        assert (
            thread_context["initial"] == {}
        ), "New thread should start with empty context"
        assert thread_context["final"] == {
            "thread": "worker"
        }, "Thread should have its own context"

        # Main thread context should still be intact
        assert RequestContextHandler.get_context() == {"thread": "main"}
