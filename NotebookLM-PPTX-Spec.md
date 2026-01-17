/# NotebookLM PDF to PowerPoint Converter - Development Specification

**Status**: Ready for LLM IDE Implementation  
**Date**: January 17, 2026  
**Based on**: Codea AI/NoteSlide research + NBLM2PPTX open-source analysis  

---

## TABLE OF CONTENTS

1. [Project Overview](#project-overview)
2. [Technical Architecture](#technical-architecture)
3. [Core Methodology](#core-methodology)
4. [Implementation Details](#implementation-details)
5. [API Integration](#api-integration)
6. [Development Roadmap](#development-roadmap)
7. [Code Structure](#code-structure)

---

## PROJECT OVERVIEW

### Objective
Build an automated system to convert NotebookLM-generated PDF slide decks into fully editable PowerPoint presentations (PPTX) with separated background images and editable text layers.

### Problem Statement
NotebookLM exports slide decks only as flattened PDFs, where text and images are rendered together as a single visual layer. Users cannot edit text, adjust layouts, or modify content without manual screenshot editing. Current solutions are:
- **Canva Pro**: Requires manual effort to make text editable
- **Adobe Acrobat + ChatGPT**: Workaround, not automated
- **Commercial tools**: Codea AI/NoteSlide (pay-per-use, not open)

### Solution Architecture
1. Extract PDF structure (text + images + positioning data)
2. Use AI Vision API to understand slide layout
3. Separate background images from text content
4. Generate PowerPoint with:
   - Original images as slide backgrounds
   - Extracted text as editable text boxes
   - Proper positioning and formatting preserved

### Success Metrics
- ✅ 100% of text remains editable in output PPTX
- ✅ Image quality maintained at original resolution
- ✅ Positioning accuracy within 2% of original
- ✅ Processing time: <5 seconds per slide
- ✅ Compatible with PowerPoint 2019+, Office 365, Google Slides
- ✅ Zero content loss

---

## TECHNICAL ARCHITECTURE

### Component Overview

```
┌─────────────────────────────────────────────────────┐
│                    INPUT LAYER                       │
│              NotebookLM PDF Upload                   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│           PDF PROCESSING PIPELINE                    │
├─────────────────────────────────────────────────────┤
│  1. PDF Analysis (PyMuPDF)                          │
│     ├─ Extract pages                                │
│     ├─ Get page dimensions                          │
│     ├─ Extract all images with coordinates          │
│     └─ Extract text with bounding boxes             │
│                                                      │
│  2. Text Extraction (PDFText)                       │
│     ├─ Structured text blocks                       │
│     ├─ Font information (name, size, weight)        │
│     ├─ Position data (x, y, width, height)          │
│     └─ Color information                            │
│                                                      │
│  3. Vision Analysis (Gemini API)                    │
│     ├─ Render page to high-res image                │
│     ├─ Analyze layout structure                     │
│     ├─ Identify text regions                        │
│     ├─ Detect graphics/decorations                  │
│     └─ Return JSON with confidence scores           │
│                                                      │
│  4. Layer Separation Engine                         │
│     ├─ Identify background vs foreground            │
│     ├─ Group related text elements                  │
│     ├─ Remove watermarks                            │
│     └─ Prepare export-ready assets                  │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│         POWERPOINT GENERATION (python-pptx)         │
├─────────────────────────────────────────────────────┤
│  1. Create Presentation                             │
│  2. For each page:                                  │
│     ├─ Create blank slide                           │
│     ├─ Add background image                         │
│     ├─ Add positioned text boxes                    │
│     ├─ Preserve formatting (fonts, colors)          │
│     └─ Set proper z-ordering                        │
│  3. Apply slide dimensions & properties             │
│  4. Save to PPTX file                               │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                  OUTPUT LAYER                        │
│       Fully Editable PowerPoint (PPTX)              │
└─────────────────────────────────────────────────────┘
```

### Key Technologies

| Component | Library | Purpose | Rationale |
|-----------|---------|---------|-----------|
| PDF Reading | PyMuPDF (fitz) | Extract images, text, coordinates | Fast, comprehensive, industry standard |
| Text Extraction | pdftext (PDFText) | Structured text with position | 97.78% accuracy, Apache license, font metadata |
| Image Extraction | PyMuPDF | Bitmap image extraction | Already using for PDF, coordinates included |
| Vision Analysis | Google Gemini API | Layout understanding | Accurate, fast, handles complex layouts |
| PPTX Generation | python-pptx | Create editable PowerPoint | Only mainstream pure-Python PPTX library |
| Image Processing | Pillow (PIL) | Image optimization | Standard, reliable |
| Async Processing | asyncio | Parallel page processing | Built-in Python, no extra deps needed |

---

## CORE METHODOLOGY

### NotebookLM PDF Characteristics

**What NotebookLM creates:**
- Flattened PDF: Text and images composited as single visual layer
- Text Layer: OCR/embedded, selectable text (preserves content)
- Image Layer: Rendered background graphics
- Watermark: Applied as additional layer (can be removed)
- Format: Typically 16:9 aspect ratio, 1920x1080 or similar

**Why standard PDF extraction fails:**
- Text bounding boxes may not align with visual positions
- Images are integrated with text as single raster
- Layout hierarchy lost in flattening process
- Visual and logical structure differ

### Three-Phase Extraction Strategy

#### Phase 1: Raw Data Extraction

**PyMuPDF Analysis:**
```
For each PDF page:
  1. Get page dimensions (page_height, page_width)
  2. List all embedded images:
     - Extract image bytes
     - Get reference number (xref)
     - Get position rectangle [x0, y0, x1, y1]
     - Store image with metadata
  3. List all text content:
     - Extract text blocks
     - Get block coordinates
     - Note font information
```

**PDFText Analysis:**
```
For each PDF page:
  1. Extract structured blocks (paragraphs)
  2. For each block:
     - Get bounding box
     - List lines within block
     - For each line:
       - Get line bounding box
       - List text spans
       - For each span:
         - Text content
         - Font name, size, weight
         - Color (if available)
         - Position bbox [x1, y1, x2, y2]
```

**Output**: JSON structure with all elements and coordinates

#### Phase 2: Vision-Based Layout Analysis

**Gemini Vision API Call:**
```
Input:
  - Page rendered as PNG (300 DPI)
  - Analysis request:
    {
      "task": "analyze_slide_layout",
      "requirements": [
        "Identify background image area (bounding box)",
        "Identify all text content (bounding boxes + content)",
        "Identify graphics, icons, decorations",
        "Determine text hierarchy (title, subtitle, body, emphasis)",
        "Identify empty space regions",
        "Return confidence score for each element"
      ],
      "format": "json"
    }

Output:
  {
    "background_image": {
      "bbox": [x, y, w, h],
      "color_dominant": "#hexcode",
      "confidence": 0.95
    },
    "text_elements": [
      {
        "text": "extracted text",
        "bbox": [x, y, w, h],
        "role": "title|subtitle|body|emphasis",
        "font_size_estimate": "large|medium|small",
        "confidence": 0.92
      }
    ],
    "graphics": [
      {
        "type": "icon|shape|decoration",
        "bbox": [x, y, w, h],
        "description": "...",
        "confidence": 0.88
      }
    ],
    "layout_type": "title_with_image|two_column|centered|full_bleed",
    "processing_quality": "high|medium|low"
  }
```

#### Phase 3: Intelligent Layer Separation

**Algorithm:**

```
1. IDENTIFY BACKGROUND LAYER
   Input: Vision API output + PyMuPDF images
   
   For each extracted image:
     a. Check if marked as "background_image" by Vision API
     b. If yes:
        - Mark as background
        - Store original position
        - Extract at maximum resolution
     c. If uncertain:
        - Compare size to page size
        - If >70% of page: likely background
        - If <30% of page: likely content graphic
   
   Action: Extract largest/fullest image as background

2. IDENTIFY TEXT ELEMENTS
   Input: PDFText output + Vision API text_elements
   
   For each text span from PDFText:
     a. Validate position with Vision API results
     b. Calculate confidence:
        - PDFText confidence (native extraction)
        - Vision API confidence (image recognition)
        - Overlap between both outputs
     c. If both agree (confidence >0.85):
        - Extract as editable text box
        - Store position, font, color
     d. If mismatch:
        - Use Vision API bbox (more reliable for flattened PDFs)
        - Flag for manual review if confidence <0.70
   
   Output: List of [text, position, formatting] tuples

3. IDENTIFY & REMOVE WATERMARKS
   Input: All extracted images + Vision API description
   
   Algorithm:
     a. Detect if NotebookLM watermark present
        - Known watermark pattern recognition
        - Color sampling in corners/edges
     b. If detected:
        - Get surrounding color/gradient
        - Use inpainting algorithm:
          * Bilinear interpolation
          * Multi-point color sampling
          * Gradient reconstruction
        - Replace watermark with background
     c. Validate watermark removal quality
   
   Output: Cleaned image without watermark

4. HANDLE OVERLAPS & ORDERING
   For each text element:
     a. Check if overlaps with background image
     b. If yes:
        - Add semi-transparent background to text box
        - OR adjust text color for contrast
        - Store z-order (text above image)
     c. Validate readability
   
   Output: Conflict resolution list

5. PREPARE FOR EXPORT
   a. Convert coordinates from PDF space to PPTX EMUs:
      * PDF origin: (0,0) at bottom-left, y goes up
      * PPTX origin: (0,0) at top-left, y goes down
      * Formula: pptx_y = page_height - pdf_y
      * Convert inches to EMUs: value * 914400
   
   b. Validate all coordinates are within slide bounds
   c. Group text elements by position (for logical text boxes)
   d. Prepare image file for insertion
```

---

## IMPLEMENTATION DETAILS

### Module 1: PDF Processing

```python
# pdf_processor.py

class PDFProcessor:
    """
    Extract structured data from NotebookLM PDFs
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None
        self.pages_data = []
    
    def extract_all_images(self) -> List[Dict]:
        """
        Extract all images with position metadata
        Returns: [{xref, bytes, bbox, page_num}]
        """
        # Implementation
    
    def extract_text_with_coords(self) -> List[Dict]:
        """
        Extract text using PDFText (structured)
        Returns: [{text, bbox, font_info, page_num}]
        """
        # Implementation
    
    def get_page_dimensions(self, page_num: int) -> Tuple[float, float]:
        """
        Get width and height of page in points
        """
        # Implementation
    
    def render_page_to_image(self, page_num: int, dpi: int = 300) -> bytes:
        """
        Render PDF page to high-resolution PNG for vision analysis
        """
        # Implementation
```

### Module 2: Vision Analysis

```python
# vision_analyzer.py

class VisionAnalyzer:
    """
    Use Google Gemini Vision API to understand slide layout
    """
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"  # Latest vision model
    
    async def analyze_slide_layout(self, image_bytes: bytes) -> Dict:
        """
        Send image to Gemini for layout analysis
        
        Returns: {
            'background_image': {...},
            'text_elements': [...],
            'graphics': [...],
            'layout_type': str,
            'confidence': float
        }
        """
        # Implementation: Call Gemini API with structured prompt
    
    def _build_analysis_prompt(self) -> str:
        """
        Construct detailed prompt for consistent vision results
        """
        # Implementation
    
    def _parse_vision_response(self, response: str) -> Dict:
        """
        Parse and validate Gemini JSON response
        """
        # Implementation
```

### Module 3: Layer Separation

```python
# layer_separator.py

class LayerSeparator:
    """
    Intelligently separate background images from text layers
    """
    
    def __init__(self, pdf_data: Dict, vision_data: Dict):
        self.pdf_data = pdf_data
        self.vision_data = vision_data
        self.background = None
        self.text_elements = []
        self.graphics = []
    
    def separate_layers(self) -> Dict:
        """
        Main separation workflow
        """
        self._identify_background()
        self._identify_text_elements()
        self._remove_watermarks()
        self._resolve_overlaps()
        self._prepare_export_data()
        
        return {
            'background': self.background,
            'text_elements': self.text_elements,
            'graphics': self.graphics
        }
    
    def _identify_background(self):
        """
        Find and extract background image
        - Largest image, or
        - Image marked as background by Vision API
        """
        # Implementation
    
    def _identify_text_elements(self):
        """
        Extract all text with validated positioning
        - Cross-reference PDFText and Vision API
        - Calculate confidence scores
        - Group related text
        """
        # Implementation
    
    def _remove_watermarks(self):
        """
        Detect and remove NotebookLM watermarks
        Algorithm:
        1. Pattern detection
        2. Color sampling from surroundings
        3. Inpainting with bilinear interpolation
        """
        # Implementation
    
    def _resolve_overlaps(self):
        """
        Handle text overlapping with background
        - Add contrast backgrounds to text
        - Adjust colors if needed
        - Maintain readability
        """
        # Implementation
    
    def _prepare_export_data(self):
        """
        Convert all coordinates to PPTX-ready format
        - PDF → PPTX coordinate conversion
        - Validate bounds
        - Group elements logically
        """
        # Implementation
```

### Module 4: PowerPoint Generation

```python
# pptx_generator.py

class PowerPointGenerator:
    """
    Generate fully editable PPTX from separated layers
    """
    
    def __init__(self, width_inches: float = 10, height_inches: float = 5.625):
        self.prs = Presentation()
        self.prs.slide_width = Inches(width_inches)
        self.prs.slide_height = Inches(height_inches)
        self.slides_created = 0
    
    def create_slide_from_data(self, slide_data: Dict) -> None:
        """
        Create single slide with background image and text boxes
        
        slide_data: {
            'background': image_bytes,
            'text_elements': [{'text': str, 'bbox': (x,y,w,h), 'font': ...}],
            'graphics': [...]
        }
        """
        # Implementation
    
    def _add_background_image(self, slide, image_bytes: bytes) -> None:
        """
        Add image as slide background
        - Full bleed to slide dimensions
        - Maintain aspect ratio
        """
        # Implementation
    
    def _add_text_boxes(self, slide, text_elements: List[Dict]) -> None:
        """
        Add editable text boxes for each text element
        - Position accurately on slide
        - Preserve font, color, size
        - Make text fully editable
        """
        # Implementation
    
    def _add_graphics(self, slide, graphics: List[Dict]) -> None:
        """
        Add remaining graphics/icons
        """
        # Implementation
    
    def save(self, output_path: str) -> None:
        """
        Save presentation to PPTX file
        """
        self.prs.save(output_path)
        print(f"✓ Saved {self.slides_created} slides to {output_path}")
```

### Module 5: Main Orchestrator

```python
# converter.py

class NotebookLMToPPTXConverter:
    """
    Main orchestrator for the conversion pipeline
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.processor = None
        self.analyzer = None
        self.separator = None
        self.generator = None
    
    async def convert(self, pdf_path: str, output_path: str) -> None:
        """
        Main conversion workflow:
        1. Extract PDF data
        2. Analyze with Vision API
        3. Separate layers
        4. Generate PowerPoint
        """
        
        print(f"📄 Processing: {pdf_path}")
        
        # Step 1: Extract PDF
        print("  [1/5] Extracting PDF structure...")
        self.processor = PDFProcessor(pdf_path)
        pdf_data = self.processor.extract_all_data()
        
        # Step 2: Vision analysis
        print("  [2/5] Analyzing slide layouts...")
        self.analyzer = VisionAnalyzer(self.api_key)
        vision_data = await self.analyzer.analyze_all_slides(pdf_data)
        
        # Step 3: Layer separation
        print("  [3/5] Separating layers...")
        self.separator = LayerSeparator(pdf_data, vision_data)
        separated_data = self.separator.separate_layers()
        
        # Step 4: Generate PPTX
        print("  [4/5] Generating PowerPoint...")
        self.generator = PowerPointGenerator()
        self.generator.create_presentation(separated_data)
        
        # Step 5: Save output
        print("  [5/5] Saving output...")
        self.generator.save(output_path)
        
        print(f"✅ Conversion complete: {output_path}")
```

---

## API INTEGRATION

### Google Gemini Vision Setup

```python
# config.py

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"  # Latest multimodal model
DPI_FOR_VISION = 300  # High-res for accuracy
VISION_CONFIDENCE_THRESHOLD = 0.75  # When to trust Vision API
```

### Sample Vision API Call

```python
# vision_analyzer.py (detailed)

async def analyze_slide_layout(self, image_bytes: bytes, page_num: int) -> Dict:
    """
    Call Gemini Vision API for slide layout analysis
    """
    
    import base64
    import json
    
    # Encode image to base64
    image_b64 = base64.standard_b64encode(image_bytes).decode('utf-8')
    
    # Construct analysis request
    prompt = f"""
    You are analyzing a NotebookLM-generated slide (page {page_num}).
    
    CRITICAL INSTRUCTIONS:
    1. Identify the BACKGROUND IMAGE area (usually the main visual)
    2. Identify ALL TEXT CONTENT with precise bounding boxes
    3. For each text element, provide:
       - Exact text content
       - Bounding box as [x, y, width, height] in pixels
       - Text role: "title" | "subtitle" | "body" | "emphasis"
       - Estimated font size category: "large" | "medium" | "small"
    4. Identify any graphics, icons, or decorative elements
    5. Assess overall layout type
    
    RETURN ONLY VALID JSON (no markdown, no explanations):
    {{
        "background_image": {{
            "bbox": [x, y, w, h],
            "description": "...",
            "confidence": 0.0-1.0
        }},
        "text_elements": [
            {{
                "text": "...",
                "bbox": [x, y, w, h],
                "role": "title|subtitle|body|emphasis",
                "font_size": "large|medium|small",
                "confidence": 0.0-1.0
            }}
        ],
        "graphics": [
            {{
                "type": "icon|shape|decoration",
                "bbox": [x, y, w, h],
                "description": "...",
                "confidence": 0.0-1.0
            }}
        ],
        "layout_type": "...",
        "overall_confidence": 0.0-1.0,
        "extraction_quality": "high|medium|low"
    }}
    """
    
    # Call Gemini API
    response = self.client.models.generate_content(
        model=self.model,
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_b64
                        }
                    }
                ]
            }
        ],
        generation_config={
            "temperature": 0.0,  # Deterministic
            "max_output_tokens": 4096,
        }
    )
    
    # Parse response
    response_text = response.text
    
    # Extract JSON (handle markdown wrapping if present)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    result = json.loads(response_text.strip())
    return result
```

### Error Handling & Fallback

```python
# vision_analyzer.py (error handling)

async def analyze_slide_layout_with_fallback(self, 
                                              image_bytes: bytes, 
                                              page_num: int) -> Dict:
    """
    Analyze with Vision API, fallback to basic PDF extraction if fails
    """
    try:
        result = await self.analyze_slide_layout(image_bytes, page_num)
        
        # Validate result
        if not result.get('text_elements') or result.get('overall_confidence', 0) < 0.5:
            print(f"⚠️  Low confidence on page {page_num}, using fallback")
            return self._generate_fallback_result()
        
        return result
        
    except RateLimitError:
        print(f"⚠️  Rate limited on page {page_num}, waiting...")
        await asyncio.sleep(60)
        return await self.analyze_slide_layout_with_fallback(image_bytes, page_num)
        
    except Exception as e:
        print(f"❌ Vision API error on page {page_num}: {e}")
        print(f"   Falling back to PDF-only extraction...")
        return self._generate_fallback_result()

def _generate_fallback_result(self) -> Dict:
    """
    Generate result using only PDF-extracted data (no Vision API)
    - Use PDFText coordinates directly
    - Assume first large image is background
    - Less accurate but always works
    """
    return {
        "background_image": {
            "bbox": [0, 0, 1920, 1080],  # Full page estimate
            "confidence": 0.5
        },
        "text_elements": [],  # Will be filled from PDFText
        "graphics": [],
        "layout_type": "unknown",
        "overall_confidence": 0.5,
        "extraction_quality": "medium",
        "note": "Vision API unavailable, using PDF extraction"
    }
```

---

## DEVELOPMENT ROADMAP

### Phase 1: Core MVP (Weeks 1-2)

**Objective**: Basic PDF → PPTX conversion working end-to-end

- [ ] Setup project structure
- [ ] Implement PDFProcessor (PyMuPDF integration)
- [ ] Implement basic image extraction
- [ ] Implement basic text extraction (PDFText)
- [ ] Implement PowerPointGenerator (python-pptx)
- [ ] Create basic orchestrator
- [ ] Test with 5 NotebookLM PDFs
- [ ] Document API key setup

**Deliverable**: Command-line tool that converts single PDF to PPTX

### Phase 2: Vision Integration (Weeks 3-4)

**Objective**: Add Gemini Vision API for intelligent layout understanding

- [ ] Setup Google Gemini API
- [ ] Implement VisionAnalyzer
- [ ] Build vision prompt engineering
- [ ] Test vision analysis accuracy
- [ ] Implement LayerSeparator (basic)
- [ ] Validate text positioning accuracy
- [ ] Add confidence scoring
- [ ] Test with 20 NotebookLM PDFs

**Deliverable**: Converter with vision-based layout understanding

### Phase 3: Polish & Optimization (Weeks 5-6)

**Objective**: Handle edge cases and improve quality

- [ ] Watermark removal algorithm
- [ ] Text overlap handling
- [ ] Coordinate conversion validation
- [ ] Format preservation (fonts, colors)
- [ ] Error handling & logging
- [ ] Performance optimization
- [ ] Comprehensive testing (50+ PDFs)
- [ ] Create test suite

**Deliverable**: Production-ready converter with quality assurance

### Phase 4: Web Interface (Weeks 7-8)

**Objective**: Make tool accessible via web app

- [ ] Design web UI
- [ ] Build FastAPI backend
- [ ] Implement file upload
- [ ] Add progress tracking
- [ ] Async job processing
- [ ] Download management
- [ ] Error reporting
- [ ] Deploy to cloud

**Deliverable**: Web application for easy access

### Phase 5: Enterprise Features (Future)

- [ ] Batch processing
- [ ] Custom templates
- [ ] Style transfer
- [ ] OCR for image-only content
- [ ] Google Slides export
- [ ] API access
- [ ] Usage analytics
- [ ] Admin dashboard

---

## CODE STRUCTURE

### Project Layout

```
notebooklm-pptx-converter/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration & API keys
│   ├── pdf_processor.py          # PDF extraction
│   ├── vision_analyzer.py        # Gemini Vision API
│   ├── layer_separator.py        # Layer separation logic
│   ├── pptx_generator.py         # PowerPoint generation
│   ├── converter.py              # Main orchestrator
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── coordinates.py        # Coordinate conversion
│   │   ├── image_utils.py        # Image processing
│   │   ├── watermark_removal.py  # Watermark algorithms
│   │   └── validators.py         # Data validation
│   └── models/
│       ├── __init__.py
│       ├── slide_data.py         # Data classes
│       └── extraction_result.py  # Result structures
│
├── tests/
│   ├── __init__.py
│   ├── test_pdf_processor.py
│   ├── test_vision_analyzer.py
│   ├── test_layer_separator.py
│   ├── test_pptx_generator.py
│   └── test_integration.py
│
├── examples/
│   ├── simple_convert.py         # Basic usage example
│   ├── batch_convert.py          # Batch processing
│   └── sample_notebooklm.pdf     # Test PDF
│
├── docs/
│   ├── API.md                    # API documentation
│   ├── ARCHITECTURE.md           # Technical details
│   ├── INSTALLATION.md           # Setup guide
│   ├── TROUBLESHOOTING.md        # Common issues
│   └── DEVELOPMENT.md            # Dev guide
│
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── README.md                     # Project overview
└── LICENSE                       # MIT License

```

### Dependencies

```txt
# Core PDF processing
PyMuPDF>=1.23.0              # fitz - PDF extraction
pdftext>=0.2.0               # Structured text extraction
pypdf>=3.0.0                 # Alternative PDF handling

# Image processing
Pillow>=10.0.0               # Image manipulation
pdf2image>=1.16.0            # PDF to image rendering

# Vision API
google-generativeai>=0.3.0   # Gemini API client

# PowerPoint generation
python-pptx>=0.6.21          # PPTX creation

# Async & utility
asyncio                       # Async operations (built-in)
aiofiles>=23.0.0             # Async file operations
python-dotenv>=1.0.0         # Environment variables

# Logging & monitoring
structlog>=23.0.0            # Structured logging

# Development
pytest>=7.0.0                # Testing
pytest-asyncio>=0.21.0       # Async test support
pytest-cov>=4.0.0            # Coverage reporting
black>=23.0.0                # Code formatting
flake8>=6.0.0                # Linting
mypy>=1.0.0                  # Type checking
```

### Simple Usage Example

```python
# examples/simple_convert.py

import asyncio
from src.converter import NotebookLMToPPTXConverter

async def main():
    # Initialize converter
    converter = NotebookLMToPPTXConverter(
        api_key="your-gemini-api-key-here"
    )
    
    # Convert PDF to PPTX
    await converter.convert(
        pdf_path="path/to/notebooklm_slides.pdf",
        output_path="output/presentation.pptx"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## CRITICAL IMPLEMENTATION NOTES

### 1. Coordinate System Conversion

**Critical**: PDF and PPTX use different coordinate systems!

```python
# utils/coordinates.py

def pdf_to_pptx_coordinates(pdf_bbox, page_height, page_width):
    """
    Convert PDF coordinates to PPTX coordinates
    
    PDF: origin (0,0) at bottom-left, y increases upward
    PPTX: origin (0,0) at top-left, y increases downward
    
    Args:
        pdf_bbox: (x, y, width, height) in PDF points
        page_height: PDF page height in points
    
    Returns:
        PPTX-ready (left, top, width, height) in EMUs
    """
    x, y, w, h = pdf_bbox
    
    # Convert to top-left origin
    pptx_top = page_height - (y + h)
    pptx_left = x
    
    # Convert points to inches
    left_inches = pptx_left / 72.0
    top_inches = pptx_top / 72.0
    width_inches = w / 72.0
    height_inches = h / 72.0
    
    # Convert to EMUs (914400 EMUs per inch)
    left_emu = int(left_inches * 914400)
    top_emu = int(top_inches * 914400)
    width_emu = int(width_inches * 914400)
    height_emu = int(height_inches * 914400)
    
    return (left_emu, top_emu, width_emu, height_emu)
```

### 2. Image Resolution & Quality

```python
# Config recommendations for NotebookLM PDFs

DPI_FOR_VISION = 300          # Vision API analysis
DPI_FOR_EXPORT = 150          # Background image quality
JPEG_QUALITY = 95             # Export quality
PNG_COMPRESSION = 6           # Balance quality/size
```

### 3. Text Positioning Accuracy

- Vision API gives pixel coordinates (for 300 DPI image)
- PDF extraction gives points (1/72 inch)
- Test both independently and validate alignment
- If mismatch >5%: flag for manual review

### 4. Fallback Strategy

Always implement graceful degradation:
```python
1. Try Vision API + PDF extraction (best accuracy)
2. If Vision API fails: use PDF extraction only (medium accuracy)
3. If PDF extraction sparse: add basic layout assumptions (low accuracy)
```

### 5. Testing Strategy

```python
# tests/test_integration.py

@pytest.mark.asyncio
async def test_full_conversion():
    """Test complete conversion pipeline"""
    converter = NotebookLMToPPTXConverter(api_key=test_api_key)
    
    # Convert test PDF
    await converter.convert(
        pdf_path="tests/fixtures/sample_notebooklm.pdf",
        output_path="tests/output/test.pptx"
    )
    
    # Verify output
    assert os.path.exists("tests/output/test.pptx")
    
    # Load and validate PPTX
    prs = Presentation("tests/output/test.pptx")
    assert len(prs.slides) > 0
    
    # Check text editable
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                assert shape.text_frame.text is not None
```

---

## PERFORMANCE TARGETS

| Metric | Target | Notes |
|--------|--------|-------|
| Processing time | <5 sec/slide | Includes Vision API call |
| Memory usage | <500 MB | For 20-slide presentation |
| Output file size | Original ±10% | Optimized images |
| Text accuracy | >99% | OCR quality from NotebookLM |
| Position accuracy | ±2% | Within acceptable tolerance |
| Vision API cost | $0.01-0.05/slide | At current pricing |

---

## NEXT STEPS FOR IMPLEMENTATION

1. **Fork/create repository** with structure above
2. **Setup development environment**:
   ```bash
   python -m venv venv
   pip install -r requirements.txt
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env
   ```

3. **Start with Phase 1**: Core PDF → PPTX
4. **Build test suite** as you implement
5. **Test extensively** with real NotebookLM PDFs
6. **Document** as you code
7. **Plan monetization** strategy

---

## RESEARCH SOURCES & REFERENCES

- **NBLM2PPTX**: https://github.com/laihenyi/NBLM2PPTX (direct competitor)
- **PyMuPDF**: https://pymupdf.io (PDF processing)
- **PDFText**: https://github.com/datalab-to/pdftext (text extraction)
- **python-pptx**: https://python-pptx.readthedocs.io (PPTX generation)
- **Google Gemini**: https://ai.google.dev (Vision API)
- **Docling Parse**: https://github.com/docling-project/docling-parse (alternative parsing)

---

**Document Version**: 1.0  
**Last Updated**: January 17, 2026  
**Status**: Ready for Implementation  
**Confidence Level**: HIGH ✅

This specification provides everything needed for an LLM IDE to develop a production-ready NotebookLM PDF to PowerPoint converter.
