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


class CleaningOptions(BaseModel):
    """Configuration options for text cleaning."""
    
    model_config = ConfigDict(frozen=True)
    
    remove_headers_footers: bool = Field(default=True, description="Remove detected headers and footers")
    remove_page_numbers: bool = Field(default=True, description="Remove page numbers")
    remove_repeated_artifacts: bool = Field(default=True, description="Remove repeated artifacts like watermarks")
    clean_formatting: bool = Field(default=True, description="Clean formatting remnants")
    header_footer_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Threshold for header/footer detection")
    artifact_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Threshold for repeated artifact detection")


class CleaningMetadata(BaseModel):
    """Metadata about text cleaning operations."""
    
    model_config = ConfigDict(frozen=True)
    
    headers_removed: List[str] = Field(default_factory=list, description="List of removed headers")
    footers_removed: List[str] = Field(default_factory=list, description="List of removed footers")
    page_numbers_removed: List[str] = Field(default_factory=list, description="List of removed page numbers")
    artifacts_removed: List[str] = Field(default_factory=list, description="List of removed repeated artifacts")
    formatting_cleaned: bool = Field(default=False, description="Whether formatting was cleaned")
    total_removals: int = Field(default=0, ge=0, description="Total number of text removals")


class SegmentationOptions(BaseModel):
    """Configuration options for text segmentation."""
    
    model_config = ConfigDict(frozen=True)
    
    chunk_size_tokens: int = Field(default=256, ge=50, le=1024, description="Target chunk size in tokens")
    overlap_percentage: float = Field(default=0.2, ge=0.0, le=0.5, description="Overlap between chunks (0.0-0.5)")
    min_chunk_size: int = Field(default=50, ge=10, description="Minimum chunk size in tokens")
    max_chunk_size: int = Field(default=512, ge=100, description="Maximum chunk size in tokens")
    prefer_semantic_boundaries: bool = Field(default=True, description="Prefer paragraph/section breaks")
    sentence_segmentation_model: str = Field(default="en_core_web_sm", description="spaCy model for sentence segmentation")


class TextSegment(BaseModel):
    """Individual text segment/chunk."""
    
    model_config = ConfigDict(frozen=True)
    
    segment_id: str = Field(..., description="Unique segment identifier")
    text: str = Field(..., description="Segment text content")
    start_char: int = Field(..., ge=0, description="Character offset in source text")
    end_char: int = Field(..., ge=0, description="Character offset end in source text")
    token_count: int = Field(..., ge=0, description="Estimated token count")
    sentence_count: int = Field(..., ge=0, description="Number of sentences in segment")
    has_semantic_boundary: bool = Field(default=False, description="Whether segment ends at semantic boundary")
    overlap_with_previous: Optional[str] = Field(default=None, description="Overlap text with previous segment")
    overlap_with_next: Optional[str] = Field(default=None, description="Overlap text with next segment")


class SegmentationMetadata(BaseModel):
    """Metadata about segmentation process."""
    
    model_config = ConfigDict(frozen=True)
    
    total_segments: int = Field(..., ge=0, description="Total number of segments created")
    total_sentences: int = Field(..., ge=0, description="Total sentences across all segments")
    avg_segment_size: float = Field(..., ge=0.0, description="Average segment size in tokens")
    min_segment_size: int = Field(..., ge=0, description="Minimum segment size in tokens")
    max_segment_size: int = Field(..., ge=0, description="Maximum segment size in tokens")
    semantic_boundaries_used: int = Field(..., ge=0, description="Number of semantic boundaries respected")
    segmentation_time_ms: float = Field(..., ge=0.0, description="Processing time in milliseconds")


class SegmentationResult(BaseModel):
    """Complete segmentation result."""
    
    model_config = ConfigDict(frozen=True)
    
    segments: List[TextSegment] = Field(default_factory=list, description="List of text segments")
    metadata: SegmentationMetadata = Field(..., description="Segmentation metadata")
    source_text_length: int = Field(..., ge=0, description="Original text length in characters")
    segmented_at: datetime = Field(default_factory=datetime.utcnow, description="Segmentation timestamp")


class ExtractionResult(BaseModel):
    """Complete PDF extraction result."""
    
    model_config = ConfigDict(frozen=True)
    
    status: ExtractionStatus = Field(..., description="Overall extraction status")
    text: str = Field(..., description="Complete extracted and normalized text")
    raw_text: str = Field(..., description="Complete raw text before normalization")
    pages: List[PageResult] = Field(default_factory=list, description="Per-page results")
    metadata: ExtractionMetadata = Field(..., description="Extraction metadata")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    cleaning_metadata: Optional[CleaningMetadata] = Field(default=None, description="Text cleaning metadata")
    
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
