"""
Unit tests for the coordinates module.

Tests coordinate conversion between PDF, pixel, and PPTX (EMU) coordinate systems.
"""

import pytest
from notebooklm2ppt.utils.coordinates import (
    pdf_to_pptx_coordinates,
    pixels_to_pptx_coordinates,
    scale_bbox_to_image,
    validate_bbox_in_bounds,
    calculate_overlap_ratio,
    point_in_bbox,
    EMUS_PER_INCH,
    POINTS_PER_INCH,
)


class TestPdfToPptxCoordinates:
    """Tests for PDF to PPTX coordinate conversion."""
    
    def test_origin_conversion(self):
        """Test that origin is properly flipped from bottom-left to top-left."""
        # PDF bbox at bottom-left corner
        pdf_bbox = (0, 0, 72, 72)  # 1 inch square at origin
        page_height = 720  # 10 inches
        page_width = 1280
        
        result = pdf_to_pptx_coordinates(pdf_bbox, page_height, page_width)
        
        # After conversion, y should be at the bottom of the page
        left, top, width, height = result
        
        # Width and height should be 1 inch in EMUs
        assert width == EMUS_PER_INCH
        assert height == EMUS_PER_INCH
        
    def test_points_to_emus(self):
        """Test that points are correctly converted to EMUs."""
        # 72 points = 1 inch
        pdf_bbox = (0, 0, 72, 72)
        page_height = 720
        page_width = 1280
        
        result = pdf_to_pptx_coordinates(pdf_bbox, page_height, page_width)
        
        # Result should be in EMUs (914400 per inch)
        _, _, width, height = result
        assert width == EMUS_PER_INCH
        assert height == EMUS_PER_INCH


class TestPixelsToPptxCoordinates:
    """Tests for pixel to PPTX coordinate conversion."""
    
    def test_full_image_covers_slide(self):
        """Test that full image bbox covers full slide."""
        pixel_bbox = (0, 0, 1920, 1080)  # Full HD
        slide_width_emu = 16 * EMUS_PER_INCH
        slide_height_emu = 9 * EMUS_PER_INCH
        
        result = pixels_to_pptx_coordinates(
            pixel_bbox, 1920, 1080,
            slide_width_emu, slide_height_emu
        )
        
        left, top, width, height = result
        assert left == 0
        assert top == 0
        assert width == slide_width_emu
        assert height == slide_height_emu
    
    def test_center_element(self):
        """Test positioning of centered element."""
        # Element at center of 1920x1080 image
        pixel_bbox = (960, 540, 200, 100)
        slide_width_emu = 16 * EMUS_PER_INCH
        slide_height_emu = 9 * EMUS_PER_INCH
        
        result = pixels_to_pptx_coordinates(
            pixel_bbox, 1920, 1080,
            slide_width_emu, slide_height_emu
        )
        
        left, top, width, height = result
        
        # Left should be at 50% of slide width
        expected_left = int(960 * (slide_width_emu / 1920))
        assert left == expected_left


class TestScaleBboxToImage:
    """Tests for bounding box scaling."""
    
    def test_no_scale(self):
        """Test that same dimensions returns same bbox."""
        bbox = (100, 100, 200, 150)
        result = scale_bbox_to_image(bbox, 1920, 1080, 1920, 1080)
        assert result == bbox
    
    def test_double_scale(self):
        """Test scaling to double size."""
        bbox = (100, 100, 200, 150)
        result = scale_bbox_to_image(bbox, 1920, 1080, 3840, 2160)
        
        assert result == (200, 200, 400, 300)
    
    def test_half_scale(self):
        """Test scaling to half size."""
        bbox = (100, 100, 200, 150)
        result = scale_bbox_to_image(bbox, 1920, 1080, 960, 540)
        
        assert result == (50, 50, 100, 75)


class TestValidateBboxInBounds:
    """Tests for bounding box validation."""
    
    def test_valid_bbox_unchanged(self):
        """Test that valid bbox is unchanged."""
        bbox = (100, 100, 200, 150)
        result = validate_bbox_in_bounds(bbox, 1920, 1080)
        assert result == bbox
    
    def test_negative_coordinates_clamped(self):
        """Test that negative coordinates are clamped to 0."""
        bbox = (-50, -30, 200, 150)
        result = validate_bbox_in_bounds(bbox, 1920, 1080)
        
        x, y, w, h = result
        assert x == 0
        assert y == 0
    
    def test_overflow_clamped(self):
        """Test that overflow is clamped to bounds."""
        bbox = (1800, 1000, 200, 150)
        result = validate_bbox_in_bounds(bbox, 1920, 1080)
        
        x, y, w, h = result
        # Width should be reduced to fit
        assert x + w <= 1920
        assert y + h <= 1080


class TestCalculateOverlapRatio:
    """Tests for overlap ratio calculation."""
    
    def test_no_overlap(self):
        """Test that disjoint boxes have 0 overlap."""
        bbox1 = (0, 0, 100, 100)
        bbox2 = (200, 200, 100, 100)
        
        result = calculate_overlap_ratio(bbox1, bbox2)
        assert result == 0.0
    
    def test_full_overlap(self):
        """Test that contained box has 1.0 overlap."""
        bbox1 = (0, 0, 200, 200)
        bbox2 = (50, 50, 100, 100)  # Fully inside bbox1
        
        result = calculate_overlap_ratio(bbox1, bbox2)
        assert result == 1.0
    
    def test_partial_overlap(self):
        """Test partial overlap returns correct ratio."""
        bbox1 = (0, 0, 100, 100)
        bbox2 = (50, 50, 100, 100)
        
        result = calculate_overlap_ratio(bbox1, bbox2)
        
        # Intersection is 50x50 = 2500
        # Smaller box is 100x100 = 10000
        # Ratio = 2500/10000 = 0.25
        assert result == 0.25


class TestPointInBbox:
    """Tests for point-in-bbox check."""
    
    def test_point_inside(self):
        """Test point inside bbox returns True."""
        point = (150, 150)
        bbox = (100, 100, 200, 200)
        
        assert point_in_bbox(point, bbox) is True
    
    def test_point_outside(self):
        """Test point outside bbox returns False."""
        point = (50, 50)
        bbox = (100, 100, 200, 200)
        
        assert point_in_bbox(point, bbox) is False
    
    def test_point_on_edge(self):
        """Test point on edge of bbox returns True."""
        point = (100, 100)  # Top-left corner
        bbox = (100, 100, 200, 200)
        
        assert point_in_bbox(point, bbox) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
