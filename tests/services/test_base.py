"""Tests for BaseService."""

from services.base import BaseService


class TestBaseServiceInit:
    """Test BaseService initialization."""

    def test_init_creates_logger(self):
        """Test initialization creates logger."""
        service = BaseService()

        assert service.logger is not None
        assert service.logger.name == "BaseService"


class TestCustomService:
    """Test custom service inheriting from BaseService."""

    def test_custom_service_has_correct_logger_name(self):
        """Test custom service gets correct logger name."""

        class CustomService(BaseService):
            pass

        service = CustomService()

        assert service.logger.name == "CustomService"


class TestLogMethods:
    """Test logging methods."""

    def test_log_debug(self, caplog):
        """Test debug logging."""
        service = BaseService()

        with caplog.at_level("DEBUG"):
            service.log_debug("Test debug message")

        assert "Test debug message" in caplog.text

    def test_log_info(self, caplog):
        """Test info logging."""
        service = BaseService()

        with caplog.at_level("INFO"):
            service.log_info("Test info message")

        assert "Test info message" in caplog.text

    def test_log_warning(self, caplog):
        """Test warning logging."""
        service = BaseService()

        with caplog.at_level("WARNING"):
            service.log_warning("Test warning message")

        assert "Test warning message" in caplog.text

    def test_log_error(self, caplog):
        """Test error logging."""
        service = BaseService()

        with caplog.at_level("ERROR"):
            service.log_error("Test error message")

        assert "Test error message" in caplog.text

    def test_log_error_with_exc_info(self, caplog):
        """Test error logging with exception info."""
        service = BaseService()

        try:
            raise ValueError("Test exception")
        except Exception:
            with caplog.at_level("ERROR"):
                service.log_error("Test error with exception", exc_info=True)

        assert "Test error with exception" in caplog.text
        assert "Test exception" in caplog.text

    def test_log_critical(self, caplog):
        """Test critical logging."""
        service = BaseService()

        with caplog.at_level("CRITICAL"):
            service.log_critical("Test critical message")

        assert "Test critical message" in caplog.text

    def test_log_critical_with_exc_info(self, caplog):
        """Test critical logging with exception info."""
        service = BaseService()

        try:
            raise RuntimeError("Test critical exception")
        except Exception:
            with caplog.at_level("CRITICAL"):
                service.log_critical("Test critical with exception", exc_info=True)

        assert "Test critical with exception" in caplog.text
        assert "Test critical exception" in caplog.text


class TestLoggerProperty:
    """Test logger property."""

    def test_logger_property_returns_logger(self):
        """Test logger property returns logger instance."""
        service = BaseService()

        logger = service.logger

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")
