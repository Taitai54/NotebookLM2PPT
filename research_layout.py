import cv2
import numpy as np
import os
from pathlib import Path

def detect_regions(image_path):
    print(f"Analyzing: {image_path}")
    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold to find non-white content
    # In NotebookLM slides, bg is white (255)
    # Binary inverse: content becomes white (255), bg becomes black (0)
    _, binary = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
    
    # 2. Run OCR (simulation - assuming we have text mask)
    # To properly extract images, we need to IGNORE text regions. 
    # Since I can't run the full OCR pipeline here easily in a script without the context,
    # I will just look for LARGE contours. Text is usually small/fragmented.
    # Images/Boxes are large.
    
    # Dilate to connect nearby components
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"Found {len(contours)} contours")
    
    vis_img = img.copy()
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        
        # Filter:
        # 1. Ignore very small stuff (noise/page numbers)
        # 2. Ignore likely text lines (wide but very short) - though paragraphs might look like blocks.
        
        # Heuristic: Width > 100px AND Height > 100px
        if w > 100 and h > 100:
             cv2.rectangle(vis_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
             print(f"Potential Image Region: {x},{y} {w}x{h} (Area: {area})")
        else:
             # Likely text
             cv2.rectangle(vis_img, (x, y), (x+w, y+h), (0, 255, 0), 1)

    output_path = "debug_layout.jpg"
    cv2.imwrite(output_path, vis_img)
    print(f"Saved debug visualization to {output_path}")

if __name__ == "__main__":
    # Test on page 2 which likely has content
    target = r"c:\Users\matti\OneDrive\Documents\GitHub\NotebookLM2PPT\workspace\AI_Health_Implementation_North_Star_pngs\page_0002.png"
    if os.path.exists(target):
        detect_regions(target)
    else:
        # Fallback to any png
        ws = Path(r"c:\Users\matti\OneDrive\Documents\GitHub\NotebookLM2PPT\workspace\AI_Health_Implementation_North_Star_pngs")
        pngs = list(ws.glob("*.png"))
        if pngs:
            detect_regions(str(pngs[0]))
