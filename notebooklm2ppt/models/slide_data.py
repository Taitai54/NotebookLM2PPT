"""
Data classes for slide extraction and processing.

These models represent the structured data extracted from PDF slides
and used throughout the conversion pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class TextRole(Enum):
    """Role/type of a text element in a slide."""
    TITLE = "title"
    SUBTITLE = "subtitle"
    BODY = "body"
    CAPTION = "caption"
    LABEL = "label"
    EMPHASIS = "emphasis"
    UNKNOWN = "unknown"


class FontSize(Enum):
    """Relative font size categories."""
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class GraphicType(Enum):
    """Type of graphic element."""
    ICON = "icon"
    DIAGRAM = "diagram"
    CHART = "chart"
    IMAGE = "image"
    DECORATION = "decoration"
    SHAPE = "shape"


class ExtractionQuality(Enum):
    """Quality level of extraction result."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BoundingBox:
    """Bounding box for an element."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def left(self) -> int:
        return self.x
    
    @property
    def top(self) -> int:
        return self.y
    
    @property
    def right(self) -> int:
        return self.x + self.width
    
    @property
    def bottom(self) -> int:
        return self.y + self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)
    
    @classmethod
    def from_tuple(cls, bbox: Tuple[int, int, int, int]) -> "BoundingBox":
        return cls(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])


@dataclass
class TextElement:
    """A text element extracted from a slide."""
    text: str
    bbox: BoundingBox
    role: TextRole = TextRole.BODY
    font_size: FontSize = FontSize.MEDIUM
    font_size_px: int = 20
    confidence: float = 1.0
    font_name: Optional[str] = None
    font_color: Optional[str] = None
    
    @property
    def box(self) -> Tuple[int, int, int, int]:
        """Legacy property for backward compatibility."""
        return self.bbox.as_tuple()


@dataclass
class GraphicElement:
    """A graphic/image element extracted from a slide."""
    bbox: BoundingBox
    graphic_type: GraphicType = GraphicType.IMAGE
    description: str = ""
    confidence: float = 1.0
    path: str = ""
    crop: Optional[any] = None  # numpy array of cropped image
    text_count: int = 0  # number of text elements inside this graphic
    
    @property
    def box(self) -> Tuple[int, int, int, int]:
        """Legacy property for backward compatibility."""
        return self.bbox.as_tuple()


@dataclass
class BackgroundImage:
    """Background image data for a slide."""
    bbox: BoundingBox
    dominant_color: Optional[str] = None
    confidence: float = 1.0
    image_bytes: Optional[bytes] = None
    path: str = ""


@dataclass 
class VisionAnalysisResult:
    """Result from Vision API analysis of a slide."""
    text_elements: List[TextElement] = field(default_factory=list)
    graphics: List[GraphicElement] = field(default_factory=list)
    background: Optional[BackgroundImage] = None
    layout_type: str = "unknown"
    overall_confidence: float = 0.0
    extraction_quality: ExtractionQuality = ExtractionQuality.MEDIUM
    used_vision_api: bool = False
    note: str = ""


@dataclass
class SlideData:
    """Complete data for a single slide, ready for PPTX generation."""
    page_number: int
    width: int
    height: int
    text_blocks: List[TextElement] = field(default_factory=list)
    image_objects: List[GraphicElement] = field(default_factory=list)
    background_path: str = ""
    clean_image: Optional[any] = None  # numpy array
    used_gemini: bool = False
    
    @property
    def text_blocks_legacy(self) -> List[dict]:
        """Convert to legacy dict format for backward compatibility."""
        return [
            {
                "text": t.text,
                "box": t.box,
                "font_size": t.font_size_px,
                "role": t.role.value,
                "score": t.confidence
            }
            for t in self.text_blocks
        ]
    
    @property
    def image_objects_legacy(self) -> List[dict]:
        """Convert to legacy dict format for backward compatibility."""
        return [
            {
                "path": g.path,
                "box": g.box,
                "box_original": g.box,
                "crop": g.crop,
                "id": i,
                "text_count": g.text_count
            }
            for i, g in enumerate(self.image_objects)
        ]


@dataclass
class ExtractionResult:
    """Result from the complete extraction pipeline for a PDF."""
    slides: List[SlideData] = field(default_factory=list)
    total_pages: int = 0
    successful_pages: int = 0
    vision_api_used: int = 0
    fallback_used: int = 0
    errors: List[str] = field(default_factory=list)
