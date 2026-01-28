"""NotebookLM2PPT - Automation tool for converting PDF documents to PowerPoint presentations"""

__version__ = "0.4.0"
__author__ = "Elliott Zheng"

# Core classes
from .ocr_converter import SlideReconstructor
from .ppt_generator import PPTCreator, PowerPointGenerator
from .config import get_api_key, is_gemini_available

# Expose main functionality
__all__ = [
    "SlideReconstructor",
    "PPTCreator",
    "PowerPointGenerator",
    "VisionAnalyzer",
    "get_api_key",
    "is_gemini_available",
]
