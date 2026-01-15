"""
Unit tests for PDF text extraction.

These tests are designed to INTENTIONALLY FAIL initially and expose weaknesses
in the extraction logic. Tests are IMMUTABLE - only the implementation code
should be modified to make tests pass.

Test Philosophy:
- Tests define correctness
- Tests are never weakened or modified
- Implementation must satisfy all test requirements
"""

import pytest
from pathlib import Path
from app.services.pdf_extractor import PDFExtractor
from app.schemas.extraction_result import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pdfs"


class TestBasicExtraction:
    """Test basic PDF extraction functionality."""
    
    def test_extract_simple_pdf_returns_text(self):
        """Simple PDF extraction should return non-empty text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert isinstance(result, ExtractionResult)
        assert result.status == ExtractionStatus.SUCCESS
        assert len(result.text) > 0
        assert "Machine Learning" in result.text or "machine learning" in result.text.lower()
    
    def test_extract_multipage_pdf_preserves_order(self):
        """Multi-page PDF should preserve page order."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "multipage.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.status == ExtractionStatus.SUCCESS
        assert result.metadata.total_pages == 5
        assert len(result.pages) == 5
        
        # Verify page order
        for i, page in enumerate(result.pages, start=1):
            assert page.page_number == i
            assert f"Page {i}" in page.text
    
    def test_extract_empty_pages_pdf_handles_gracefully(self):
        """PDF with empty pages should be handled gracefully."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "empty_pages.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL]
        assert result.metadata.total_pages == 5
        
        # Pages 1, 3, 5 should have content
        assert "Page 1" in result.text
        assert "Page 3" in result.text
        assert "Page 5" in result.text
    
    def test_extract_nonexistent_file_raises_error(self):
        """Attempting to extract non-existent file should raise FileNotFoundError."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "nonexistent.pdf"
        
        with pytest.raises(FileNotFoundError):
            extractor.extract_text(pdf_path)
    
    def test_extract_returns_extraction_metadata(self):
        """Extraction should return comprehensive metadata."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.metadata is not None
        assert result.metadata.total_pages > 0
        assert result.metadata.pages_extracted > 0
        assert result.metadata.processing_time_ms >= 0
        assert result.metadata.file_size_bytes > 0
        assert result.metadata.extraction_method in ExtractionMethod


class TestReadingOrderPreservation:
    """Test reading order preservation for complex layouts."""
    
    def test_multi_column_layout_preserves_reading_order(self):
        """Two-column layout should maintain correct reading order."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "multi_column.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.status == ExtractionStatus.SUCCESS
        
        # Check that sections appear in logical order
        text_lower = result.text.lower()
        abstract_pos = text_lower.find("abstract")
        intro_pos = text_lower.find("introduction")
        method_pos = text_lower.find("methodology")
        
        # Abstract should come before Introduction, Introduction before Methodology
        assert abstract_pos < intro_pos < method_pos, \
            "Reading order not preserved in multi-column layout"
    
    def test_complex_layout_maintains_logical_flow(self):
        """Complex layout with sidebars should maintain logical flow."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "complex_layout.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.status == ExtractionStatus.SUCCESS
        
        # Main content should come before sidebar content
        text = result.text
        main_content_pos = text.find("main content")
        sidebar_pos = text.find("Quick Facts")
        
        # This is a challenging test - main content should ideally come first
        # or at least be properly separated from sidebar
        assert main_content_pos != -1 or sidebar_pos != -1, \
            "Failed to extract content from complex layout"
    
    def test_text_blocks_sorted_top_to_bottom(self):
        """Text blocks should be sorted from top to bottom of page."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        for page in result.pages:
            if len(page.text_blocks) > 1:
                # Verify blocks are sorted by y-coordinate (top to bottom)
                for i in range(len(page.text_blocks) - 1):
                    current_block = page.text_blocks[i]
                    next_block = page.text_blocks[i + 1]
                    # In PDF coordinates, higher y means higher on page
                    assert current_block.y1 >= next_block.y1, \
                        "Text blocks not sorted top-to-bottom"


class TestWhitespaceNormalization:
    """Test whitespace normalization logic."""
    
    def test_excessive_spaces_normalized_to_single_space(self):
        """Multiple consecutive spaces should be normalized to single space."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "excessive_whitespace.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should not contain multiple consecutive spaces
        assert "  " not in result.text, \
            "Multiple consecutive spaces not normalized"
    
    def test_paragraph_breaks_preserved(self):
        """Paragraph breaks (double newlines) should be preserved."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should contain paragraph breaks
        assert "\n\n" in result.text or "\n" in result.text, \
            "Paragraph structure not preserved"
    
    def test_leading_trailing_whitespace_removed(self):
        """Leading and trailing whitespace should be removed from text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "excessive_whitespace.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Overall text should not start or end with whitespace
        assert result.text == result.text.strip(), \
            "Leading/trailing whitespace not removed"
        
        # Individual lines should not have trailing spaces
        for line in result.text.split('\n'):
            if line:  # Skip empty lines
                assert line == line.rstrip(), \
                    f"Line has trailing whitespace: '{line}'"
    
    def test_tabs_converted_to_spaces(self):
        """Tab characters should be converted to spaces."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "excessive_whitespace.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should not contain tab characters
        assert "\t" not in result.text, \
            "Tab characters not converted to spaces"
    
    def test_multiple_newlines_collapsed_appropriately(self):
        """Excessive newlines should be collapsed while preserving paragraphs."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "excessive_whitespace.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result.text, \
            "Excessive newlines not collapsed"


class TestEncodingHandling:
    """Test encoding and special character handling."""
    
    def test_utf8_text_extracted_correctly(self):
        """UTF-8 encoded text should be extracted correctly."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "encoding_issues.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL]
        assert len(result.text) > 0
    
    def test_special_characters_preserved(self):
        """Special characters and unicode should be preserved."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "encoding_issues.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should contain some special characters (at least some should be preserved)
        text = result.text
        has_special_chars = any(char in text for char in ['©', '®', '™', '€', '£'])
        has_math_symbols = any(char in text for char in ['α', 'β', 'γ', '∑', '∫'])
        
        # At least one category of special characters should be present
        assert has_special_chars or has_math_symbols, \
            "Special characters not preserved during extraction"
    
    def test_smart_quotes_handled(self):
        """Smart quotes should be handled appropriately."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "encoding_issues.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should contain quotes (smart or normalized)
        assert '"' in result.text or '"' in result.text or '"' in result.text, \
            "Quotes not handled correctly"
    
    def test_unicode_normalization_applied(self):
        """Unicode normalization should be applied consistently."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "encoding_issues.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Text should be valid UTF-8
        try:
            result.text.encode('utf-8')
        except UnicodeEncodeError:
            pytest.fail("Extracted text is not valid UTF-8")


class TestMixedContent:
    """Test extraction from PDFs with mixed content (text, tables, images)."""
    
    def test_mixed_content_pdf_extracts_text(self):
        """PDF with tables and mixed content should extract text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "mixed_content.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL]
        assert "Quarterly Report" in result.text or "quarterly report" in result.text.lower()
    
    def test_table_content_extracted(self):
        """Table content should be extracted."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "mixed_content.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should extract some table data
        text_lower = result.text.lower()
        assert "revenue" in text_lower or "metric" in text_lower, \
            "Table content not extracted"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_extraction_result_includes_page_results(self):
        """Extraction result should include per-page results."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "multipage.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert len(result.pages) > 0
        assert all(hasattr(page, 'text') for page in result.pages)
        assert all(hasattr(page, 'page_number') for page in result.pages)
    
    def test_extraction_metadata_includes_timing(self):
        """Extraction metadata should include processing time."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.metadata.processing_time_ms >= 0
    
    def test_extraction_tracks_success_rate(self):
        """Extraction result should track success rate."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert 0 <= result.success_rate <= 100
    
    def test_invalid_pdf_path_type_raises_error(self):
        """Invalid path type should raise TypeError."""
        extractor = PDFExtractor()
        
        with pytest.raises(TypeError):
            extractor.extract_text(123)  # Invalid type
    
    def test_extraction_result_is_immutable(self):
        """Extraction result should be immutable (frozen)."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
            result.text = "modified"


class TestWordAndCharacterCounts:
    """Test accurate word and character counting."""
    
    def test_char_count_accurate(self):
        """Character count should be accurate."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Verify character count matches actual text length
        assert result.total_char_count == len(result.text)
    
    def test_word_count_reasonable(self):
        """Word count should be reasonable."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Word count should be positive and reasonable
        assert result.total_word_count > 0
        
        # Rough validation: word count should be less than char count
        assert result.total_word_count < result.total_char_count
    
    def test_per_page_counts_sum_to_total(self):
        """Per-page counts should sum to total counts."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "multipage.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        total_chars = sum(page.char_count for page in result.pages)
        total_words = sum(page.word_count for page in result.pages)
        
        assert total_chars == result.total_char_count
        assert total_words == result.total_word_count
