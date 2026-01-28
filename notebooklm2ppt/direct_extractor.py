import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

class DirectSlideExtractor:
    """
    Extracts text and objects directly from PDF using PyMuPDF (digital layer),
    bypassing OCR for better accuracy.
    """
    
    def __init__(self):
        pass

    def process_page(self, pdf_path: str, page_num: int, image_path: str, output_dir=None) -> Dict:
        """
        Process a specific page of the PDF to extract text and objects.
        
        Args:
            pdf_path: Path to source PDF
            page_num: Page number (0-indexed)
            image_path: Path to the rendered PNG of this page (for dimensions/diagrams)
            output_dir: Debug output directory
            
        Returns:
            Dict matching SlideReconstructor format:
            {
                "text_blocks": [...],
                "image_objects": [...],
                "clean_image": ...
            }
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Load the rendered image to match dimensions
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
            
        img_h, img_w = img.shape[:2]
        
        # PDF dimensions
        rect = page.rect
        pdf_w, pdf_h = rect.width, rect.height
        
        # Scale factors (PDF point -> Image Pixel)
        scale_x = img_w / pdf_w
        scale_y = img_h / pdf_h
        
        # 1. Extract Text with sophisticated filtering
        text_blocks = []
        # "dict" format gives detailed text positioning: block -> line -> span
        text_data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)
        
        mask_text = np.zeros((img_h, img_w), dtype=np.uint8)
        
        seen_boxes = [] # To check for duplicates
        
        for block in text_data.get("blocks", []):
            if block["type"] == 0: # Text
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        
                        # Filter tiny text (often OCR artifacts)
                        if span["size"] < 4:
                            continue
                            
                        # Filter invisible text (white on white or transparent)
                        # PyMuPDF color is sRGB int or list? usually int or tuple.
                        # We assume if alpha is present and 0, or color is white...
                        # Actually standard check is render mode (invisible). fitz doesn't expose render mode easily in dict.
                        # But we can check overlap.
                        
                        # PDF BBox (x0, y0, x1, y1)
                        bx0, by0, bx1, by1 = span["bbox"]
                        
                        # Convert to Image Pixels
                        px0, py0 = int(bx0 * scale_x), int(by0 * scale_y)
                        px1, py1 = int(bx1 * scale_x), int(by1 * scale_y)
                        
                        w = px1 - px0
                        h = py1 - py0
                        
                        current_box = [px0, py0, w, h]
                        
                        # DUPLICATE CHECK: 
                        # If this box significantly overlaps with a seen box AND text is similar-ish
                        # "hidden text layer" usually sits exactly on top of visible text.
                        is_duplicate = False
                        for seen_b in seen_boxes:
                            sx, sy, sw, sh = seen_b
                            # Intersection
                            ix = max(px0, sx)
                            iy = max(py0, sy)
                            iw = min(px0+w, sx+sw) - ix
                            ih = min(py0+h, sy+sh) - iy
                            
                            if iw > 0 and ih > 0:
                                inter_area = iw * ih
                                self_area = w * h
                                # If 80% overlap
                                if inter_area / self_area > 0.8:
                                    is_duplicate = True
                                    break
                        
                        if is_duplicate:
                            continue
                            
                        seen_boxes.append(current_box)
                        
                        text_blocks.append({
                            "text": text,
                            "box": [px0, py0, w, h],
                            "font_size": span["size"] * scale_y, # Use scaled font size
                            "font": span["font"],
                            "color": span["color"]
                        })
                        
                        # Add to text mask (slightly dilated)
                        pad = 5 # Moderate padding
                        cv2.rectangle(mask_text, (max(0, px0-pad), max(0, py0-pad)), 
                                      (min(img_w, px1+pad), min(img_h, py1+pad)), 255, -1)

        # Group text blocks into paragraphs
        grouped_blocks = self._group_text_spans(text_blocks)

        # 2. Extract Image Objects (Diagrams)
        # We assume diagrams are valid image content that is NOT text.
        # So we look at the original image, masked where the digital text is.
        # What remains are: backgrounds, non-text graphics, embedded images.
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Remove known text areas from the binary map
        binary_no_text = cv2.bitwise_and(binary, binary, mask=cv2.bitwise_not(mask_text))
        
        # Dilate to connect diagram parts
        kernel_img = np.ones((5,5), np.uint8)
        dilated_img_map = cv2.dilate(binary_no_text, kernel_img, iterations=2)
        
        contours, _ = cv2.findContours(dilated_img_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        image_objects = []
        mask_images = np.zeros((img_h, img_w), dtype=np.uint8)
        
        for idx, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # Heuristics for diagrams
            if w > 30 and h > 30 and area > 1000:
                if w > 0.9 * img_w and h > 0.9 * img_h:
                    continue # Likely full page border
                    
                pad = 10
                x_p, y_p = max(0, x - pad), max(0, y - pad)
                w_p, h_p = min(img_w - x_p, w + 2*pad), min(img_h - y_p, h + 2*pad)
                
                crop = img[y_p:y_p+h_p, x_p:x_p+w_p]
                
                img_obj = {
                    "path": "", 
                    "box": [x_p, y_p, w_p, h_p],
                    "crop": crop,
                    "id": idx
                }
                image_objects.append(img_obj)
                cv2.rectangle(mask_images, (x_p, y_p), (x_p+w_p, y_p+h_p), 255, -1)
        
        # 3. Save Image Objects
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)
            for img_obj in image_objects:
                img_filename = f"{Path(image_path).stem}_img_{img_obj['id']}.png"
                img_path_out = output_dir / img_filename
                cv2.imwrite(str(img_path_out), img_obj['crop'])
                img_obj['path'] = str(img_path_out)
        
        # 4. Create Clean Background
        # Mask out both text and extracted images to leave just the background
        full_mask = cv2.bitwise_or(mask_text, mask_images)
        kernel_text_bg = np.ones((7,7), np.uint8)
        full_mask = cv2.dilate(full_mask, kernel_text_bg, iterations=2)
        
        # Remove NotebookLM icon/watermark from bottom-right corner
        # Icon is approximately at 91% from left, 96% from top, 8% width x 4% height
        icon_left = int(0.91 * img_w)
        icon_top = int(0.95 * img_h)
        full_mask[icon_top:, icon_left:] = 255  # Mark for inpainting
        
        clean_image = cv2.inpaint(img, full_mask, 3, cv2.INPAINT_NS)
        
        # Debug Output
        if output_dir:
            debug_img = img.copy()
            for b in grouped_blocks:
                x, y, w, h = b['box']
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 1)
            for i in image_objects:
                x, y, w, h = i['box']
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.imwrite(str(output_dir / f"{Path(image_path).stem}_debug_direct.jpg"), debug_img)
            
        return {
            "text_blocks": grouped_blocks,
            "image_objects": image_objects,
            "clean_image": clean_image
        }

    def _group_text_spans(self, raw_blocks):
        """
        Group individual text spans from PyMuPDF into logical paragraphs.
        PyMuPDF spans are often single lines or even fragments.
        """
        if not raw_blocks:
            return []
            
        # Sort top-down, left-right
        raw_blocks.sort(key=lambda b: (b['box'][1], b['box'][0]))
        
        merged = []
        if not raw_blocks:
            return []
            
        curr = raw_blocks[0]
        
        for next_b in raw_blocks[1:]:
            # Check for merging
            # Same alignment? Close vertically?
            
            x_diff = abs(curr['box'][0] - next_b['box'][0])
            
            curr_bottom = curr['box'][1] + curr['box'][3]
            next_top = next_b['box'][1]
            y_dist = next_top - curr_bottom
            
            line_height = curr['box'][3]
            
            # Merging Logic:
            # 1. Horizontal alignment (strict)
            # 2. Vertical Proximity (logical line wrap)
            # 3. Font similarity (optional, but good for headers vs body)
            
            # Simple heuristic for now:
            if x_diff < 10 and y_dist < line_height * 1.5 and y_dist >= -5:
                # Merge
                curr['text'] += " " + next_b['text']
                
                # Expand box
                x1 = min(curr['box'][0], next_b['box'][0])
                y1 = min(curr['box'][1], next_b['box'][1])
                x2 = max(curr['box'][0] + curr['box'][2], next_b['box'][0] + next_b['box'][2])
                y2 = max(curr['box'][1] + curr['box'][3], next_b['box'][1] + next_b['box'][3])
                
                curr['box'] = [x1, y1, x2-x1, y2-y1]
            else:
                merged.append(curr)
                curr = next_b
                
        merged.append(curr)
        return merged
