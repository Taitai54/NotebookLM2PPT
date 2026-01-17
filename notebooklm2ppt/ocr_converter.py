"""
Vision-based Slide Reconstructor for NotebookLM PDFs.

Uses Google Gemini Vision API for intelligent text extraction,
falling back to RapidOCR if API is unavailable.

This is the main orchestrator that combines VisionAnalyzer with
layer separation logic to produce editable PowerPoint-ready data.
"""

import cv2
import numpy as np
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import the new VisionAnalyzer module
from .vision_analyzer import VisionAnalyzer, GEMINI_AVAILABLE

# Import configuration
from .config import (
    MIN_IMAGE_OBJ_WIDTH,
    MIN_IMAGE_OBJ_HEIGHT,
    MIN_IMAGE_OBJ_AREA,
    MAX_TEXT_IN_IMAGE_OBJECT,
    IMAGE_OBJECT_PADDING,
    WATERMARK_PATTERNS,
)

# Import coordinate utilities
from .utils.coordinates import point_in_bbox, validate_bbox_in_bounds

# Fallback to RapidOCR
try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False


class SlideReconstructor:
    """
    Reconstruct slides by extracting text and separating images.
    
    Uses Gemini Vision API for accurate text extraction when available,
    with RapidOCR as fallback. Separates text layers from background
    to create editable PowerPoint slides.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the reconstructor.
        
        Args:
            api_key: Google Gemini API key. If None, will try GEMINI_API_KEY env var.
        """
        # Initialize Vision Analyzer (handles Gemini API)
        self.vision_analyzer = VisionAnalyzer(api_key)
        
        # Initialize RapidOCR as fallback
        self.ocr = None
        if RAPIDOCR_AVAILABLE:
            self.ocr = RapidOCR()
        
        # Status message
        if self.vision_analyzer.is_available:
            print("✓ Gemini Vision API initialized")
        elif self.ocr:
            print("✓ Using RapidOCR fallback (Gemini API not configured)")
        else:
            print("⚠ Warning: Neither Gemini API nor RapidOCR available")

    def fix_text_spacing(self, text: str) -> str:
        """
        Post-process OCR text to fix common spacing issues.
        Only used for RapidOCR fallback.
        """
        if not text:
            return text
        
        # Add space before capitals in middle of words (CamelCase)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Add space after punctuation if followed by a letter
        text = re.sub(r'([,;:])([A-Za-z])', r'\1 \2', text)
        
        # Add space after period if followed by uppercase
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        # Add space before/after parentheses if adjacent to letters
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        text = re.sub(r'\)([A-Za-z])', r') \1', text)
        
        # Fix common OCR merge patterns
        text = re.sub(r'\bif([a-z])', r'if \1', text, flags=re.IGNORECASE)
        text = re.sub(r'\bwe([a-z])', r'we \1', text, flags=re.IGNORECASE)
        
        # Clean up double spaces
        text = re.sub(r'  +', ' ', text)
        
        return text.strip()

    def _is_watermark(self, text: str) -> bool:
        """Check if text is a watermark based on known patterns."""
        for pattern in WATERMARK_PATTERNS:
            if pattern.lower() in text.lower():
                return True
        return False

    def _fallback_ocr(self, img: np.ndarray) -> List[Dict]:
        """
        Fallback to RapidOCR if Gemini is unavailable.
        """
        if not self.ocr:
            return []
            
        ocr_result, _ = self.ocr(img)
        
        blocks = []
        if ocr_result:
            for item in ocr_result:
                box_points, text, score = item
                
                # Apply text spacing fixes
                text = self.fix_text_spacing(text)
                
                # Skip watermarks
                if self._is_watermark(text):
                    continue
                    
                pts = np.array(box_points, dtype=np.int32)
                x, y, w, h = cv2.boundingRect(pts)
                blocks.append({
                    "text": text,
                    "box": [x, y, w, h],
                    "font_size": h,
                    "role": "body",
                    "score": score
                })
        
        return blocks

    def _process_vision_result(
        self,
        result: Dict,
        full_w: int,
        full_h: int
    ) -> List[Dict]:
        """
        Process Vision API result into standardized text blocks.
        """
        text_blocks = []
        
        for elem in result.get('text_elements', []):
            text = elem.get('text', '')
            bbox = elem.get('bbox', [0, 0, 100, 20])
            
            # Skip watermarks
            if self._is_watermark(text):
                continue
            
            # Validate bounding box
            if len(bbox) >= 4:
                bbox = validate_bbox_in_bounds(
                    (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])),
                    full_w, full_h
                )
            else:
                bbox = (0, 0, 100, 20)
            
            # Estimate font size from height
            font_size = bbox[3] if len(bbox) >= 4 else 20
            
            text_blocks.append({
                "text": text,
                "box": list(bbox),
                "font_size": font_size,
                "role": elem.get('role', 'body'),
                "score": elem.get('confidence', 1.0)
            })
        
        return text_blocks

    def _detect_image_objects(
        self,
        img: np.ndarray,
        mask_text: np.ndarray,
        text_blocks: List[Dict]
    ) -> List[Dict]:
        """
        Detect image objects (diagrams, icons) separate from text.
        """
        full_h, full_w = img.shape[:2]
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Remove text regions from detection
        binary_no_text = cv2.bitwise_and(binary, binary, mask=cv2.bitwise_not(mask_text))
        
        # Dilate to connect loose parts
        kernel_img = np.ones((5,5), np.uint8)
        dilated_img_map = cv2.dilate(binary_no_text, kernel_img, iterations=3)
        
        contours, _ = cv2.findContours(dilated_img_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        image_objects = []
        
        for idx, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # Size filter using config values
            if w < MIN_IMAGE_OBJ_WIDTH or h < MIN_IMAGE_OBJ_HEIGHT or area < MIN_IMAGE_OBJ_AREA:
                continue
                
            # Skip if covers almost entire slide
            if w > 0.9 * full_w and h > 0.9 * full_h:
                continue
            
            # Count text blocks inside this region
            text_inside_count = 0
            for block in text_blocks:
                bx, by, bw, bh = block['box']
                center = (bx + bw//2, by + bh//2)
                if point_in_bbox(center, (x, y, w, h)):
                    text_inside_count += 1
            
            # Skip complex diagrams with lots of text
            if text_inside_count > MAX_TEXT_IN_IMAGE_OBJECT:
                continue
                    
            # Extract crop with padding
            pad = IMAGE_OBJECT_PADDING
            x_p = max(0, x - pad)
            y_p = max(0, y - pad)
            w_p = min(full_w - x_p, w + 2*pad)
            h_p = min(full_h - y_p, h + 2*pad)
            
            crop = img[y_p:y_p+h_p, x_p:x_p+w_p]
            
            img_obj = {
                "path": "", 
                "box": [x_p, y_p, w_p, h_p],
                "box_original": [x, y, w, h],
                "crop": crop,
                "id": idx,
                "text_count": text_inside_count
            }
            image_objects.append(img_obj)
        
        return image_objects

    def _create_clean_background(
        self,
        img: np.ndarray,
        mask_text: np.ndarray,
        image_objects: List[Dict]
    ) -> np.ndarray:
        """
        Create clean background by inpainting text and image regions.
        """
        # Create mask for image objects
        mask_images = np.zeros(img.shape[:2], dtype=np.uint8)
        for img_obj in image_objects:
            x, y, w, h = img_obj['box']
            cv2.rectangle(mask_images, (x, y), (x+w, y+h), 255, -1)
        
        # Combine masks
        full_mask = cv2.bitwise_or(mask_text, mask_images)
        kernel_bg = np.ones((5,5), np.uint8)
        full_mask = cv2.dilate(full_mask, kernel_bg, iterations=2)
        
        # Inpaint
        clean_image = cv2.inpaint(img, full_mask, 5, cv2.INPAINT_NS)
        
        return clean_image

    def _filter_text_in_images(
        self,
        text_blocks: List[Dict],
        image_objects: List[Dict]
    ) -> List[Dict]:
        """
        Filter out text blocks that are inside extracted image objects.
        """
        final_text_blocks = []
        
        for block in text_blocks:
            bx, by, bw, bh = block['box']
            text_center = (bx + bw//2, by + bh//2)
            
            is_inside_image = False
            for img_obj in image_objects:
                if point_in_bbox(text_center, tuple(img_obj['box_original'])):
                    is_inside_image = True
                    break
            
            if not is_inside_image:
                final_text_blocks.append(block)
        
        return final_text_blocks

    def _save_debug_image(
        self,
        img: np.ndarray,
        text_blocks: List[Dict],
        image_objects: List[Dict],
        output_path: Path
    ) -> None:
        """
        Save debug visualization showing detected regions.
        """
        debug_img = img.copy()
        
        # Red = Image objects
        for img_obj in image_objects:
            x, y, w, h = img_obj['box_original']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(debug_img, f"T:{img_obj['text_count']}", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Green = Final text boxes
        for block in text_blocks:
            x, y, w, h = block['box']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 1)
        
        cv2.imwrite(str(output_path), debug_img)

    def process_image(
        self,
        image_path,
        output_dir=None,
        page_num: int = 0
    ) -> Dict:
        """
        Process an image to extract text paragraphs and separate image objects.
        
        Uses Gemini Vision API for accurate extraction when available,
        falls back to RapidOCR otherwise.
        
        Args:
            image_path: Path to the slide image
            output_dir: Directory to save extracted images (optional)
            page_num: Page number for Vision API context
        
        Returns:
            Dict with text_blocks, image_objects, clean_image, and used_gemini flag
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
            
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)
        
        full_h, full_w = img.shape[:2]
        
        # Try Gemini Vision API first
        text_blocks = []
        use_gemini = False
        
        if self.vision_analyzer.is_available:
            # Encode image as PNG bytes
            _, img_encoded = cv2.imencode('.png', img)
            img_bytes = img_encoded.tobytes()
            
            result = self.vision_analyzer.analyze_slide_layout(img_bytes, page_num)
            
            if result and 'text_elements' in result and len(result['text_elements']) > 0:
                use_gemini = True
                print(f"  ✓ Using Gemini Vision API ({len(result['text_elements'])} text elements)")
                text_blocks = self._process_vision_result(result, full_w, full_h)
        
        # Fallback to RapidOCR
        if not use_gemini:
            print(f"  → Falling back to RapidOCR")
            text_blocks = self._fallback_ocr(img)
        
        # Create text mask for inpainting
        mask_text = np.zeros(img.shape[:2], dtype=np.uint8)
        for block in text_blocks:
            x, y, w, h = block['box']
            cv2.rectangle(mask_text, (x, y), (x+w, y+h), 255, -1)
        
        # Dilate text mask
        kernel_text = np.ones((5,5), np.uint8)
        mask_text = cv2.dilate(mask_text, kernel_text, iterations=2)

        # Detect Image Objects
        image_objects = self._detect_image_objects(img, mask_text, text_blocks)
        
        # Create mask for image objects (for inpainting)
        mask_images = np.zeros(img.shape[:2], dtype=np.uint8)
        for img_obj in image_objects:
            x, y, w, h = img_obj['box']
            cv2.rectangle(mask_images, (x, y), (x+w, y+h), 255, -1)

        # Create Clean Background
        clean_image = self._create_clean_background(img, mask_text, image_objects)
        
        # Filter text blocks that overlap with extracted images
        final_text_blocks = self._filter_text_in_images(text_blocks, image_objects)
                
        # Save image objects
        if output_dir:
            for img_obj in image_objects:
                img_filename = f"{Path(image_path).stem}_img_{img_obj['id']}.png"
                img_path = output_dir / img_filename
                cv2.imwrite(str(img_path), img_obj['crop'])
                img_obj['path'] = str(img_path)

        # Debug Visualization
        if output_dir:
            debug_path = output_dir / f"{Path(image_path).stem}_debug.jpg"
            self._save_debug_image(img, final_text_blocks, image_objects, debug_path)
        
        return {
            "text_blocks": final_text_blocks,
            "image_objects": image_objects,
            "clean_image": clean_image,
            "used_gemini": use_gemini
        }


if __name__ == "__main__":
    pass
