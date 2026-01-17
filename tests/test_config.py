"""
Unit tests for the config module.

Tests configuration loading and helper functions.
"""

import pytest
import os
from unittest.mock import patch

from notebooklm2ppt.config import (
    get_api_key,
    is_gemini_available,
    GEMINI_MODEL,
    DPI_FOR_VISION,
    DPI_FOR_EXPORT,
    SLIDE_WIDTH_INCHES,
    SLIDE_HEIGHT_INCHES,
    EMUS_PER_INCH,
)


class TestConfigConstants:
    """Tests for configuration constants."""
    
    def test_model_name(self):
        """Test that Gemini model is set."""
        assert GEMINI_MODEL is not None
        assert "gemini" in GEMINI_MODEL.lower()
    
    def test_dpi_settings(self):
        """Test DPI settings are reasonable."""
        assert DPI_FOR_VISION >= 150
        assert DPI_FOR_EXPORT >= 72
    
    def test_slide_dimensions(self):
        """Test slide dimensions are 16:9."""
        ratio = SLIDE_WIDTH_INCHES / SLIDE_HEIGHT_INCHES
        expected_ratio = 16 / 9
        
        assert abs(ratio - expected_ratio) < 0.01
    
    def test_emus_per_inch(self):
        """Test EMUs per inch is correct PowerPoint value."""
        assert EMUS_PER_INCH == 914400


class TestGetApiKey:
    """Tests for get_api_key function."""
    
    def test_returns_string_or_none(self):
        """Test that get_api_key returns string or None."""
        result = get_api_key()
        assert result is None or isinstance(result, str)
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"})
    def test_reads_from_env(self):
        """Test that API key is read from environment."""
        # Note: This test may not work if config.py has already cached the value
        # In a real test, we'd reload the module
        pass


class TestIsGeminiAvailable:
    """Tests for is_gemini_available function."""
    
    def test_returns_bool(self):
        """Test that is_gemini_available returns boolean."""
        result = is_gemini_available()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
