"""
Watermark removal utilities for NotebookLM slides.

Provides dynamic watermark detection and removal using inpainting.
Supports both hardcoded NotebookLM watermark positions and custom regions.
"""

import cv2
import numpy as np
from PIL import Image
from skimage.restoration import inpaint
from typing import Tuple, Optional, Dict


# Default NotebookLM watermark region (relative coordinates for 16:9 slides)
# Based on analysis: watermark at bottom-right, approximately:
# - Position: 91.4% from left, 95.6% from top
# - Size: 8.4% of width, 4.1% of height
DEFAULT_WATERMARK_REGION = {
    "relative_left": 0.914,
    "relative_top": 0.956,
    "relative_width": 0.084,
    "relative_height": 0.041,
}


def get_watermark_region(
    image_width: int,
    image_height: int,
    region_config: Optional[Dict[str, float]] = None
) -> Tuple[int, int, int, int]:
    """
    Calculate the watermark region in absolute pixel coordinates.
    
    Args:
        image_width: Width of the image in pixels
        image_height: Height of the image in pixels
        region_config: Optional dict with relative_left, relative_top, 
                      relative_width, relative_height. Defaults to NotebookLM standard.
    
    Returns:
        Tuple of (top_row, bottom_row, left_col, right_col) in pixels
    """
    config = region_config or DEFAULT_WATERMARK_REGION
    
    left = int(config["relative_left"] * image_width)
    top = int(config["relative_top"] * image_height)
    width = int(config["relative_width"] * image_width)
    height = int(config["relative_height"] * image_height)
    
    # Ensure bounds are valid
    right = min(left + width, image_width)
    bottom = min(top + height, image_height)
    left = max(0, left)
    top = max(0, top)
    
    return (top, bottom, left, right)


def remove_watermark(
    image_path: str,
    output_path: str,
    region_config: Optional[Dict[str, float]] = None
) -> bool:
    """
    Remove watermark from an image using biharmonic inpainting.
    
    This function automatically calculates the watermark region based on
    image dimensions and uses biharmonic inpainting to fill the area.
    
    Args:
        image_path: Path to the input image
        output_path: Path to save the cleaned image
        region_config: Optional custom watermark region config.
                      If None, uses NotebookLM default position.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load image
        image = Image.open(image_path)
        image_array = np.array(image)
        
        height, width = image_array.shape[:2]
        
        # Get watermark region
        r1, r2, c1, c2 = get_watermark_region(width, height, region_config)
        
        # Create mask
        mask = np.zeros(image_array.shape[:-1], dtype=bool)
        mask[r1:r2, c1:c2] = True
        
        # Apply biharmonic inpainting
        result = inpaint.inpaint_biharmonic(image_array, mask, channel_axis=-1)
        
        # Save result
        Image.fromarray((result * 255).astype("uint8")).save(output_path)
        
        return True
        
    except Exception as e:
        print(f"Warning: Watermark removal failed: {e}")
        return False


def remove_watermark_cv2(
    image: np.ndarray,
    region_config: Optional[Dict[str, float]] = None
) -> np.ndarray:
    """
    Remove watermark from a cv2 image array using OpenCV inpainting.
    
    This is faster than biharmonic inpainting and works directly with
    cv2/numpy arrays without file I/O.
    
    Args:
        image: Input image as numpy array (BGR format from cv2)
        region_config: Optional custom watermark region config
    
    Returns:
        Cleaned image array
    """
    height, width = image.shape[:2]
    
    # Get watermark region
    r1, r2, c1, c2 = get_watermark_region(width, height, region_config)
    
    # Create mask (white = area to inpaint)
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[r1:r2, c1:c2] = 255
    
    # Apply Navier-Stokes inpainting (fast, good quality)
    result = cv2.inpaint(image, mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
    
    return result


def detect_watermark_text(
    image: np.ndarray,
    patterns: list = None
) -> Optional[Tuple[int, int, int, int]]:
    """
    Attempt to detect NotebookLM watermark by text pattern matching.
    
    Uses template matching or OCR to find watermark text location.
    This is a fallback for non-standard watermark positions.
    
    Args:
        image: Input image as numpy array
        patterns: List of text patterns to search for 
                 (default: ["NotebookLM", "Notebook LM"])
    
    Returns:
        Bounding box (x, y, w, h) of detected watermark, or None if not found
    """
    if patterns is None:
        patterns = ["NotebookLM", "Notebook LM", "Made with NotebookLM"]
    
    # For now, return None - this would require OCR integration
    # Future enhancement: use RapidOCR or pytesseract to find watermark text
    return None


# Legacy function for backward compatibility
def inpaint_image(image_path: str, output_path: str) -> None:
    """
    Legacy wrapper for watermark removal.
    
    Kept for backward compatibility with existing code.
    """
    remove_watermark(image_path, output_path)