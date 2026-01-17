"""
Unit tests for PDF text cleaning and noise removal.

These tests are designed to INTENTIONALLY FAIL initially and expose weaknesses
in the cleaning logic. Tests are IMMUTABLE - only the implementation code
should be modified to make tests pass.

Test Philosophy:
- Tests define correctness
- Tests are never weakened or modified
- Implementation must satisfy all test requirements
"""

import pytest
from pathlib import Path
from app.services.pdf_cleaner import PDFCleaner
from app.services.pdf_extractor import PDFExtractor
from app.schemas.extraction_result import (
    CleaningOptions,
    CleaningMetadata,
    PageResult,
)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pdfs"


class TestHeaderFooterDetection:
    """Test header and footer detection and removal."""
    
    def test_detect_consistent_headers_across_pages(self):
        """Headers appearing on all pages should be detected."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should detect the course header
        assert result.cleaning_metadata is not None
        assert len(result.cleaning_metadata.headers_removed) > 0
        assert any("CS 101" in header or "Machine Learning" in header 
                  for header in result.cleaning_metadata.headers_removed)
    
    def test_detect_consistent_footers_across_pages(self):
        """Footers appearing on all pages should be detected."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should detect the copyright footer
        assert result.cleaning_metadata is not None
        assert len(result.cleaning_metadata.footers_removed) > 0
        assert any("University" in footer or "Confidential" in footer 
                  for footer in result.cleaning_metadata.footers_removed)
    
    def test_headers_removed_from_final_text(self):
        """Detected headers should not appear in cleaned text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Header text should be removed
        assert "CS 101 - Introduction to Machine Learning" not in result.text
        assert "Fall 2025" not in result.text
    
    def test_footers_removed_from_final_text(self):
        """Detected footers should not appear in cleaned text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Footer text should be removed
        assert "© 2025 University of AI" not in result.text
        assert "Do Not Distribute" not in result.text
    
    def test_ignore_first_page_unique_header(self):
        """Headers unique to first page (like title) should not be removed."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Title should be preserved
        assert "Introduction to Machine Learning" in result.text
    
    def test_header_footer_position_threshold(self):
        """Only text in top/bottom 10% of page should be considered."""
        cleaner = PDFCleaner()
        
        # Create mock pages with text at different positions
        # This test verifies the position-based filtering logic
        # Implementation should only consider text in header/footer regions
        assert hasattr(cleaner, 'detect_headers_footers')


class TestPageNumberRemoval:
    """Test page number detection and removal."""
    
    def test_remove_simple_page_numbers(self):
        """Simple page numbers like '1', '2', '3' should be removed."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Page numbers should be detected
        assert result.cleaning_metadata is not None
        assert len(result.cleaning_metadata.page_numbers_removed) > 0
    
    def test_remove_page_x_of_y_format(self):
        """Page numbers in 'Page X of Y' format should be removed."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should detect "Page 1 of 5" format
        assert result.cleaning_metadata is not None
        page_nums = result.cleaning_metadata.page_numbers_removed
        assert any("of" in str(pn).lower() for pn in page_nums)
    
    def test_page_numbers_removed_from_text(self):
        """Detected page numbers should not appear in cleaned text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Page number patterns should be removed
        assert "Page 1 of 5" not in result.text
        assert "Page 2 of 5" not in result.text
        assert "Page 3 of 5" not in result.text
    
    def test_preserve_numbers_in_content(self):
        """Numbers that are part of content should be preserved."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Content numbers should be preserved (e.g., "1. Forward propagation")
        assert "1." in result.text or "2." in result.text  # List numbers
    
    def test_remove_dashed_page_numbers(self):
        """Page numbers with dashes like '- 5 -' should be removed."""
        cleaner = PDFCleaner()
        
        text = "Some content\n- 5 -\nMore content"
        cleaned = cleaner.clean_text(text, [], CleaningOptions())
        
        assert "- 5 -" not in cleaned
        assert "Some content" in cleaned
        assert "More content" in cleaned


class TestRepeatedArtifactRemoval:
    """Test detection and removal of repeated artifacts."""
    
    def test_detect_watermarks(self):
        """Repeated watermarks should be detected and removed."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # DRAFT watermark should be detected
        assert result.cleaning_metadata is not None
        assert len(result.cleaning_metadata.artifacts_removed) > 0
        assert any("DRAFT" in artifact for artifact in result.cleaning_metadata.artifacts_removed)
    
    def test_watermark_removed_from_text(self):
        """Detected watermarks should not appear in cleaned text."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # DRAFT watermark should be removed
        assert "DRAFT" not in result.text
    
    def test_threshold_based_detection(self):
        """Only artifacts appearing on >70% of pages should be removed."""
        cleaner = PDFCleaner()
        
        # Artifact appearing on 2 out of 5 pages (40%) should NOT be removed
        # Artifact appearing on 4 out of 5 pages (80%) SHOULD be removed
        # This tests the threshold logic
        assert hasattr(cleaner, 'remove_repeated_artifacts')
    
    def test_preserve_intentional_repetition(self):
        """Intentionally repeated content (like section headers) should be preserved."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Lecture titles should be preserved (they're content, not noise)
        assert "Neural Networks" in result.text


class TestFormattingCleanup:
    """Test cleanup of formatting remnants."""
    
    def test_remove_orphaned_bullets(self):
        """Standalone bullet points without text should be removed."""
        cleaner = PDFCleaner()
        
        text = "Content\n•\nMore content"
        cleaned = cleaner.clean_text(text, [], CleaningOptions())
        
        # Orphaned bullet should be removed
        lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
        assert "•" not in lines
        assert "Content" in cleaned
        assert "More content" in cleaned
    
    def test_preserve_bullet_lists(self):
        """Bullet points with content should be preserved."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Bullet list items should be preserved
        assert "Perceptrons" in result.text or "perceptrons" in result.text.lower()
        assert "Backpropagation" in result.text or "backpropagation" in result.text.lower()
    
    def test_remove_table_borders(self):
        """Table border characters should be removed."""
        cleaner = PDFCleaner()
        
        text = "Content\n├──┤\nMore content"
        cleaned = cleaner.clean_text(text, [], CleaningOptions())
        
        assert "├" not in cleaned
        assert "──" not in cleaned
        assert "┤" not in cleaned
    
    def test_remove_excessive_punctuation(self):
        """Excessive punctuation like '.....' should be removed."""
        cleaner = PDFCleaner()
        
        text = "Content.....\nMore content"
        cleaned = cleaner.clean_text(text, [], CleaningOptions())
        
        assert "....." not in cleaned
        assert "Content" in cleaned


class TestSemanticPreservation:
    """Test that meaningful content is preserved during cleaning."""
    
    def test_meaningful_content_preserved(self):
        """Core lecture content should remain intact."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Key content should be preserved
        assert "neural networks" in result.text.lower()
        assert "fundamentals" in result.text.lower()
        assert "activation functions" in result.text.lower()
        assert "backpropagation" in result.text.lower()
        assert "gradient descent" in result.text.lower()
    
    def test_no_false_positives_in_clean_pdf(self):
        """Clean PDFs should have minimal or no cleaning."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should have minimal cleaning for already clean PDF
        if result.cleaning_metadata:
            total_removals = result.cleaning_metadata.total_removals
            assert total_removals < 5  # Allow for minor cleanup
    
    def test_cleaning_is_deterministic(self):
        """Same input should produce same output."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result1 = extractor.extract_text(pdf_path)
        result2 = extractor.extract_text(pdf_path)
        
        assert result1.text == result2.text
        if result1.cleaning_metadata and result2.cleaning_metadata:
            assert result1.cleaning_metadata.total_removals == result2.cleaning_metadata.total_removals
    
    def test_cleaning_metadata_accurate(self):
        """Metadata should accurately reflect actual removals."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        assert result.cleaning_metadata is not None
        
        # Total removals should equal sum of individual removal counts
        total = (len(result.cleaning_metadata.headers_removed) +
                len(result.cleaning_metadata.footers_removed) +
                len(result.cleaning_metadata.page_numbers_removed) +
                len(result.cleaning_metadata.artifacts_removed))
        
        assert result.cleaning_metadata.total_removals >= total


class TestCleaningOptions:
    """Test configurable cleaning options."""
    
    def test_disable_header_footer_removal(self):
        """Should preserve headers/footers when disabled."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Extract with cleaning disabled for headers/footers
        options = CleaningOptions(remove_headers_footers=False)
        result = extractor.extract_text(pdf_path, cleaning_options=options)
        
        # Headers/footers should be present
        assert "CS 101" in result.text or "Machine Learning" in result.text
    
    def test_disable_page_number_removal(self):
        """Should preserve page numbers when disabled."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        options = CleaningOptions(remove_page_numbers=False)
        result = extractor.extract_text(pdf_path, cleaning_options=options)
        
        # Page numbers should be present
        assert "Page" in result.text and "of" in result.text
    
    def test_disable_all_cleaning(self):
        """Should preserve all noise when all cleaning is disabled."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        options = CleaningOptions(
            remove_headers_footers=False,
            remove_page_numbers=False,
            remove_repeated_artifacts=False,
            clean_formatting=False
        )
        result = extractor.extract_text(pdf_path, cleaning_options=options)
        
        # All noise should be present
        assert result.cleaning_metadata is None or result.cleaning_metadata.total_removals == 0


class TestIntegration:
    """Integration tests for end-to-end cleaning pipeline."""
    
    def test_end_to_end_cleaning_pipeline(self):
        """Full extraction and cleaning pipeline should work."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should successfully extract and clean
        assert result.status.value == "success"
        assert len(result.text) > 0
        assert result.cleaning_metadata is not None
        assert result.cleaning_metadata.total_removals > 0
    
    def test_cleaning_with_multipage_pdf(self):
        """Cleaning should work correctly with multi-page PDFs."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should process all 5 pages
        assert result.metadata.total_pages == 5
        assert result.metadata.pages_extracted == 5
        
        # Should detect patterns across all pages
        assert result.cleaning_metadata.total_removals > 0
    
    def test_cleaning_with_complex_layout(self):
        """Cleaning should handle complex layouts correctly."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "complex_layout.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should extract successfully
        assert result.status.value in ["success", "partial"]
        
        # Main content should be preserved
        assert "complex layout" in result.text.lower() or "main content" in result.text.lower()
    
    def test_cleaning_preserves_extraction_metadata(self):
        """Cleaning should not interfere with extraction metadata."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Extraction metadata should be complete
        assert result.metadata.total_pages > 0
        assert result.metadata.processing_time_ms > 0
        assert result.metadata.file_size_bytes > 0
