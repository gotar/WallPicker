"""Tests for Config domain model."""

from pathlib import Path

import pytest

from domain.config import Config, ConfigError


def test_config_default_values():
    """Test Config with default values."""
    config = Config()
    assert config.local_wallpapers_dir is None
    assert config.wallhaven_api_key is None


def test_config_with_values():
    """Test Config with values."""
    config = Config(
        local_wallpapers_dir=Path("/test/path"), wallhaven_api_key="test-key"
    )
    assert config.local_wallpapers_dir == Path("/test/path")
    assert config.wallhaven_api_key == "test-key"


def test_config_validation_valid():
    """Test Config validation accepts any Path value (type check only).

    Existence checks moved to ConfigService (L16): a vanished wallpapers dir
    must never block saving the config.
    """
    config = Config(local_wallpapers_dir=Path("/nonexistent/but/type-valid"))
    config.validate()  # Should not raise


def test_config_validation_non_path_raises():
    """Test Config validation still rejects non-Path values."""
    config = Config(local_wallpapers_dir="/a/string/not/a/path")
    with pytest.raises(ConfigError, match="must be a Path"):
        config.validate()


def test_config_validation_none_ok():
    """Test Config validation passes when no directory is configured."""
    Config().validate()  # Should not raise


def test_config_pictures_dir():
    """Test pictures_dir property."""
    custom_dir = Path("/custom/path")
    config = Config(local_wallpapers_dir=custom_dir)
    assert config.pictures_dir == custom_dir

    config2 = Config()
    assert config2.pictures_dir == Path.home() / "Pictures"


def test_config_serialization():
    """Test Config to_dict and from_dict."""
    config = Config(
        local_wallpapers_dir=Path("/test/path"), wallhaven_api_key="test-key"
    )

    data = config.to_dict()
    assert data["local_wallpapers_dir"] == "/test/path"
    assert data["wallhaven_api_key"] == "test-key"


def test_config_from_dict():
    """Test Config.from_dict."""
    data = {
        "local_wallpapers_dir": "/test/path",
        "wallhaven_api_key": "test-key",
    }

    config = Config.from_dict(data)
    assert config.local_wallpapers_dir == Path("/test/path")
    assert config.wallhaven_api_key == "test-key"


def test_config_from_dict_with_none():
    """Test Config.from_dict with None values."""
    data = {
        "local_wallpapers_dir": None,
        "wallhaven_api_key": None,
    }

    config = Config.from_dict(data)
    assert config.local_wallpapers_dir is None
    assert config.wallhaven_api_key is None
