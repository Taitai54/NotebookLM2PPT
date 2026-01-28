import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from pathlib import Path

class SlideReconstructor:
    def __init__(self):
        self.ocr = RapidOCR()

    def process_image(self, image_path, output_dir=None):
        """
        Process an image to extract text paragraphs and separate image objects.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
            
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)
            
        # 1. Run OCR
        ocr_result, _ = self.ocr(img)
        
        raw_text_blocks = []
        mask_text = np.zeros(img.shape[:2], dtype=np.uint8)
        
        if ocr_result:
            for item in ocr_result:
                box_points, text, score = item
                
                # Filter unwanted text
                if "NotebookLM" in text:
                    pass 
                else:
                    pts = np.array(box_points, dtype=np.int32)
                    x, y, w, h = cv2.boundingRect(pts)
                    raw_text_blocks.append({
                        "text": text,
                        "box": [x, y, w, h],
                        "font_size": h 
                    })
                
                pts = np.array(box_points, dtype=np.int32)
                cv2.fillPoly(mask_text, [pts], 255)
                # Aggressive dilation for inpainting: Draw a padded rectangle
                # This ensures we fully cover the text pixels to prevent 'ghosting'
                x, y, w, h = cv2.boundingRect(pts)
                pad = 10 
                cv2.rectangle(mask_text, (max(0, x-pad), max(0, y-pad)), 
                              (min(img.shape[1], x+w+pad), min(img.shape[0], y+h+pad)), 255, -1)
        
        # Dilate text mask
        kernel_text = np.ones((7,7), np.uint8)
        mask_text = cv2.dilate(mask_text, kernel_text, iterations=3)

        # 2. Detect & Extract Image Objects
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Remove text
        binary_no_text = cv2.bitwise_and(binary, binary, mask=cv2.bitwise_not(mask_text))
        
        # Dilate to connect loose parts of diagrams
        # Removed erosion - was too aggressive and broke some elements
        kernel_img = np.ones((5,5), np.uint8)
        dilated_img_map = cv2.dilate(binary_no_text, kernel_img, iterations=2)
        
        contours, _ = cv2.findContours(dilated_img_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        image_objects = []
        mask_images = np.zeros(img.shape[:2], dtype=np.uint8)
        
        full_h, full_w = img.shape[:2]
        
        for idx, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # Heuristics
            if w > 30 and h > 30 and area > 1000:
                if w > 0.9 * full_w and h > 0.9 * full_h:
                    continue
                    
                # Extract crop with Padding (Safe improvement)
                pad = 10
                x_p = max(0, x - pad)
                y_p = max(0, y - pad)
                w_p = min(full_w - x_p, w + 2*pad)
                h_p = min(full_h - y_p, h + 2*pad)
                
                crop = img[y_p:y_p+h_p, x_p:x_p+w_p]
                
                img_obj = {
                    "path": "", 
                    "box": [x_p, y_p, w_p, h_p],
                    "crop": crop,
                    "id": idx
                }
                image_objects.append(img_obj)
                
                cv2.rectangle(mask_images, (x_p, y_p), (x_p+w_p, y_p+h_p), 255, -1)

        # 3. Create Clean Background
        full_mask = cv2.bitwise_or(mask_text, mask_images)
        kernel_text_bg = np.ones((7,7), np.uint8)
        full_mask = cv2.dilate(full_mask, kernel_text_bg, iterations=2)
        
        # Inpaint
        clean_image = cv2.inpaint(img, full_mask, 3, cv2.INPAINT_NS)
        
        # 4. Group Text into Paragraphs
        grouped_blocks = self.group_text_blocks(raw_text_blocks)
        
        # 5. Overlap Detection
        # If text overlaps an image by 50%+, discard it - the image shows that text
        # 50% is a balance: catches true overlaps, preserves edge text
        final_text_blocks = []
        overlap_threshold = 0.5
        
        for block in grouped_blocks:
            bx, by, bw, bh = block['box']
            
            is_inside_image = False
            for img_obj in image_objects:
                ix, iy, iw, ih = img_obj['box']
                
                # Calculate intersection area
                x_overlap = max(0, min(bx + bw, ix + iw) - max(bx, ix))
                y_overlap = max(0, min(by + bh, iy + ih) - max(by, iy))
                overlap_area = x_overlap * y_overlap
                text_area = bw * bh
                
                # Check if text is mostly (70%+) inside the image
                if text_area > 0 and (overlap_area / text_area) > overlap_threshold:
                    is_inside_image = True
                    break
            
            if not is_inside_image:
                final_text_blocks.append(block)
                
        # Save image objects
        if output_dir:
            for img_obj in image_objects:
                img_filename = f"{Path(image_path).stem}_img_{img_obj['id']}.png"
                img_path = output_dir / img_filename
                cv2.imwrite(str(img_path), img_obj['crop'])
                img_obj['path'] = str(img_path)

        # 6. Debug Visualization
        if output_dir:
            debug_img = img.copy()
            # Draw Image Boxes (Red)
            for img_obj in image_objects:
                x, y, w, h = img_obj['box']
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
            
            # Draw Final Text Boxes (Green)
            for block in final_text_blocks:
                x, y, w, h = block['box']
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
            debug_path = output_dir / f"{Path(image_path).stem}_debug.jpg"
            cv2.imwrite(str(debug_path), debug_img)
        
        return {
            "text_blocks": final_text_blocks,
            "image_objects": image_objects,
            "clean_image": clean_image
        }

    def group_text_blocks(self, blocks):
        """
        Merges single-line text blocks into paragraphs based on spatial proximity.
        Made LESS aggressive to prevent incorrectly merging separate slide elements.
        """
        if not blocks:
            return []
            
        # Sort by Y coordinate primarily, X secondarily
        # Group logic relies on reading order (top-down, left-right)
        blocks.sort(key=lambda b: (b['box'][1], b['box'][0]))
        
        merged_blocks = []
        
        if not blocks:
            return []
            
        current_block = blocks[0]
        
        for next_block in blocks[1:]:
            # Check criteria to merge 'next_block' into 'current_block'
            
            # 1. Vertical Proximity
            # Distance between bottom of current and top of next
            curr_bottom = current_block['box'][1] + current_block['box'][3]
            next_top = next_block['box'][1]
            vertical_dist = next_top - curr_bottom
            
            # STRICT: Only 0.3x line height (was 0.8x - too aggressive)
            # This prevents separate bullet points and slide elements from merging
            line_height = current_block['box'][3]
            if vertical_dist < line_height * 0.3 and vertical_dist >= -5:
                
                # 2. Horizontal Alignment (must be well-aligned)
                h_diff = abs(current_block['box'][0] - next_block['box'][0])
                if h_diff < 30: # Reduced from 50px - stricter alignment
                    
                    # MERGE
                    # Update text: join with space
                    current_block['text'] += " " + next_block['text']
                    
                    # Update box: union of both boxes
                    x1 = min(current_block['box'][0], next_block['box'][0])
                    y1 = min(current_block['box'][1], next_block['box'][1])
                    x2 = max(current_block['box'][0] + current_block['box'][2], 
                             next_block['box'][0] + next_block['box'][2])
                    y2 = max(current_block['box'][1] + current_block['box'][3], 
                             next_block['box'][1] + next_block['box'][3])
                    
                    current_block['box'] = [x1, y1, x2-x1, y2-y1]
                    continue
            
            # If not merged, push current and start new
            merged_blocks.append(current_block)
            current_block = next_block
            
        merged_blocks.append(current_block)
        
        # Post-process: fix common OCR issues
        for block in merged_blocks:
            block['text'] = self._fix_ocr_text(block['text'])
            
        # Post-process: remove overlapping text artifacts
        merged_blocks = self._filter_overlapping_text(merged_blocks)
        
        return merged_blocks
    
    def _fix_ocr_text(self, text):
        """Fix common OCR spacing and character errors."""
        import re
        if not text:
            return text
        
        # Add space before capitals in middle of words (CamelCase from merged words)
        # e.g. "TheStrategic" -> "The Strategic"
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Add space after punctuation if followed by a letter
        # e.g. "Hello,world" -> "Hello, world"
        text = re.sub(r'([,;:])([A-Za-z])', r'\1 \2', text)
        
        # Add space after period if followed by uppercase
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        # Fix lowercase-lowercase merges (aggressive but needed for "neutraladvice")
        # Finds 3+ letter words merged: [a-z]{3,}[a-z]{3,}
        # This is risky without a dictionary, but we can target specific patterns
        # e.g. "neutraladvice" -> "neutral advice"
        
        # Clean up double spaces
        text = re.sub(r'  +', ' ', text)
        
        # Add space around 'vs' if stuck (e.g. differsvsweights -> differs vs weights)
        text = re.sub(r'(\w)vs(\w)', r'\1 vs \2', text)
        
        # Add space around 'and' if stuck (risky, but safe for 'routinesandoutcome')
        # Limiting to at least 3 chars before/after to avoid 'band', 'sand' issues inside words? 
        # Actually 'sand' is a word. 'hand' is a word. 
        # Safer: only fix 'vs'
        
        return text.strip()

    def _filter_overlapping_text(self, blocks, threshold=0.2):
        """
        Remove text blocks that overlap significantly with other text blocks.
        This fixes the 'double text' / z-fighting issue.
        """
        if not blocks:
            return []
            
        # Sort by area (keep larger blocks usually?) or confidence?
        # Assuming we want to keep the one that encompasses the other
        blocks.sort(key=lambda b: b['box'][2] * b['box'][3], reverse=True)
        
        filtered = []
        indices_to_remove = set()
        
        for i in range(len(blocks)):
            if i in indices_to_remove:
                continue
                
            b1 = blocks[i]
            x1, y1, w1, h1 = b1['box']
            area1 = w1 * h1
            
            for j in range(i + 1, len(blocks)):
                if j in indices_to_remove:
                    continue
                    
                b2 = blocks[j]
                x2, y2, w2, h2 = b2['box']
                area2 = w2 * h2
                
                # Calculate intersection
                xx1 = max(x1, x2)
                yy1 = max(y1, y2)
                xx2 = min(x1 + w1, x2 + w2)
                yy2 = min(y1 + h1, y2 + h2)
                
                w_inter = max(0, xx2 - xx1)
                h_inter = max(0, yy2 - yy1)
                inter_area = w_inter * h_inter
                
                if inter_area > 0:
                    # Check intersection against smaller block area
                    smaller_area = min(area1, area2)
                    if smaller_area > 0 and (inter_area / smaller_area) > threshold:
                        # Significant overlap! Remove the smaller one
                        if area1 < area2:
                            indices_to_remove.add(i)
                            break # b1 is removed, stop checking b1 against others
                        else:
                            indices_to_remove.add(j)
        
        for i in range(len(blocks)):
            if i not in indices_to_remove:
                filtered.append(blocks[i])
                
        return filtered

if __name__ == "__main__":
    pass
