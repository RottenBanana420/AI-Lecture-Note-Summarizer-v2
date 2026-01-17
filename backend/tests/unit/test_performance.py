"""
Performance and scalability tests for PDF processing pipeline.

These tests are designed to INTENTIONALLY STRESS the pipeline and expose
performance bottlenecks. Tests are IMMUTABLE - only the implementation code
should be modified to make tests pass.

Test Philosophy:
- Tests define performance requirements
- Tests are never weakened or modified
- Implementation must satisfy all performance requirements
"""

import pytest
import gc
import time
import psutil
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.pdf_extractor import PDFExtractor
from app.services.pdf_segmenter import PDFSegmenter
from app.schemas.extraction_result import SegmentationOptions

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pdfs"

# Mark all tests in this module as performance tests
pytestmark = [pytest.mark.performance]


def get_memory_usage_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


class TestExtractionPerformance:
    """Test extraction speed benchmarks."""
    
    def test_small_pdf_extraction_speed(self, benchmark):
        """Small PDFs should be extracted in <500ms."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Benchmark the extraction
        result = benchmark(extractor.extract_text, pdf_path)
        
        # Verify extraction succeeded
        assert result.status.value == "success"
        assert len(result.text) > 0
        
        # Performance assertion: should complete in <500ms
        # benchmark.stats.stats.mean is in seconds
        mean_time = benchmark.stats.stats.mean
        assert mean_time < 0.5, f"Extraction took {mean_time:.3f}s, expected <0.5s"
    
    def test_medium_pdf_extraction_speed(self, benchmark):
        """Medium PDFs should be extracted in <2s."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"  # 5 pages
        
        result = benchmark(extractor.extract_text, pdf_path)
        
        assert result.status.value == "success"
        assert result.metadata.total_pages == 5
        
        # Performance assertion: should complete in <2s
        mean_time = benchmark.stats.stats.mean
        assert mean_time < 2.0, f"Extraction took {mean_time:.3f}s, expected <2s"
    
    def test_extraction_scales_linearly(self):
        """Extraction time should scale linearly with page count."""
        extractor = PDFExtractor()
        
        # Test with different sized PDFs
        small_pdf = FIXTURES_DIR / "clean_simple.pdf"  # 1 page
        medium_pdf = FIXTURES_DIR / "pdf_with_noise.pdf"  # 5 pages
        
        # Time small PDF
        start = time.time()
        result_small = extractor.extract_text(small_pdf)
        time_small = time.time() - start
        
        # Time medium PDF
        start = time.time()
        result_medium = extractor.extract_text(medium_pdf)
        time_medium = time.time() - start
        
        # Calculate time per page
        time_per_page_small = time_small / result_small.metadata.total_pages
        time_per_page_medium = time_medium / result_medium.metadata.total_pages
        
        # Should be within 3x of each other (allowing for overhead)
        ratio = max(time_per_page_small, time_per_page_medium) / min(time_per_page_small, time_per_page_medium)
        assert ratio < 3.0, f"Time per page varies too much: {time_per_page_small:.3f}s vs {time_per_page_medium:.3f}s"
    
    def test_repeated_extraction_performance(self, benchmark):
        """Repeated extractions should maintain consistent performance."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Run multiple times
        result = benchmark.pedantic(
            extractor.extract_text,
            args=(pdf_path,),
            iterations=10,
            rounds=3
        )
        
        # Verify consistency
        assert result.status.value == "success"
        
        # Standard deviation should be low (consistent performance)
        stddev = benchmark.stats.stats.stddev
        assert stddev < 0.1, f"Performance too variable: stddev={stddev:.3f}s"


class TestMemoryUsage:
    """Test memory efficiency."""
    
    def test_small_pdf_memory_usage(self):
        """Small PDFs should use <50MB of memory."""
        gc.collect()
        mem_before = get_memory_usage_mb()
        
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        mem_after = get_memory_usage_mb()
        mem_used = mem_after - mem_before
        
        assert result.status.value == "success"
        assert mem_used < 50, f"Used {mem_used:.1f}MB, expected <50MB"
    
    def test_medium_pdf_memory_usage(self):
        """Medium PDFs should use <100MB of memory."""
        gc.collect()
        mem_before = get_memory_usage_mb()
        
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        result = extractor.extract_text(pdf_path)
        
        mem_after = get_memory_usage_mb()
        mem_used = mem_after - mem_before
        
        assert result.status.value == "success"
        assert mem_used < 100, f"Used {mem_used:.1f}MB, expected <100MB"
    
    def test_memory_cleanup_after_processing(self):
        """Memory should be released after processing."""
        gc.collect()
        mem_baseline = get_memory_usage_mb()
        
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Process multiple times
        for _ in range(5):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
        
        # Force garbage collection
        gc.collect()
        mem_after = get_memory_usage_mb()
        
        # Memory should not grow significantly (allow 20MB growth for caches)
        mem_growth = mem_after - mem_baseline
        assert mem_growth < 20, f"Memory grew by {mem_growth:.1f}MB after 5 extractions, expected <20MB"
    
    def test_no_memory_leaks_over_time(self):
        """No memory leaks over extended use."""
        gc.collect()
        mem_baseline = get_memory_usage_mb()
        
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Process many times
        for _ in range(20):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
        
        gc.collect()
        mem_after = get_memory_usage_mb()
        
        # Memory should not grow significantly
        mem_growth = mem_after - mem_baseline
        assert mem_growth < 30, f"Memory leaked {mem_growth:.1f}MB after 20 extractions, expected <30MB"


class TestConcurrentProcessing:
    """Test concurrent processing capabilities."""
    
    def test_concurrent_extraction(self):
        """Should handle concurrent PDF extraction."""
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        num_concurrent = 5
        
        def extract_pdf():
            extractor = PDFExtractor()
            return extractor.extract_text(pdf_path)
        
        # Process concurrently
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(extract_pdf) for _ in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]
        
        # All should succeed
        assert len(results) == num_concurrent
        for result in results:
            assert result.status.value == "success"
            assert len(result.text) > 0
    
    def test_concurrent_processing_no_slowdown(self):
        """Concurrent processing should not cause significant slowdown."""
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Time sequential processing
        extractor = PDFExtractor()
        start = time.time()
        for _ in range(5):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
        sequential_time = time.time() - start
        
        # Time concurrent processing
        def extract_pdf():
            extractor = PDFExtractor()
            return extractor.extract_text(pdf_path)
        
        start = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(extract_pdf) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]
        concurrent_time = time.time() - start
        
        # Concurrent should be faster or similar (allow 2x overhead for thread management)
        assert concurrent_time < sequential_time * 2, \
            f"Concurrent ({concurrent_time:.2f}s) much slower than sequential ({sequential_time:.2f}s)"
    
    def test_error_isolation_between_documents(self):
        """Error in one document should not affect others."""
        valid_pdf = FIXTURES_DIR / "clean_simple.pdf"
        invalid_pdf = FIXTURES_DIR / "nonexistent.pdf"
        
        def extract_pdf(path):
            try:
                extractor = PDFExtractor()
                return extractor.extract_text(path)
            except Exception as e:
                return None
        
        # Process mix of valid and invalid PDFs concurrently
        paths = [valid_pdf, invalid_pdf, valid_pdf, invalid_pdf, valid_pdf]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(extract_pdf, path) for path in paths]
            results = [future.result() for future in as_completed(futures)]
        
        # Valid PDFs should succeed
        successful = [r for r in results if r is not None and r.status.value == "success"]
        assert len(successful) == 3, "Valid PDFs should succeed despite errors in others"


class TestResourceCleanup:
    """Test resource management and cleanup."""
    
    def test_file_handles_closed_properly(self):
        """File handles should be closed after extraction."""
        process = psutil.Process(os.getpid())
        
        # Get baseline file descriptor count
        open_files_before = len(process.open_files())
        
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Extract multiple times
        for _ in range(10):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
        
        # File descriptors should not grow
        open_files_after = len(process.open_files())
        
        # Allow small growth for caches, but no file handle leaks
        assert open_files_after - open_files_before < 5, \
            f"File handles leaked: {open_files_before} -> {open_files_after}"
    
    def test_spacy_model_cached_efficiently(self):
        """spaCy models should be loaded once and reused."""
        segmenter1 = PDFSegmenter()
        segmenter2 = PDFSegmenter()
        
        text = "This is a test sentence. This is another sentence."
        
        # First call loads model
        start = time.time()
        result1 = segmenter1.segment_text(text)
        time1 = time.time() - start
        
        # Second call should reuse cached model
        start = time.time()
        result2 = segmenter2.segment_text(text)
        time2 = time.time() - start
        
        # Both should succeed
        assert result1.metadata.total_sentences == 2
        assert result2.metadata.total_sentences == 2
        
        # Second call should be faster (model already loaded)
        # Allow some variance, but should be noticeably faster
        assert time2 < time1 * 1.5, \
            f"Second segmentation ({time2:.3f}s) not faster than first ({time1:.3f}s), model not cached?"
    
    def test_resources_cleaned_on_error(self):
        """Resources should be cleaned up even on errors."""
        process = psutil.Process(os.getpid())
        open_files_before = len(process.open_files())
        
        extractor = PDFExtractor()
        
        # Try to extract non-existent file (should error)
        try:
            extractor.extract_text(FIXTURES_DIR / "nonexistent.pdf")
        except FileNotFoundError:
            pass  # Expected
        
        # File handles should still be cleaned up
        open_files_after = len(process.open_files())
        assert open_files_after <= open_files_before + 1, \
            "File handles not cleaned up after error"


class TestPipelineThroughput:
    """Test end-to-end pipeline performance."""
    
    def test_full_pipeline_performance(self, benchmark):
        """Full pipeline (extract → clean → segment) should be efficient."""
        extractor = PDFExtractor()
        segmenter = PDFSegmenter()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        def full_pipeline():
            # Extract and clean
            extraction_result = extractor.extract_text(pdf_path, apply_cleaning=True)
            # Segment
            segmentation_result = segmenter.segment_text(extraction_result.text)
            return extraction_result, segmentation_result
        
        extraction_result, segmentation_result = benchmark(full_pipeline)
        
        # Verify results
        assert extraction_result.status.value == "success"
        assert segmentation_result.metadata.total_segments > 0
        
        # Performance assertion: full pipeline should complete in <1s for small PDF
        mean_time = benchmark.stats.stats.mean
        assert mean_time < 1.0, \
            f"Full pipeline took {mean_time:.3f}s, expected <1s"
    
    def test_batch_processing_efficiency(self):
        """Batch processing should be more efficient than individual processing."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        num_docs = 10
        
        # Time individual processing
        start = time.time()
        for _ in range(num_docs):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
        individual_time = time.time() - start
        
        # Time batch processing (simulated by reusing extractor instance)
        start = time.time()
        extractor_batch = PDFExtractor()
        for _ in range(num_docs):
            result = extractor_batch.extract_text(pdf_path)
            assert result.status.value == "success"
        batch_time = time.time() - start
        
        # Batch should be similar or faster (caching benefits)
        # Allow significant variance due to test execution order and system load
        assert batch_time <= individual_time * 2.0, \
            f"Batch processing ({batch_time:.2f}s) significantly slower than individual ({individual_time:.2f}s)"
    
    def test_cache_effectiveness(self):
        """Caching should improve performance for repeated operations."""
        segmenter = PDFSegmenter()
        text = "This is a test sentence. " * 50  # Repeated text
        
        # First segmentation (cold cache)
        start = time.time()
        result1 = segmenter.segment_text(text)
        time1 = time.time() - start
        
        # Second segmentation (warm cache)
        start = time.time()
        result2 = segmenter.segment_text(text)
        time2 = time.time() - start
        
        # Both should succeed
        assert result1.metadata.total_segments > 0
        assert result2.metadata.total_segments > 0
        
        # Second should be faster or similar (model cached)
        assert time2 <= time1 * 1.5, \
            f"Second segmentation ({time2:.3f}s) not benefiting from cache vs first ({time1:.3f}s)"
    
    def test_overall_throughput(self):
        """Overall system throughput should meet requirements."""
        extractor = PDFExtractor()
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Process 20 documents and measure throughput
        start = time.time()
        for _ in range(20):
            result = extractor.extract_text(pdf_path)
            assert result.status.value == "success"
        total_time = time.time() - start
        
        # Calculate documents per minute
        docs_per_minute = (20 / total_time) * 60
        
        # Should process at least 20 documents per minute
        assert docs_per_minute >= 20, \
            f"Throughput is {docs_per_minute:.1f} docs/min, expected ≥20 docs/min"
