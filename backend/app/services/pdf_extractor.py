"""
PDF text extraction service.

Provides robust PDF text extraction with multiple strategies and fallback mechanisms.
"""

import time
from pathlib import Path
from typing import Union, List, Optional
import fitz  # PyMuPDF
import pdfplumber
from datetime import datetime

from app.schemas.extraction_result import (
    ExtractionResult,
    PageResult,
    ExtractionMetadata,
    ExtractionStatus,
    ExtractionMethod,
    TextBlock,
)
from app.services.pdf_normalizer import PDFNormalizer


class PDFExtractor:
    """
    PDF text extraction service with multi-strategy approach.
    
    Uses PyMuPDF as primary extraction method with pdfplumber as fallback.
    Handles reading order preservation, encoding issues, and error recovery.
    """
    
    def __init__(self):
        """Initialize the PDF extractor."""
        self.normalizer = PDFNormalizer()
    
    def extract_text(self, pdf_path: Union[str, Path]) -> ExtractionResult:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ExtractionResult with extracted text and metadata
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            TypeError: If pdf_path is not a string or Path
        """
        # Validate input type
        if not isinstance(pdf_path, (str, Path)):
            raise TypeError(f"pdf_path must be str or Path, got {type(pdf_path)}")
        
        pdf_path = Path(pdf_path)
        
        # Check file exists
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Start timing
        start_time = time.time()
        
        # Get file size
        file_size = pdf_path.stat().st_size
        
        # Try primary extraction method (PyMuPDF)
        try:
            pages, metadata = self._extract_with_pymupdf(pdf_path)
            extraction_method = ExtractionMethod.PYMUPDF
            fallback_used = False
        except Exception as e:
            # Fallback to pdfplumber
            try:
                pages, metadata = self._extract_with_pdfplumber(pdf_path)
                extraction_method = ExtractionMethod.PDFPLUMBER
                fallback_used = True
                metadata.warnings.append(f"PyMuPDF extraction failed, used pdfplumber: {str(e)}")
            except Exception as e2:
                # Both methods failed
                return self._create_failed_result(pdf_path, file_size, start_time, str(e2))
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Combine all page text
        raw_text = "\n\n".join(page.raw_text for page in pages)
        normalized_text = self.normalizer.normalize_text(raw_text)
        
        # Create complete metadata with all fields
        complete_metadata = ExtractionMetadata(
            total_pages=metadata.total_pages,
            pages_extracted=metadata.pages_extracted,
            pages_failed=metadata.pages_failed,
            extraction_method=extraction_method,
            fallback_used=fallback_used,
            processing_time_ms=processing_time_ms,
            file_size_bytes=file_size,
            warnings=metadata.warnings,
            errors=metadata.errors,
        )
        
        # Determine status
        if complete_metadata.pages_failed == 0:
            status = ExtractionStatus.SUCCESS
        elif complete_metadata.pages_extracted > 0:
            status = ExtractionStatus.PARTIAL
        else:
            status = ExtractionStatus.FAILED
        
        return ExtractionResult(
            status=status,
            text=normalized_text,
            raw_text=raw_text,
            pages=pages,
            metadata=complete_metadata,
            extracted_at=datetime.utcnow(),
        )
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> tuple[List[PageResult], ExtractionMetadata]:
        """
        Extract text using PyMuPDF (fitz).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (page_results, metadata)
        """
        doc = fitz.open(pdf_path)
        pages = []
        warnings = []
        errors = []
        pages_extracted = 0
        pages_failed = 0
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                
                # Extract text with position information
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                
                # Extract text blocks with coordinates
                text_blocks = []
                raw_text_parts = []
                
                for block in blocks:
                    if block.get("type") == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span.get("text", "")
                                if text.strip():
                                    bbox = span.get("bbox", [0, 0, 0, 0])
                                    text_block = TextBlock(
                                        text=text,
                                        page_number=page_num + 1,
                                        x0=bbox[0],
                                        y0=bbox[1],
                                        x1=bbox[2],
                                        y1=bbox[3],
                                        font_name=span.get("font"),
                                        font_size=span.get("size"),
                                    )
                                    text_blocks.append(text_block)
                                    raw_text_parts.append(text)
                
                # Sort text blocks by position (top to bottom, left to right)
                text_blocks.sort(key=lambda b: (-b.y1, b.x0))
                
                # Combine text
                raw_text = " ".join(raw_text_parts)
                normalized_text = self.normalizer.normalize_text(raw_text)
                
                # Count words and characters
                char_count = len(normalized_text)
                word_count = len(normalized_text.split())
                
                # Check for images
                has_images = any(block.get("type") == 1 for block in blocks)
                
                page_result = PageResult(
                    page_number=page_num + 1,
                    text=normalized_text,
                    raw_text=raw_text,
                    text_blocks=text_blocks,
                    char_count=char_count,
                    word_count=word_count,
                    extraction_method=ExtractionMethod.PYMUPDF,
                    has_images=has_images,
                    warnings=[],
                    errors=[],
                )
                
                pages.append(page_result)
                pages_extracted += 1
                
            except Exception as e:
                pages_failed += 1
                errors.append(f"Page {page_num + 1}: {str(e)}")
        
        doc.close()
        
        metadata = ExtractionMetadata(
            total_pages=len(doc),
            pages_extracted=pages_extracted,
            pages_failed=pages_failed,
            extraction_method=ExtractionMethod.PYMUPDF,
            fallback_used=False,
            processing_time_ms=0,  # Will be set later
            file_size_bytes=0,  # Will be set later
            warnings=warnings,
            errors=errors,
        )
        
        return pages, metadata
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> tuple[List[PageResult], ExtractionMetadata]:
        """
        Extract text using pdfplumber (fallback method).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (page_results, metadata)
        """
        pages = []
        warnings = []
        errors = []
        pages_extracted = 0
        pages_failed = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    # Extract text
                    raw_text = page.extract_text() or ""
                    normalized_text = self.normalizer.normalize_text(raw_text)
                    
                    # Count words and characters
                    char_count = len(normalized_text)
                    word_count = len(normalized_text.split())
                    
                    # Extract text with positions (if available)
                    text_blocks = []
                    chars = page.chars
                    if chars:
                        # Group characters into blocks (simplified)
                        for char_data in chars[:100]:  # Limit to first 100 for performance
                            text_block = TextBlock(
                                text=char_data.get("text", ""),
                                page_number=page_num,
                                x0=char_data.get("x0", 0),
                                y0=char_data.get("y0", 0),
                                x1=char_data.get("x1", 0),
                                y1=char_data.get("y1", 0),
                                font_name=char_data.get("fontname"),
                                font_size=char_data.get("size"),
                            )
                            text_blocks.append(text_block)
                    
                    page_result = PageResult(
                        page_number=page_num,
                        text=normalized_text,
                        raw_text=raw_text,
                        text_blocks=text_blocks,
                        char_count=char_count,
                        word_count=word_count,
                        extraction_method=ExtractionMethod.PDFPLUMBER,
                        has_images=False,  # pdfplumber doesn't easily detect images
                        warnings=[],
                        errors=[],
                    )
                    
                    pages.append(page_result)
                    pages_extracted += 1
                    
                except Exception as e:
                    pages_failed += 1
                    errors.append(f"Page {page_num}: {str(e)}")
        
        metadata = ExtractionMetadata(
            total_pages=total_pages,
            pages_extracted=pages_extracted,
            pages_failed=pages_failed,
            extraction_method=ExtractionMethod.PDFPLUMBER,
            fallback_used=False,
            processing_time_ms=0,
            file_size_bytes=0,
            warnings=warnings,
            errors=errors,
        )
        
        return pages, metadata
    
    def _create_failed_result(
        self,
        pdf_path: Path,
        file_size: int,
        start_time: float,
        error_message: str
    ) -> ExtractionResult:
        """
        Create a failed extraction result.
        
        Args:
            pdf_path: Path to PDF file
            file_size: File size in bytes
            start_time: Start time of extraction
            error_message: Error message
            
        Returns:
            ExtractionResult with failed status
        """
        processing_time_ms = (time.time() - start_time) * 1000
        
        metadata = ExtractionMetadata(
            total_pages=0,
            pages_extracted=0,
            pages_failed=0,
            extraction_method=ExtractionMethod.FALLBACK,
            fallback_used=True,
            processing_time_ms=processing_time_ms,
            file_size_bytes=file_size,
            warnings=[],
            errors=[f"Extraction failed: {error_message}"],
        )
        
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            text="",
            raw_text="",
            pages=[],
            metadata=metadata,
            extracted_at=datetime.utcnow(),
        )
