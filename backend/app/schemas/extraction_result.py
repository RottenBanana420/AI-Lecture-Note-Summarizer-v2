"""
Pydantic schemas for PDF extraction results.

These schemas define the structure of data returned by the PDF extraction service.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ExtractionStatus(str, Enum):
    """Status of PDF extraction."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ExtractionMethod(str, Enum):
    """Method used for extraction."""
    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"
    OCR = "ocr"
    FALLBACK = "fallback"


class TextBlock(BaseModel):
    """A positioned block of text extracted from a PDF."""
    
    model_config = ConfigDict(frozen=True)
    
    text: str = Field(..., description="The extracted text content")
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    x0: float = Field(..., description="Left x-coordinate")
    y0: float = Field(..., description="Bottom y-coordinate")
    x1: float = Field(..., description="Right x-coordinate")
    y1: float = Field(..., description="Top y-coordinate")
    font_name: Optional[str] = Field(None, description="Font name if available")
    font_size: Optional[float] = Field(None, description="Font size if available")


class PageResult(BaseModel):
    """Extraction result for a single page."""
    
    model_config = ConfigDict(frozen=True)
    
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    text: str = Field(..., description="Extracted and normalized text")
    raw_text: str = Field(..., description="Raw extracted text before normalization")
    text_blocks: List[TextBlock] = Field(default_factory=list, description="Individual text blocks")
    char_count: int = Field(..., ge=0, description="Character count")
    word_count: int = Field(..., ge=0, description="Word count")
    extraction_method: ExtractionMethod = Field(..., description="Method used for extraction")
    has_images: bool = Field(default=False, description="Whether page contains images")
    warnings: List[str] = Field(default_factory=list, description="Extraction warnings")
    errors: List[str] = Field(default_factory=list, description="Extraction errors")


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""
    
    model_config = ConfigDict(frozen=True)
    
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    pages_extracted: int = Field(..., ge=0, description="Number of pages successfully extracted")
    pages_failed: int = Field(..., ge=0, description="Number of pages that failed extraction")
    extraction_method: ExtractionMethod = Field(..., description="Primary extraction method used")
    fallback_used: bool = Field(default=False, description="Whether fallback method was used")
    processing_time_ms: float = Field(..., ge=0, description="Total processing time in milliseconds")
    file_size_bytes: int = Field(..., ge=0, description="Original file size")
    warnings: List[str] = Field(default_factory=list, description="Global warnings")
    errors: List[str] = Field(default_factory=list, description="Global errors")


class ExtractionResult(BaseModel):
    """Complete PDF extraction result."""
    
    model_config = ConfigDict(frozen=True)
    
    status: ExtractionStatus = Field(..., description="Overall extraction status")
    text: str = Field(..., description="Complete extracted and normalized text")
    raw_text: str = Field(..., description="Complete raw text before normalization")
    pages: List[PageResult] = Field(default_factory=list, description="Per-page results")
    metadata: ExtractionMetadata = Field(..., description="Extraction metadata")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    
    @property
    def total_char_count(self) -> int:
        """Total character count across all pages."""
        return sum(page.char_count for page in self.pages)
    
    @property
    def total_word_count(self) -> int:
        """Total word count across all pages."""
        return sum(page.word_count for page in self.pages)
    
    @property
    def success_rate(self) -> float:
        """Percentage of pages successfully extracted."""
        if self.metadata.total_pages == 0:
            return 0.0
        return (self.metadata.pages_extracted / self.metadata.total_pages) * 100
