"""Tests for mama health project."""

import pytest


def test_imports():
    """Test that basic imports work."""
    from mama_health import __version__

    assert __version__ == "0.1.0"


def test_config_initialization():
    """Test that configuration can be initialized."""
    from mama_health.config import AppConfig

    # This test will only pass if env variables are properly set
    # For CI/testing, we might want to mock these
    try:
        config = AppConfig()
        assert config is not None
    except ValueError:
        # Expected if environment variables are not set
        pytest.skip("Environment variables not fully configured")
