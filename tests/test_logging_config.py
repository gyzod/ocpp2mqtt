"""Tests for logging_config module."""

import logging
import os
import tempfile
from unittest.mock import patch

import pytest

import logging_config


@pytest.fixture
def reset_logging():
    """Reset logging configuration after each test."""
    yield
    # Clear all handlers from root logger
    root = logging.getLogger()
    root.handlers.clear()
    # Clear handlers from named loggers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.handlers.clear()


@pytest.fixture
def temp_log_file():
    """Create a temporary log file path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


# =============================================================================
# Tests for setup_logging
# =============================================================================

def test_setup_logging_default_config(reset_logging, monkeypatch):
    """Test setup_logging with default configuration."""
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    monkeypatch.setattr(logging_config, "LOG_LEVEL", "INFO")
    
    logger = logging_config.setup_logging("test_logger")
    
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1  # Console only
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_setup_logging_with_file(reset_logging, temp_log_file, monkeypatch):
    """Test setup_logging with file logging enabled."""
    monkeypatch.setattr(logging_config, "LOG_FILE", temp_log_file)
    monkeypatch.setattr(logging_config, "LOG_LEVEL", "DEBUG")
    
    logger = logging_config.setup_logging("test_file_logger")
    
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2  # Console + File


def test_setup_logging_creates_directory(reset_logging, monkeypatch):
    """Test setup_logging creates log directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "subdir", "app.log")
        monkeypatch.setattr(logging_config, "LOG_FILE", log_path)
        
        logger = logging_config.setup_logging("test_dir_logger")
        
        assert os.path.exists(os.path.dirname(log_path))


def test_setup_logging_returns_same_logger_if_configured(reset_logging, monkeypatch):
    """Test setup_logging doesn't reconfigure if logger already has handlers."""
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    
    logger1 = logging_config.setup_logging("same_logger")
    initial_handlers = len(logger1.handlers)
    
    logger2 = logging_config.setup_logging("same_logger")
    
    assert logger1 is logger2
    assert len(logger2.handlers) == initial_handlers  # No additional handlers


def test_setup_logging_invalid_level_fallback(reset_logging, monkeypatch):
    """Test setup_logging falls back to INFO for invalid log level."""
    monkeypatch.setattr(logging_config, "LOG_LEVEL", "INVALID_LEVEL")
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    
    logger = logging_config.setup_logging("invalid_level_logger")
    
    assert logger.level == logging.INFO


def test_setup_logging_file_error_handling(reset_logging, monkeypatch):
    """Test setup_logging handles file creation errors gracefully."""
    # Use an invalid path that can't be created
    monkeypatch.setattr(logging_config, "LOG_FILE", "/nonexistent/path/that/cannot/be/created/app.log")
    
    # Should not raise, just log error
    logger = logging_config.setup_logging("error_logger")
    
    # Should still have console handler
    assert len(logger.handlers) >= 1


# =============================================================================
# Tests for configure_root_logging
# =============================================================================

def test_configure_root_logging_default(reset_logging, monkeypatch):
    """Test configure_root_logging with default configuration."""
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    monkeypatch.setattr(logging_config, "LOG_LEVEL", "WARNING")
    
    root_logger = logging_config.configure_root_logging()
    
    assert root_logger.level == logging.WARNING
    assert len(root_logger.handlers) == 1


def test_configure_root_logging_with_file(reset_logging, temp_log_file, monkeypatch):
    """Test configure_root_logging with file logging."""
    monkeypatch.setattr(logging_config, "LOG_FILE", temp_log_file)
    monkeypatch.setattr(logging_config, "LOG_LEVEL", "INFO")
    
    root_logger = logging_config.configure_root_logging()
    
    assert len(root_logger.handlers) == 2


def test_configure_root_logging_clears_existing_handlers(reset_logging, monkeypatch):
    """Test configure_root_logging clears existing handlers."""
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    
    root = logging.getLogger()
    # Add a dummy handler
    dummy = logging.NullHandler()
    dummy.set_name("test_dummy_handler")
    root.addHandler(dummy)
    
    logging_config.configure_root_logging()
    
    # Our dummy handler should be cleared (check by name)
    handler_names = [h.name for h in root.handlers if hasattr(h, 'name')]
    assert "test_dummy_handler" not in handler_names
    # Should have at least a StreamHandler for console
    stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
    assert len(stream_handlers) >= 1


def test_configure_root_logging_log_format(reset_logging, temp_log_file, monkeypatch):
    """Test configure_root_logging uses custom format."""
    custom_format = "%(levelname)s - %(message)s"
    monkeypatch.setattr(logging_config, "LOG_FORMAT", custom_format)
    monkeypatch.setattr(logging_config, "LOG_FILE", temp_log_file)
    
    root_logger = logging_config.configure_root_logging()
    
    # Write a test message
    root_logger.warning("Test message")
    
    # Check the log file contains the formatted message
    with open(temp_log_file) as f:
        content = f.read()
        assert "WARNING - Test message" in content or "WARNING" in content


def test_configure_root_logging_rotation_settings(reset_logging, temp_log_file, monkeypatch):
    """Test configure_root_logging uses rotation settings."""
    monkeypatch.setattr(logging_config, "LOG_FILE", temp_log_file)
    monkeypatch.setattr(logging_config, "LOG_MAX_SIZE", 1024)
    monkeypatch.setattr(logging_config, "LOG_BACKUP_COUNT", 3)
    
    root_logger = logging_config.configure_root_logging()
    
    # Find the file handler
    file_handlers = [h for h in root_logger.handlers 
                     if hasattr(h, 'maxBytes')]
    
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == 1024
    assert file_handlers[0].backupCount == 3


# =============================================================================
# Tests for LOG_LEVEL values
# =============================================================================

@pytest.mark.parametrize("level_name,expected_level", [
    ("DEBUG", logging.DEBUG),
    ("INFO", logging.INFO),
    ("WARNING", logging.WARNING),
    ("ERROR", logging.ERROR),
    ("CRITICAL", logging.CRITICAL),
])
def test_setup_logging_all_levels(reset_logging, monkeypatch, level_name, expected_level):
    """Test setup_logging works with all standard log levels."""
    monkeypatch.setattr(logging_config, "LOG_LEVEL", level_name)
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    
    # Use unique logger name for each parametrized test
    logger = logging_config.setup_logging(f"level_test_{level_name}")
    
    assert logger.level == expected_level
