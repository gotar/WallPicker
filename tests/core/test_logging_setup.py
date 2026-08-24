"""Tests for core.logging_setup."""

import logging
from unittest.mock import patch

from core.logging_setup import setup_logging


class TestSetupLogging:
    def test_creates_log_dir_and_file(self, tmp_path):
        with patch("core.logging_setup.LOG_DIR", tmp_path / "logs"):
            with patch("core.logging_setup.LOG_FILE",
                       tmp_path / "logs" / "wallpicker.log"):
                logging.getLogger().handlers.clear()
                import core.logging_setup as lset
                lset._configured = False
                try:
                    log_file = setup_logging()
                    assert log_file.exists()
                    assert (tmp_path / "logs").is_dir()
                finally:
                    for h in logging.getLogger().handlers[:]:
                        logging.getLogger().removeHandler(h)
                        h.close()

    def test_warning_reaches_file(self, tmp_path):
        log_path = tmp_path / "wallpicker.log"
        with patch("core.logging_setup.LOG_DIR", tmp_path):
            with patch("core.logging_setup.LOG_FILE", log_path):
                logging.getLogger().handlers.clear()
                import core.logging_setup as lset
                lset._configured = False
                try:
                    setup_logging()
                    logging.getLogger("test").warning("hello log")
                    for h in logging.getLogger().handlers[:]:
                        h.flush()
                    content = log_path.read_text()
                    assert "hello log" in content
                finally:
                    for h in logging.getLogger().handlers[:]:
                        logging.getLogger().removeHandler(h)
                        h.close()

    def test_info_reaches_file(self, tmp_path):
        log_path = tmp_path / "wallpicker.log"
        with patch("core.logging_setup.LOG_DIR", tmp_path):
            with patch("core.logging_setup.LOG_FILE", log_path):
                logging.getLogger().handlers.clear()
                import core.logging_setup as lset
                lset._configured = False
                try:
                    setup_logging()
                    logging.getLogger("test").info("info message")
                    for h in logging.getLogger().handlers[:]:
                        h.flush()
                    assert "info message" in log_path.read_text()
                finally:
                    for h in logging.getLogger().handlers[:]:
                        logging.getLogger().removeHandler(h)
                        h.close()

    def test_idempotent(self, tmp_path):
        """Calling twice must not duplicate handlers."""
        with patch("core.logging_setup.LOG_DIR", tmp_path):
            with patch("core.logging_setup.LOG_FILE", tmp_path / "w.log"):
                logging.getLogger().handlers.clear()
                import core.logging_setup as lset
                lset._configured = False
                try:
                    setup_logging()
                    count = len(logging.getLogger().handlers)
                    setup_logging()
                    assert len(logging.getLogger().handlers) == count
                finally:
                    for h in logging.getLogger().handlers[:]:
                        logging.getLogger().removeHandler(h)
                        h.close()
