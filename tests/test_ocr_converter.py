"""
Unit tests for the OCR converter module.

Tests SlideReconstructor class including Vision API fallback logic.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from notebooklm2ppt.ocr_converter import SlideReconstructor


class TestSlideReconstructor:
    """Tests for SlideReconstructor class."""
    
    def test_initialization(self):
        """Test that SlideReconstructor initializes without error."""
        # Should not raise even without API key
        reconstructor = SlideReconstructor(api_key=None)
        assert reconstructor is not None
    
    def test_has_vision_analyzer(self):
        """Test that vision_analyzer is initialized."""
        reconstructor = SlideReconstructor()
        assert hasattr(reconstructor, 'vision_analyzer')


class TestTextSpacingFix:
    """Tests for fix_text_spacing method."""
    
    @pytest.fixture
    def reconstructor(self):
        return SlideReconstructor(api_key=None)
    
    def test_camelcase_splitting(self, reconstructor):
        """Test that CamelCase is split into words."""
        text = "TheStrategicGap"
        result = reconstructor.fix_text_spacing(text)
        assert result == "The Strategic Gap"
    
    def test_punctuation_spacing(self, reconstructor):
        """Test that punctuation gets proper spacing."""
        text = "Hello,world"
        result = reconstructor.fix_text_spacing(text)
        assert result == "Hello, world"
    
    def test_period_spacing(self, reconstructor):
        """Test that periods before capitals get spacing."""
        text = "End.Start"
        result = reconstructor.fix_text_spacing(text)
        assert result == "End. Start"
    
    def test_double_space_cleanup(self, reconstructor):
        """Test that double spaces are cleaned."""
        text = "Hello  world"
        result = reconstructor.fix_text_spacing(text)
        assert result == "Hello world"
    
    def test_empty_string(self, reconstructor):
        """Test handling of empty string."""
        result = reconstructor.fix_text_spacing("")
        assert result == ""
    
    def test_none_input(self, reconstructor):
        """Test handling of None input."""
        result = reconstructor.fix_text_spacing(None)
        assert result is None


class TestWatermarkDetection:
    """Tests for watermark detection."""
    
    @pytest.fixture
    def reconstructor(self):
        return SlideReconstructor(api_key=None)
    
    def test_detects_notebooklm(self, reconstructor):
        """Test that NotebookLM watermark is detected."""
        assert reconstructor._is_watermark("NotebookLM") is True
        assert reconstructor._is_watermark("Made with NotebookLM") is True
    
    def test_case_insensitive(self, reconstructor):
        """Test that detection is case insensitive."""
        assert reconstructor._is_watermark("notebooklm") is True
        assert reconstructor._is_watermark("NOTEBOOKLM") is True
    
    def test_normal_text_not_watermark(self, reconstructor):
        """Test that normal text is not detected as watermark."""
        assert reconstructor._is_watermark("Hello World") is False
        assert reconstructor._is_watermark("Strategic Planning") is False


class TestProcessVisionResult:
    """Tests for _process_vision_result method."""
    
    @pytest.fixture
    def reconstructor(self):
        return SlideReconstructor(api_key=None)
    
    def test_empty_result(self, reconstructor):
        """Test handling of empty result."""
        result = {"text_elements": []}
        blocks = reconstructor._process_vision_result(result, 1920, 1080)
        assert blocks == []
    
    def test_filters_watermarks(self, reconstructor):
        """Test that watermarks are filtered out."""
        result = {
            "text_elements": [
                {"text": "Hello World", "bbox": [0, 0, 100, 20]},
                {"text": "NotebookLM", "bbox": [100, 100, 100, 20]},
            ]
        }
        blocks = reconstructor._process_vision_result(result, 1920, 1080)
        
        assert len(blocks) == 1
        assert blocks[0]["text"] == "Hello World"
    
    def test_extracts_all_fields(self, reconstructor):
        """Test that all fields are properly extracted."""
        result = {
            "text_elements": [
                {
                    "text": "Title",
                    "bbox": [100, 50, 200, 40],
                    "role": "title",
                    "confidence": 0.95
                }
            ]
        }
        blocks = reconstructor._process_vision_result(result, 1920, 1080)
        
        assert len(blocks) == 1
        block = blocks[0]
        assert block["text"] == "Title"
        assert block["box"] == [100, 50, 200, 40]
        assert block["role"] == "title"
        assert block["score"] == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
