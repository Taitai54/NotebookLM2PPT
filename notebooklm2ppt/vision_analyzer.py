"""
Vision Analyzer module for NotebookLM PDF slides.

Uses Google Gemini Vision API to analyze slide layouts and extract
structured text/graphic information with high accuracy.
"""

import base64
import json
import os
from typing import Optional, Dict, List

# Try to import Gemini client
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Import config using try/except for flexibility
try:
    from .config import (
        GEMINI_MODEL,
        VISION_CONFIDENCE_THRESHOLD,
        VISION_API_TIMEOUT,
        MAX_RETRIES_ON_RATE_LIMIT,
        RETRY_DELAY_SECONDS,
    )
except ImportError:
    # Fallback defaults if config not available
    GEMINI_MODEL = "gemini-2.0-flash-exp"
    VISION_CONFIDENCE_THRESHOLD = 0.75
    VISION_API_TIMEOUT = 30
    MAX_RETRIES_ON_RATE_LIMIT = 3
    RETRY_DELAY_SECONDS = 60


class VisionAnalyzer:
    """
    Use Google Gemini Vision API to understand slide layout.
    
    This class handles all interactions with the Vision API,
    returning structured JSON with text elements and their positions.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Vision Analyzer.
        
        Args:
            api_key: Google Gemini API key. If None, will try GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = None
        self.model = GEMINI_MODEL
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Gemini: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if Vision API is available and configured."""
        return self.client is not None
    
    def _build_analysis_prompt(self, page_num: int = 0) -> str:
        """
        Construct detailed prompt for consistent vision results.
        """
        return f"""You are analyzing a NotebookLM-generated slide image (page {page_num}).

CRITICAL: Extract ALL text content with PRECISE bounding boxes.

For each piece of text you find:
1. Extract the EXACT text content (preserve all spacing and punctuation)
2. Provide the bounding box as [x, y, width, height] in pixels
3. Identify the text role: "title", "subtitle", "body", "caption", or "label"

IMPORTANT RULES:
- Keep words properly spaced (e.g., "The Strategic Gap" NOT "TheStrategic Gap")
- Preserve line breaks where they exist visually
- Each distinct text block should be a separate element
- Don't merge text that's in different visual areas

Also identify any graphics, icons, charts, or decorative elements.

Return ONLY valid JSON (no markdown, no explanation):
{{
    "text_elements": [
        {{
            "text": "exact text content with proper spacing",
            "bbox": [x, y, width, height],
            "role": "title|subtitle|body|caption|label",
            "font_size": "large|medium|small",
            "confidence": 0.0-1.0
        }}
    ],
    "graphics": [
        {{
            "type": "icon|diagram|chart|image|decoration",
            "bbox": [x, y, width, height],
            "description": "brief description",
            "confidence": 0.0-1.0
        }}
    ],
    "background_image": {{
        "bbox": [0, 0, width, height],
        "description": "background description",
        "confidence": 0.0-1.0
    }},
    "layout_type": "title_with_image|two_column|centered|full_bleed|text_only",
    "overall_confidence": 0.0-1.0,
    "extraction_quality": "high|medium|low"
}}"""
    
    def analyze_slide_layout(
        self,
        image_bytes: bytes,
        page_num: int = 0
    ) -> Optional[Dict]:
        """
        Call Gemini Vision API to analyze slide layout.
        
        Args:
            image_bytes: PNG image as bytes
            page_num: Page number for reference in prompt
        
        Returns:
            Structured dict with text_elements, graphics, etc.
            Returns None if API call fails.
        """
        if not self.client:
            return None
        
        # Encode image to base64
        image_b64 = base64.standard_b64encode(image_bytes).decode('utf-8')
        
        prompt = self._build_analysis_prompt(page_num)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_b64
                                }
                            }
                        ]
                    }
                ],
                config={
                    "temperature": 0.0,  # Deterministic output
                    "max_output_tokens": 8192,
                }
            )
            
            return self._parse_vision_response(response.text)
            
        except Exception as e:
            print(f"Warning: Gemini Vision API call failed: {e}")
            return None
    
    def _parse_vision_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse and validate Gemini JSON response.
        
        Handles common issues like markdown wrapping.
        """
        try:
            # Extract JSON from potential markdown wrapping
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            
            # Validate required fields
            if "text_elements" not in result:
                result["text_elements"] = []
            if "graphics" not in result:
                result["graphics"] = []
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse Vision API response: {e}")
            return None
    
    def generate_fallback_result(self) -> Dict:
        """
        Generate result when Vision API is unavailable.
        
        Returns a minimal structure that can be filled from PDF extraction.
        """
        return {
            "background_image": {
                "bbox": [0, 0, 1920, 1080],
                "confidence": 0.5
            },
            "text_elements": [],
            "graphics": [],
            "layout_type": "unknown",
            "overall_confidence": 0.5,
            "extraction_quality": "medium",
            "note": "Vision API unavailable, using PDF extraction"
        }
