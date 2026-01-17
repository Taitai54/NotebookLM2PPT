# NotebookLM2PPT OCR Conversion - Lessons Learned

## Project Goal
Convert NotebookLM-generated PDFs into editable PowerPoint presentations with:
- Fully recognized, editable text
- Separate image assets (diagrams, icons)
- Correct positioning
- No "doubled" or corrupted text

---

## Iteration History

### Version 1: "workspace" (BASELINE - User said "almost perfect")
**Settings:**
- Resolution: 150 DPI (default)
- Image Detection: `kernel (5,5)`, `iterations=3`
- Text Grouping: `1.5x line_height`
- Overlap Detection: Simple center-point check
- Padding: None

**Result:** User praised this as "almost perfect"  
**Issues:** Text/images "abridged" (cut off at edges)

---

### Version 4: "workspace_highres" (REGRESSION)
**Changes:** Resolution: 300 DPI (forced)
**Result:** **WORSE** - Diagrams shattered into tiny pieces  
**Learning:** 300 DPI with 150 DPI kernel settings doesn't work.

---

### Version 5-6: "workspace_v4", "workspace_v5", "workspace_v6" (REGRESSION)
**Changes:** Smart Asset Inpainting, Layered mode
**Result:** **WORSE** - Visual artifacts, "ghosting" / double text  
**Learning:** Can't have both image-with-text AND editable-text-box.

---

### Version 7-8: "workspace_v7", "workspace_v8" (REGRESSION)
**Changes:** Clean Card inpainting, Vision Pipeline with contrast
**Result:** **WORSE** - Over-engineered, artifacts  
**Learning:** Simple is better.

---

### Version 9: "workspace_golden" (PARTIAL SUCCESS)
**Changes:** Strict revert + 10px padding
**Result:** Better than recent versions, but still issues

---

### Version 10-13: "workspace_refined" through "workspace_refined4"
**Changes:** Various overlap thresholds (30%, 50%, 95%), text grouping (0.8x, 1.5x), erosion
**Result:** Still not matching "workspace" quality

---

## Key Parameters Reference

| Parameter | Location | Purpose | Best Value |
|-----------|----------|---------|------------|
| DPI | `cli.py` ~294 | Resolution | 150 |
| Image Kernel | `ocr_converter.py` ~60 | Connect diagrams | (5,5) |
| Dilation Iterations | `ocr_converter.py` ~61 | Glue amount | 3 |
| Overlap Threshold | `ocr_converter.py` ~113 | Discard text | 0.5 |
| Text Grouping | `ocr_converter.py` ~193 | Merge lines | 1.5x (original) |
| Padding | `ocr_converter.py` ~80 | Crop buffer | 10px |

---

## What Works
1. **150 DPI** - Stable
2. **5x5 kernel iter=3** - Good diagram detection
3. **10px padding** - Prevents cropped edges
4. **Simple overlap detection** - Complex inpainting fails

## What Doesn't Work
1. 300 DPI without scaling - Shatters diagrams
2. Smart inpainting - Too complex
3. Layered mode - Double text
4. Erosion - Breaks elements
5. Too strict grouping (0.8x) - Fragments paragraphs

---

## Rollback: "Almost Perfect" Baseline
```python
dpi = 150
kernel_img = (5,5), iterations=3
overlap = center-point check (not area ratio)
text_grouping = 1.5x line_height
padding = 0 (original) or 10 (improved)
```
