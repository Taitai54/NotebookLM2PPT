"""
Configuration module for NotebookLM2PPT.

Centralizes all configuration parameters, API keys, and processing constants
following the spec's recommended architecture.
"""

import os
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# API Configuration
# =============================================================================

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Latest vision model

# Vision API confidence threshold
VISION_CONFIDENCE_THRESHOLD = 0.75


# =============================================================================
# Processing Parameters
# =============================================================================

# DPI settings
DPI_FOR_VISION = 300      # High-res for Vision API analysis
DPI_FOR_EXPORT = 150      # Background image quality (default)

# Image quality
JPEG_QUALITY = 95
PNG_COMPRESSION = 6

# Slide dimensions (16:9 format)
SLIDE_WIDTH_INCHES = 16
SLIDE_HEIGHT_INCHES = 9

# EMUs per inch (PowerPoint uses English Metric Units)
EMUS_PER_INCH = 914400

# PDF points per inch
POINTS_PER_INCH = 72


# =============================================================================
# Watermark Detection
# =============================================================================

# Known NotebookLM watermark patterns
WATERMARK_PATTERNS = [
    "NotebookLM",
    "Notebook LM", 
    "Made with NotebookLM",
]

# Default watermark region (relative to bottom-right, for 16:9 slides)
# These are relative coordinates that will be scaled to actual image size
WATERMARK_REGION_DEFAULTS = {
    "relative_left": 0.914,   # ~91.4% from left
    "relative_top": 0.956,    # ~95.6% from top
    "relative_width": 0.084,  # ~8.4% of width
    "relative_height": 0.041, # ~4.1% of height
}


# =============================================================================
# Text Extraction Settings
# =============================================================================

# Minimum text block dimensions (pixels)
MIN_TEXT_WIDTH = 10
MIN_TEXT_HEIGHT = 5

# Minimum confidence for text extraction
MIN_TEXT_CONFIDENCE = 0.5


# =============================================================================
# Image Object Detection
# =============================================================================

# Minimum dimensions for image objects
MIN_IMAGE_OBJ_WIDTH = 30
MIN_IMAGE_OBJ_HEIGHT = 30
MIN_IMAGE_OBJ_AREA = 1000

# Max text blocks inside a region to consider it an "image object"
MAX_TEXT_IN_IMAGE_OBJECT = 3

# Padding for image object extraction
IMAGE_OBJECT_PADDING = 10


# =============================================================================
# Performance Settings
# =============================================================================

# Processing timeouts
VISION_API_TIMEOUT = 30       # seconds
MAX_RETRIES_ON_RATE_LIMIT = 3
RETRY_DELAY_SECONDS = 60

# Async settings
MAX_CONCURRENT_PAGES = 5


# =============================================================================
# Output Settings
# =============================================================================

# Default output directory
DEFAULT_OUTPUT_DIR = Path("workspace")

# File naming patterns
PNG_FILENAME_PATTERN = "page_{:04d}.png"
DEBUG_FILENAME_PATTERN = "{stem}_debug.jpg"
CLEAN_BG_FILENAME_PATTERN = "{stem}_clean.jpg"


def get_api_key() -> str:
    """Get the Gemini API key from config or environment."""
    return GEMINI_API_KEY


def is_gemini_available() -> bool:
    """Check if Gemini API is configured and available."""
    return bool(GEMINI_API_KEY)
