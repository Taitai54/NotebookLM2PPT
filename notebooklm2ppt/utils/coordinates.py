"""
Coordinate conversion utilities for PDF to PowerPoint conversion.

CRITICAL: PDF and PPTX use different coordinate systems!
- PDF: origin (0,0) at bottom-left, y increases upward
- PPTX: origin (0,0) at top-left, y increases downward

This module handles all coordinate transformations between these systems.
"""

from typing import Tuple

# EMUs per inch (English Metric Units - PowerPoint's internal unit)
EMUS_PER_INCH = 914400

# PDF points per inch
POINTS_PER_INCH = 72


def pdf_to_pptx_coordinates(
    pdf_bbox: Tuple[float, float, float, float],
    page_height: float,
    page_width: float
) -> Tuple[int, int, int, int]:
    """
    Convert PDF coordinates to PPTX coordinates.
    
    PDF: origin (0,0) at bottom-left, y increases upward
    PPTX: origin (0,0) at top-left, y increases downward
    
    Args:
        pdf_bbox: (x, y, width, height) in PDF points
        page_height: PDF page height in points
        page_width: PDF page width in points (unused but kept for consistency)
    
    Returns:
        PPTX-ready (left, top, width, height) in EMUs
    """
    x, y, w, h = pdf_bbox
    
    # Convert to top-left origin (flip y-axis)
    pptx_top = page_height - (y + h)
    pptx_left = x
    
    # Convert points to inches
    left_inches = pptx_left / POINTS_PER_INCH
    top_inches = pptx_top / POINTS_PER_INCH
    width_inches = w / POINTS_PER_INCH
    height_inches = h / POINTS_PER_INCH
    
    # Convert to EMUs
    left_emu = int(left_inches * EMUS_PER_INCH)
    top_emu = int(top_inches * EMUS_PER_INCH)
    width_emu = int(width_inches * EMUS_PER_INCH)
    height_emu = int(height_inches * EMUS_PER_INCH)
    
    return (left_emu, top_emu, width_emu, height_emu)


def pixels_to_pptx_coordinates(
    pixel_bbox: Tuple[int, int, int, int],
    image_width: int,
    image_height: int,
    slide_width_emu: int,
    slide_height_emu: int
) -> Tuple[int, int, int, int]:
    """
    Convert pixel coordinates from an image to PPTX EMU coordinates.
    
    This is useful when coordinates come from Vision API (pixel-based)
    rather than PDF extraction (point-based).
    
    Args:
        pixel_bbox: (x, y, width, height) in pixels
        image_width: Source image width in pixels
        image_height: Source image height in pixels
        slide_width_emu: Target slide width in EMUs
        slide_height_emu: Target slide height in EMUs
    
    Returns:
        PPTX-ready (left, top, width, height) in EMUs
    """
    x, y, w, h = pixel_bbox
    
    # Calculate scale factors
    scale_x = slide_width_emu / image_width
    scale_y = slide_height_emu / image_height
    
    # Convert to EMUs
    left_emu = int(x * scale_x)
    top_emu = int(y * scale_y)
    width_emu = int(w * scale_x)
    height_emu = int(h * scale_y)
    
    return (left_emu, top_emu, width_emu, height_emu)


def scale_bbox_to_image(
    bbox: Tuple[int, int, int, int],
    original_width: int,
    original_height: int,
    target_width: int,
    target_height: int
) -> Tuple[int, int, int, int]:
    """
    Scale a bounding box from one image size to another.
    
    Useful when Vision API analyzes at different DPI than export DPI.
    
    Args:
        bbox: (x, y, width, height) in original image pixels
        original_width: Width of original image
        original_height: Height of original image
        target_width: Width of target image
        target_height: Height of target image
    
    Returns:
        Scaled (x, y, width, height) in target image pixels
    """
    x, y, w, h = bbox
    
    scale_x = target_width / original_width
    scale_y = target_height / original_height
    
    return (
        int(x * scale_x),
        int(y * scale_y),
        int(w * scale_x),
        int(h * scale_y)
    )


def validate_bbox_in_bounds(
    bbox: Tuple[int, int, int, int],
    max_width: int,
    max_height: int
) -> Tuple[int, int, int, int]:
    """
    Ensure a bounding box is within valid bounds.
    
    Clamps coordinates to valid range and ensures width/height are positive.
    
    Args:
        bbox: (x, y, width, height)
        max_width: Maximum allowed width (image/slide width)
        max_height: Maximum allowed height (image/slide height)
    
    Returns:
        Validated (x, y, width, height) clamped to bounds
    """
    x, y, w, h = bbox
    
    # Ensure x, y are non-negative
    x = max(0, x)
    y = max(0, y)
    
    # Ensure box doesn't extend beyond bounds
    if x + w > max_width:
        w = max_width - x
    if y + h > max_height:
        h = max_height - y
    
    # Ensure width/height are positive
    w = max(1, w)
    h = max(1, h)
    
    return (x, y, w, h)


def calculate_overlap_ratio(
    bbox1: Tuple[int, int, int, int],
    bbox2: Tuple[int, int, int, int]
) -> float:
    """
    Calculate the overlap ratio between two bounding boxes.
    
    Returns the ratio of intersection area to the smaller box's area.
    Useful for determining if text is "inside" an image region.
    
    Args:
        bbox1: (x, y, width, height) of first box
        bbox2: (x, y, width, height) of second box
    
    Returns:
        Overlap ratio from 0.0 (no overlap) to 1.0 (fully contained)
    """
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    
    # Calculate intersection
    ix1 = max(x1, x2)
    iy1 = max(y1, y2)
    ix2 = min(x1 + w1, x2 + w2)
    iy2 = min(y1 + h1, y2 + h2)
    
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    
    intersection_area = (ix2 - ix1) * (iy2 - iy1)
    smaller_area = min(w1 * h1, w2 * h2)
    
    if smaller_area == 0:
        return 0.0
    
    return intersection_area / smaller_area


def point_in_bbox(
    point: Tuple[int, int],
    bbox: Tuple[int, int, int, int]
) -> bool:
    """
    Check if a point is inside a bounding box.
    
    Args:
        point: (x, y) coordinates
        bbox: (x, y, width, height) of the box
    
    Returns:
        True if point is inside bbox
    """
    px, py = point
    bx, by, bw, bh = bbox
    
    return bx <= px <= bx + bw and by <= py <= by + bh
