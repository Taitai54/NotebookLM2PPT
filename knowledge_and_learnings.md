# NotebookLM to PPTX: Knowledge & Learnings
**Date:** 2026-01-18
**Status:** Best Working Version (Direct Extraction)

## 🏆 Best Working Configuration
The most reliable method for converting NotebookLM PDFs is **Direct PDF Extraction (PyMuPDF)** operating at the **Span Level**.

### Critical Settings
*   **Extraction Method:** `fitz` (PyMuPDF) `get_text("dict")`.
*   **Granularity:** **Spans** (not Blocks). NotebookLM PDFs often have poorly defined "Blocks" that cause text chaos. Using Spans and manually grouping them works best.
*   **Deduplication:** A custom filter is required to remove "Hidden Text Layers" (duplicate text often placed by OCR engines for indexing). This prevents "Ghosting" (double text).
    *   *Logic:* Overlap > 80% check in `direct_extractor.py`.
*   **Font Scaling:** `0.95` factor.
    *   *Why:* Matches the visual weight of the original PDF best without overflowing text boxes.
*   **Image Inpainting:** Standard OpenCV Inpainting with `pad=10`.
    *   *Why:* AI Inpainting (Gemini) was attempted but failed due to API limitations (Refusal/No Image Output). Standard CV is reliable enough with the improved masks.

## ❌ Failed Experiments (Do Not Repeat)

### 1. Vision-First AI (Gemini 2.0 Flash)
*   **Idea:** Use Multimodal AI to "see" the slide and return JSON layout.
*   **Failure Mode:** "Hallucination" of coordinates. The AI grouped text semantically well but placed it loosely, resulting in misalignment. It was also very slow and rate-limited.
*   **Verdict:** Too unstable and slow for production use compared to deterministic PDF extraction.

### 2. Smart Merging (Block-Based)
*   **Idea:** Trust the PDF's internal "Block" structure (as done in `NBLM2PPTX` repo) to group paragraphs.
*   **Failure Mode:** "Text all over the place". NotebookLM's PDF generation engine can create massive, overlapping, or fragmented blocks. Trusting them blindly destroys the layout.
*   **Verdict:** Manually grouping Spans based on X/Y proximity is superior (current implementation).

### 3. AI Background Removal
*   **Idea:** Ask Gemini to "remove text and return image".
*   **Failure Mode:** API Safety Filters and Capability blocks. The API often refuses to generate the image or returns text descriptions instead.
*   **Verdict:** Stick to OpenCV Inpainting until Image Generation APIs are more permissive/stable.

## 📂 Key Files
*   `notebooklm2ppt/direct_extractor.py`: The core engine. Contains the deduplication and span-grouping logic.
*   `notebooklm2ppt/ppt_generator.py`: Handles the font scaling heuristic.
*   `notebooklm2ppt/cli.py`: Orchestrates the pipeline (currently set to use `DirectSlideExtractor`).

## 🚀 Future Improvements Checklist
- [ ] Explore `pdf.js` (JavaScript) for rendering if Python rendering quality degrades.
- [ ] Re-visit AI Inpainting if Google releases a dedicated "Edit Image" endpoint for Gemini.
- [ ] Implement color extraction from the PDF spans to colorize the PPT text (currently defaults often).
