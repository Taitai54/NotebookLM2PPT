"""Utility functions module"""

from .image_viewer import show_image_fullscreen
from .image_inpainter import inpaint_image, remove_watermark, remove_watermark_cv2
from .screenshot_automation import take_fullscreen_snip, mouse, screen_height, screen_width
from .coordinates import (
    pdf_to_pptx_coordinates,
    pixels_to_pptx_coordinates,
    scale_bbox_to_image,
    validate_bbox_in_bounds,
    calculate_overlap_ratio,
    point_in_bbox,
)

__all__ = [
    'show_image_fullscreen',
    'inpaint_image',
    'remove_watermark',
    'remove_watermark_cv2',
    'take_fullscreen_snip',
    'mouse',
    'screen_height',
    'screen_width',
    'pdf_to_pptx_coordinates',
    'pixels_to_pptx_coordinates',
    'scale_bbox_to_image',
    'validate_bbox_in_bounds',
    'calculate_overlap_ratio',
    'point_in_bbox',
]

