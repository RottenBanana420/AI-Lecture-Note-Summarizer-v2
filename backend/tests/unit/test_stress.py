"""
Stress tests for PDF processing pipeline.

These tests are designed to INTENTIONALLY PUSH the pipeline beyond normal limits
and expose edge cases. Tests are IMMUTABLE - only the implementation code
should be modified to make tests pass.

Test Philosophy:
- Tests define robustness requirements
- Tests are never weakened or modified
- Implementation must handle extreme scenarios gracefully
"""

import pytest
import gc
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from app.services.pdf_extractor import PDFExtractor
from app.services.pdf_segmenter import PDFSegmenter
from app.services.pdf_cleaner import PDFCleaner
from app.schemas.extraction_result import CleaningOptions, SegmentationOptions

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pdfs"


class TestLargeDocuments:
    """Test handling of very large documents."""
    
    def test_multipage_pdf_extraction(self):
        """Should handle multi-page PDFs efficiently."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"  # 5 pages
        
        result = extractor.extract_text(pdf_path)
        
        # Should extract all pages successfully
        assert result.status.value == "success"
        assert result.metadata.total_pages == 5
        assert result.metadata.pages_extracted == 5
        assert result.metadata.pages_failed == 0
    
    def test_complex_layout_pdf(self):
        """Should handle complex layouts without excessive time."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "complex_layout.pdf"
        
        import time
        start = time.time()
        result = extractor.extract_text(pdf_path)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (<5s for complex layout)
        assert elapsed < 5.0, f"Complex layout took {elapsed:.2f}s, expected <5s"
        assert result.status.value in ["success", "partial"]
    
    def test_multi_column_pdf(self):
        """Should handle multi-column layouts."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "multi_column.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should extract text (reading order may vary)
        assert result.status.value in ["success", "partial"]
        assert len(result.text) > 0
    
    def test_large_text_segmentation(self):
        """Should segment very long text efficiently."""
        segmenter = PDFSegmenter()
        
        # Create very long text (simulate 50-page document)
        text = " ".join([f"This is sentence number {i}." for i in range(1000)])
        
        import time
        start = time.time()
        result = segmenter.segment_text(text)
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 10.0, f"Segmentation took {elapsed:.2f}s for 1000 sentences, expected <10s"
        assert result.metadata.total_segments > 0
        assert result.metadata.total_sentences == 1000
    
    def test_very_long_single_sentence(self):
        """Should handle extremely long single sentences."""
        segmenter = PDFSegmenter()
        
        # Create a very long sentence (10,000 words)
        text = " ".join(["word"] * 10000) + "."
        
        result = segmenter.segment_text(text)
        
        # Should create segments even for very long sentence
        assert result.metadata.total_segments >= 1
        # Should not crash or hang


class TestErrorIsolation:
    """Test failure isolation and error handling."""
    
    def test_corrupted_pdf_doesnt_crash_pipeline(self):
        """Corrupted PDF should fail gracefully without crashing."""
        extractor = PDFExtractor()
        
        # Try to extract from a non-PDF file
        try:
            result = extractor.extract_text(__file__)  # Python file, not PDF
            # Should either fail gracefully or return failed status
            assert result.status.value == "failed"
        except Exception as e:
            # Should raise a specific exception, not crash
            assert isinstance(e, (FileNotFoundError, TypeError, ValueError))
    
    def test_missing_file_error_handling(self):
        """Missing file should raise appropriate error."""
        extractor = PDFExtractor()
        
        with pytest.raises(FileNotFoundError):
            extractor.extract_text(FIXTURES_DIR / "nonexistent.pdf")
    
    def test_empty_pdf_handling(self):
        """Empty PDF should be handled gracefully."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "empty_pages.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should complete without crashing
        assert result.status.value in ["success", "partial"]
        # May have empty text, but should not crash
    
    def test_one_document_failure_doesnt_affect_others(self):
        """Failure in one document should not affect processing of others."""
        extractor = PDFExtractor()
        
        valid_pdf = FIXTURES_DIR / "clean_simple.pdf"
        invalid_pdf = FIXTURES_DIR / "nonexistent.pdf"
        
        # Process valid PDF
        result1 = extractor.extract_text(valid_pdf)
        assert result1.status.value == "success"
        
        # Try invalid PDF (should fail)
        try:
            extractor.extract_text(invalid_pdf)
        except FileNotFoundError:
            pass  # Expected
        
        # Process valid PDF again (should still work)
        result2 = extractor.extract_text(valid_pdf)
        assert result2.status.value == "success"
        assert result2.text == result1.text  # Should produce same result
    
    def test_partial_extraction_on_page_failure(self):
        """Should continue extraction even if some pages fail."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should extract successfully or partially
        assert result.status.value in ["success", "partial"]
        # Should have extracted at least some pages
        assert result.metadata.pages_extracted > 0


class TestMemoryPressure:
    """Test memory stress scenarios."""
    
    def test_sequential_large_pdf_processing(self):
        """Should handle multiple large PDFs sequentially without memory issues."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Process 10 times sequentially
        for i in range(10):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success", f"Failed on iteration {i+1}"
            
            # Force garbage collection between iterations
            gc.collect()
        
        # Should complete all iterations without memory errors
    
    def test_memory_released_between_documents(self):
        """Memory should be released between document processing."""
        import psutil
        process = psutil.Process(os.getpid())
        
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Get baseline memory
        gc.collect()
        mem_baseline = process.memory_info().rss / 1024 / 1024
        
        # Process multiple documents
        for _ in range(5):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
            gc.collect()
        
        # Check memory after processing
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_growth = mem_after - mem_baseline
        
        # Memory should not grow excessively (allow 50MB for caches)
        assert mem_growth < 50, f"Memory grew by {mem_growth:.1f}MB, expected <50MB"
    
    def test_concurrent_large_pdf_processing(self):
        """Should handle concurrent processing of large PDFs."""
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        def extract_pdf():
            extractor = PDFExtractor()
            return extractor.extract_text(pdf_path)
        
        # Process 5 PDFs concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(extract_pdf) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result.status.value == "success"
    
    def test_segmentation_memory_efficiency(self):
        """Segmentation should not use excessive memory."""
        import psutil
        process = psutil.Process(os.getpid())
        
        segmenter = PDFSegmenter()
        
        # Create large text
        text = " ".join([f"Sentence {i}." for i in range(5000)])
        
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024
        
        result = segmenter.segment_text(text)
        
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_used = mem_after - mem_before
        
        # Should segment successfully
        assert result.metadata.total_sentences == 5000
        
        # Should not use excessive memory (<400MB for 5000 sentences including spaCy model)
        # spaCy model itself takes ~150MB, plus processing overhead for large text (~200MB)
        assert mem_used < 400, f"Used {mem_used:.1f}MB for segmentation, expected <400MB"


class TestEdgeCases:
    """Test extreme edge cases."""
    
    def test_pdf_with_only_images(self):
        """PDF with only images should not crash."""
        extractor = PDFExtractor()
        # Use a PDF that might have minimal text
        pdf_path = FIXTURES_DIR / "empty_pages.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should complete without crashing
        assert result.status.value in ["success", "partial", "failed"]
        # Text may be empty, but should not crash
    
    def test_empty_text_segmentation(self):
        """Empty text should be handled gracefully."""
        segmenter = PDFSegmenter()
        
        result = segmenter.segment_text("")
        
        # Should return empty result, not crash
        assert result.metadata.total_segments == 0
        assert len(result.segments) == 0
    
    def test_whitespace_only_text(self):
        """Whitespace-only text should be handled."""
        segmenter = PDFSegmenter()
        
        result = segmenter.segment_text("   \n\n   \t\t   ")
        
        # Should return empty result
        assert result.metadata.total_segments == 0
    
    def test_special_characters_in_text(self):
        """Text with special characters should be processed correctly."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "encoding_issues.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should handle encoding issues gracefully
        assert result.status.value in ["success", "partial"]
    
    def test_mixed_content_pdf(self):
        """PDF with mixed content (text, images, tables) should be processed."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "mixed_content.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should extract text content
        assert result.status.value in ["success", "partial"]
        assert len(result.text) > 0
    
    def test_excessive_whitespace_handling(self):
        """PDF with excessive whitespace should be normalized."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "excessive_whitespace.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should normalize whitespace
        assert result.status.value == "success"
        # Should not have excessive consecutive spaces
        assert "    " not in result.text  # No 4+ consecutive spaces
    
    def test_very_small_text_blocks(self):
        """Should handle PDFs with many small text blocks."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "complex_layout.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        # Should process all text blocks
        assert result.status.value in ["success", "partial"]
        total_blocks = sum(len(page.text_blocks) for page in result.pages)
        assert total_blocks > 0


class TestRobustness:
    """Test overall system robustness."""
    
    def test_repeated_processing_stability(self):
        """System should remain stable over repeated processing."""
        extractor = PDFExtractor()
        segmenter = PDFSegmenter()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Process 50 times
        for i in range(50):
            # Extract
            extraction_result = extractor.extract_text(pdf_path)
            assert extraction_result.status.value == "success", f"Extraction failed on iteration {i+1}"
            
            # Segment
            segmentation_result = segmenter.segment_text(extraction_result.text)
            assert segmentation_result.metadata.total_segments > 0, f"Segmentation failed on iteration {i+1}"
        
        # Should complete all iterations without degradation
    
    def test_error_recovery(self):
        """System should recover from errors and continue processing."""
        extractor = PDFExtractor()
        
        valid_pdf = FIXTURES_DIR / "clean_simple.pdf"
        
        # Process valid PDF
        result1 = extractor.extract_text(valid_pdf)
        assert result1.status.value == "success"
        
        # Try to process invalid input (should error)
        try:
            extractor.extract_text(FIXTURES_DIR / "nonexistent.pdf")
        except FileNotFoundError:
            pass
        
        # Try another invalid input
        try:
            extractor.extract_text(__file__)  # Python file
        except Exception:
            pass
        
        # Should still process valid PDF correctly
        result2 = extractor.extract_text(valid_pdf)
        assert result2.status.value == "success"
        assert result2.text == result1.text
    
    def test_concurrent_mixed_workload(self):
        """Should handle concurrent mix of different PDF types."""
        pdfs = [
            FIXTURES_DIR / "clean_simple.pdf",
            FIXTURES_DIR / "pdf_with_noise.pdf",
            FIXTURES_DIR / "complex_layout.pdf",
            FIXTURES_DIR / "multi_column.pdf",
            FIXTURES_DIR / "mixed_content.pdf",
        ]
        
        def extract_pdf(pdf_path):
            extractor = PDFExtractor()
            return extractor.extract_text(pdf_path)
        
        # Process all concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(extract_pdf, pdf) for pdf in pdfs]
            results = [future.result() for future in as_completed(futures)]
        
        # All should complete (success or partial)
        assert len(results) == 5
        for result in results:
            assert result.status.value in ["success", "partial"]
    
    def test_graceful_degradation(self):
        """System should degrade gracefully under stress."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Process many documents rapidly
        results = []
        for _ in range(20):
            result = extractor.extract_text(pdf_path)
            results.append(result)
        
        # Most should succeed
        successful = [r for r in results if r.status.value == "success"]
        assert len(successful) >= 18, "Too many failures under load"
        
        # All should complete (no hangs or crashes)
        assert len(results) == 20
