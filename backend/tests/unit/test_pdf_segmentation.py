"""
Unit tests for PDF text segmentation.

These tests are designed to INTENTIONALLY FAIL initially and expose weaknesses
in the segmentation logic. Tests are IMMUTABLE - only the implementation code
should be modified to make tests pass.

Test Philosophy:
- Tests define correctness
- Tests are never weakened or modified
- Implementation must satisfy all test requirements
"""

import pytest
from pathlib import Path
from app.services.pdf_segmenter import PDFSegmenter
from app.services.pdf_extractor import PDFExtractor
from app.schemas.extraction_result import (
    SegmentationOptions,
    SegmentationMetadata,
    TextSegment,
    SegmentationResult,
)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pdfs"


class TestSentenceSegmentation:
    """Test sentence-level segmentation accuracy."""
    
    def test_accurate_sentence_boundary_detection(self):
        """Sentences should be accurately detected at proper boundaries."""
        segmenter = PDFSegmenter()
        
        text = "This is the first sentence. This is the second sentence. And this is the third."
        result = segmenter.segment_text(text)
        
        # Should detect 3 sentences
        assert result.metadata.total_sentences == 3
    
    def test_handle_abbreviations(self):
        """Abbreviations like Dr., Mr., etc. should not break sentences."""
        segmenter = PDFSegmenter()
        
        text = "Dr. Smith gave a lecture. Mr. Jones attended it."
        result = segmenter.segment_text(text)
        
        # Should detect 2 sentences, not 4
        assert result.metadata.total_sentences == 2
    
    def test_multi_sentence_paragraphs(self):
        """Multiple sentences in a paragraph should be detected correctly."""
        segmenter = PDFSegmenter()
        
        text = """Neural networks are powerful models. They consist of layers of neurons. 
        Each neuron performs a weighted sum. The result is passed through an activation function."""
        
        result = segmenter.segment_text(text)
        
        # Should detect 4 sentences
        assert result.metadata.total_sentences == 4
    
    def test_single_sentence_text(self):
        """Single sentence text should be handled correctly."""
        segmenter = PDFSegmenter()
        
        text = "This is a single sentence."
        result = segmenter.segment_text(text)
        
        # Should detect 1 sentence
        assert result.metadata.total_sentences == 1
        # Should create 1 segment
        assert result.metadata.total_segments == 1
    
    def test_text_without_punctuation(self):
        """Text without proper punctuation should still be segmented."""
        segmenter = PDFSegmenter()
        
        text = "This is text without proper punctuation it should still work"
        result = segmenter.segment_text(text)
        
        # Should create at least 1 segment
        assert result.metadata.total_segments >= 1


class TestSemanticChunking:
    """Test chunk creation with semantic coherence."""
    
    def test_chunk_size_respects_token_limits(self):
        """Chunks should not exceed maximum token limit."""
        segmenter = PDFSegmenter()
        
        # Create long text
        text = " ".join(["This is a test sentence."] * 100)
        
        options = SegmentationOptions(
            chunk_size_tokens=256,
            max_chunk_size=512
        )
        result = segmenter.segment_text(text, options)
        
        # No chunk should exceed max size
        for segment in result.segments:
            assert segment.token_count <= 512
    
    def test_chunk_size_meets_minimum(self):
        """Chunks should meet minimum size unless at end of document."""
        segmenter = PDFSegmenter()
        
        text = " ".join(["This is a test sentence."] * 50)
        
        options = SegmentationOptions(
            chunk_size_tokens=256,
            min_chunk_size=50
        )
        result = segmenter.segment_text(text, options)
        
        # All chunks except possibly the last should meet minimum
        for i, segment in enumerate(result.segments[:-1]):
            assert segment.token_count >= 50
    
    def test_overlap_percentage_is_accurate(self):
        """Overlap between chunks should match configured percentage."""
        segmenter = PDFSegmenter()
        
        text = " ".join(["This is a test sentence."] * 100)
        
        options = SegmentationOptions(
            chunk_size_tokens=200,
            overlap_percentage=0.2
        )
        result = segmenter.segment_text(text, options)
        
        # Check overlap between consecutive segments
        if len(result.segments) > 1:
            for i in range(len(result.segments) - 1):
                current = result.segments[i]
                next_seg = result.segments[i + 1]
                
                # Overlap should exist
                assert current.overlap_with_next is not None
                assert next_seg.overlap_with_previous is not None
                
                # Overlap should be approximately 20% of chunk size
                overlap_tokens = segmenter._estimate_token_count(current.overlap_with_next)
                expected_overlap = int(current.token_count * 0.2)
                
                # Allow 10% tolerance
                assert abs(overlap_tokens - expected_overlap) <= expected_overlap * 0.1
    
    def test_semantic_boundaries_preferred(self):
        """Chunks should prefer breaking at paragraph boundaries."""
        segmenter = PDFSegmenter()
        
        text = """First paragraph with multiple sentences. This continues the first paragraph.
        
        Second paragraph starts here. It also has multiple sentences.
        
        Third paragraph is the last one. It ends the document."""
        
        options = SegmentationOptions(
            chunk_size_tokens=100,
            prefer_semantic_boundaries=True
        )
        result = segmenter.segment_text(text, options)
        
        # Should detect and use semantic boundaries
        semantic_count = sum(1 for seg in result.segments if seg.has_semantic_boundary)
        assert semantic_count > 0
    
    def test_no_orphaned_fragments(self):
        """Chunks should not create tiny orphaned fragments."""
        segmenter = PDFSegmenter()
        
        text = " ".join(["This is a test sentence."] * 50)
        
        options = SegmentationOptions(
            chunk_size_tokens=256,
            min_chunk_size=50
        )
        result = segmenter.segment_text(text, options)
        
        # Last chunk can be smaller, but not tiny (< 20% of min)
        if len(result.segments) > 1:
            last_chunk = result.segments[-1]
            assert last_chunk.token_count >= options.min_chunk_size * 0.2


class TestTokenCounting:
    """Test token estimation accuracy."""
    
    def test_token_count_reasonable_estimate(self):
        """Token count should be a reasonable estimate."""
        segmenter = PDFSegmenter()
        
        # Known text: ~25 words, should be ~25-35 tokens
        text = "This is a test sentence with exactly twenty five words in it to test the token counting functionality properly."
        
        token_count = segmenter._estimate_token_count(text)
        
        # Should be in reasonable range (20-40 tokens)
        assert 20 <= token_count <= 40
    
    def test_token_count_consistency(self):
        """Same text should always produce same token count."""
        segmenter = PDFSegmenter()
        
        text = "Consistent token counting is important for reproducibility."
        
        count1 = segmenter._estimate_token_count(text)
        count2 = segmenter._estimate_token_count(text)
        
        assert count1 == count2
    
    def test_token_count_handles_special_characters(self):
        """Token counting should handle special characters correctly."""
        segmenter = PDFSegmenter()
        
        text = "Text with special chars: @#$%, numbers 123, and punctuation!!!"
        
        token_count = segmenter._estimate_token_count(text)
        
        # Should return a positive count
        assert token_count > 0
    
    def test_empty_text_token_count(self):
        """Empty text should have zero tokens."""
        segmenter = PDFSegmenter()
        
        assert segmenter._estimate_token_count("") == 0
        assert segmenter._estimate_token_count("   ") == 0


class TestChunkOverlap:
    """Test overlap strategy validation."""
    
    def test_first_chunk_no_previous_overlap(self):
        """First chunk should have no overlap with previous."""
        segmenter = PDFSegmenter()
        
        text = " ".join(["This is a test sentence."] * 50)
        
        options = SegmentationOptions(overlap_percentage=0.2)
        result = segmenter.segment_text(text, options)
        
        # First chunk should have no previous overlap
        assert result.segments[0].overlap_with_previous is None
    
    def test_last_chunk_no_next_overlap(self):
        """Last chunk should have no overlap with next."""
        segmenter = PDFSegmenter()
        
        text = " ".join(["This is a test sentence."] * 50)
        
        options = SegmentationOptions(overlap_percentage=0.2)
        result = segmenter.segment_text(text, options)
        
        # Last chunk should have no next overlap
        assert result.segments[-1].overlap_with_next is None
    
    def test_overlap_content_matches(self):
        """Overlap content should match between consecutive chunks."""
        segmenter = PDFSegmenter()
        
        text = " ".join(["This is a test sentence."] * 50)
        
        options = SegmentationOptions(overlap_percentage=0.2)
        result = segmenter.segment_text(text, options)
        
        # Check that overlap content matches
        if len(result.segments) > 1:
            for i in range(len(result.segments) - 1):
                current = result.segments[i]
                next_seg = result.segments[i + 1]
                
                # Current's next overlap should match next's previous overlap
                assert current.overlap_with_next == next_seg.overlap_with_previous
    
    def test_no_duplicate_content_beyond_overlap(self):
        """Content should not be duplicated beyond the overlap region."""
        segmenter = PDFSegmenter()
        
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        
        options = SegmentationOptions(
            chunk_size_tokens=50,
            overlap_percentage=0.2
        )
        result = segmenter.segment_text(text, options)
        
        # Reconstruct text from segments (removing overlap)
        reconstructed_parts = []
        for i, segment in enumerate(result.segments):
            if i == 0:
                reconstructed_parts.append(segment.text)
            else:
                # Remove overlap from beginning
                overlap_len = len(segment.overlap_with_previous) if segment.overlap_with_previous else 0
                non_overlap_text = segment.text[overlap_len:]
                reconstructed_parts.append(non_overlap_text)
        
        reconstructed = "".join(reconstructed_parts)
        
        # Reconstructed should match original (allowing for whitespace differences)
        assert reconstructed.strip() == text.strip()


class TestSemanticCoherence:
    """Test semantic quality validation."""
    
    def test_chunks_dont_break_mid_sentence(self):
        """Chunks should never break in the middle of a sentence."""
        segmenter = PDFSegmenter()
        
        text = " ".join([f"This is sentence number {i}." for i in range(100)])
        
        result = segmenter.segment_text(text)
        
        # Each chunk should end with proper sentence ending
        for segment in result.segments:
            text_stripped = segment.text.strip()
            # Should end with sentence-ending punctuation
            assert text_stripped[-1] in '.!?'
    
    def test_paragraph_boundaries_respected(self):
        """Paragraph boundaries should be respected when possible."""
        segmenter = PDFSegmenter()
        
        paragraphs = [
            "First paragraph. It has multiple sentences.",
            "Second paragraph. Also with multiple sentences.",
            "Third paragraph. The final one."
        ]
        text = "\n\n".join(paragraphs)
        
        options = SegmentationOptions(
            chunk_size_tokens=100,
            prefer_semantic_boundaries=True
        )
        result = segmenter.segment_text(text, options)
        
        # Should use semantic boundaries
        assert result.metadata.semantic_boundaries_used > 0
    
    def test_section_headers_stay_with_content(self):
        """Section headers should stay with their content."""
        segmenter = PDFSegmenter()
        
        text = """Introduction
        
        This is the introduction paragraph. It explains the topic.
        
        Methods
        
        This is the methods section. It describes the approach."""
        
        options = SegmentationOptions(
            chunk_size_tokens=150,
            prefer_semantic_boundaries=True
        )
        result = segmenter.segment_text(text, options)
        
        # Check that headers are not isolated
        for segment in result.segments:
            lines = segment.text.strip().split('\n')
            # If segment has multiple lines, first line shouldn't be alone
            if len(lines) > 1:
                assert len(lines[0].split()) > 1 or len(lines) > 2


class TestEdgeCases:
    """Test boundary conditions."""
    
    def test_very_short_document(self):
        """Very short documents (< chunk size) should create one segment."""
        segmenter = PDFSegmenter()
        
        text = "This is a very short document."
        
        options = SegmentationOptions(chunk_size_tokens=256)
        result = segmenter.segment_text(text, options)
        
        # Should create exactly 1 segment
        assert result.metadata.total_segments == 1
        assert result.segments[0].text == text
    
    def test_very_long_document(self):
        """Very long documents should be segmented into multiple chunks."""
        segmenter = PDFSegmenter()
        
        # Create a very long document
        text = " ".join([f"Sentence number {i}." for i in range(1000)])
        
        options = SegmentationOptions(chunk_size_tokens=256)
        result = segmenter.segment_text(text, options)
        
        # Should create multiple segments
        assert result.metadata.total_segments > 5
    
    def test_empty_text(self):
        """Empty text should return empty result."""
        segmenter = PDFSegmenter()
        
        result = segmenter.segment_text("")
        
        assert result.metadata.total_segments == 0
        assert len(result.segments) == 0
    
    def test_whitespace_only_text(self):
        """Whitespace-only text should return empty result."""
        segmenter = PDFSegmenter()
        
        result = segmenter.segment_text("   \n\n   \t\t   ")
        
        assert result.metadata.total_segments == 0
        assert len(result.segments) == 0
    
    def test_single_very_long_sentence(self):
        """A single very long sentence should be handled gracefully."""
        segmenter = PDFSegmenter()
        
        # Create a very long sentence (no periods)
        text = " and ".join(["this is a clause"] * 100)
        
        options = SegmentationOptions(
            chunk_size_tokens=256,
            max_chunk_size=512
        )
        result = segmenter.segment_text(text, options)
        
        # Should create segments even without sentence boundaries
        assert result.metadata.total_segments >= 1
    
    def test_no_semantic_boundaries(self):
        """Text without clear semantic boundaries should still segment."""
        segmenter = PDFSegmenter()
        
        # All one paragraph, no clear breaks
        text = " ".join([f"Sentence {i}." for i in range(50)])
        
        options = SegmentationOptions(
            chunk_size_tokens=100,
            prefer_semantic_boundaries=True
        )
        result = segmenter.segment_text(text, options)
        
        # Should still create segments
        assert result.metadata.total_segments > 1


class TestDeterministicBehavior:
    """Test reproducibility."""
    
    def test_same_input_produces_same_output(self):
        """Same input should produce identical output."""
        segmenter = PDFSegmenter()
        
        text = " ".join([f"This is sentence {i}." for i in range(50)])
        
        result1 = segmenter.segment_text(text)
        result2 = segmenter.segment_text(text)
        
        # Should produce same number of segments
        assert result1.metadata.total_segments == result2.metadata.total_segments
        
        # Each segment should be identical
        for seg1, seg2 in zip(result1.segments, result2.segments):
            assert seg1.text == seg2.text
            assert seg1.token_count == seg2.token_count
            assert seg1.start_char == seg2.start_char
            assert seg1.end_char == seg2.end_char
    
    def test_segment_ids_are_consistent(self):
        """Segment IDs should be consistent across runs."""
        segmenter = PDFSegmenter()
        
        text = "First sentence. Second sentence. Third sentence."
        
        result1 = segmenter.segment_text(text)
        result2 = segmenter.segment_text(text)
        
        # Segment IDs should match
        for seg1, seg2 in zip(result1.segments, result2.segments):
            assert seg1.segment_id == seg2.segment_id
    
    def test_metadata_is_accurate(self):
        """Metadata should accurately reflect segmentation."""
        segmenter = PDFSegmenter()
        
        text = " ".join([f"Sentence {i}." for i in range(30)])
        
        result = segmenter.segment_text(text)
        
        # Total segments should match list length
        assert result.metadata.total_segments == len(result.segments)
        
        # Average segment size should be accurate
        if result.segments:
            actual_avg = sum(seg.token_count for seg in result.segments) / len(result.segments)
            assert abs(actual_avg - result.metadata.avg_segment_size) < 0.1
        
        # Min/max should be accurate
        if result.segments:
            token_counts = [seg.token_count for seg in result.segments]
            assert result.metadata.min_segment_size == min(token_counts)
            assert result.metadata.max_segment_size == max(token_counts)


class TestIntegration:
    """End-to-end pipeline tests."""
    
    def test_integration_with_pdf_extraction(self):
        """Segmentation should work with extracted PDF text."""
        extractor = PDFExtractor()
        segmenter = PDFSegmenter()
        
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        # Extract text
        extraction_result = extractor.extract_text(pdf_path)
        
        # Segment the cleaned text
        segmentation_result = segmenter.segment_text(extraction_result.text)
        
        # Should create segments
        assert segmentation_result.metadata.total_segments > 0
        assert len(segmentation_result.segments) > 0
    
    def test_integration_with_multipage_pdf(self):
        """Segmentation should handle multi-page PDFs."""
        extractor = PDFExtractor()
        segmenter = PDFSegmenter()
        
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Extract and clean text
        extraction_result = extractor.extract_text(pdf_path)
        
        # Segment
        segmentation_result = segmenter.segment_text(extraction_result.text)
        
        # Should create multiple segments for multi-page document
        assert segmentation_result.metadata.total_segments > 1
    
    def test_full_pipeline_extract_clean_segment(self):
        """Full pipeline: extract → clean → segment should work."""
        extractor = PDFExtractor()
        segmenter = PDFSegmenter()
        
        pdf_path = FIXTURES_DIR / "pdf_with_noise.pdf"
        
        # Extract with cleaning
        extraction_result = extractor.extract_text(pdf_path, apply_cleaning=True)
        
        # Segment the cleaned text
        options = SegmentationOptions(
            chunk_size_tokens=256,
            overlap_percentage=0.2,
            prefer_semantic_boundaries=True
        )
        segmentation_result = segmenter.segment_text(extraction_result.text, options)
        
        # Should successfully segment
        assert segmentation_result.metadata.total_segments > 0
        
        # All segments should have valid data
        for segment in segmentation_result.segments:
            assert len(segment.text) > 0
            assert segment.token_count > 0
            assert segment.end_char > segment.start_char
    
    def test_segmentation_preserves_content(self):
        """Segmentation should preserve all content from source."""
        extractor = PDFExtractor()
        segmenter = PDFSegmenter()
        
        pdf_path = FIXTURES_DIR / "clean_simple.pdf"
        
        extraction_result = extractor.extract_text(pdf_path)
        original_text = extraction_result.text
        
        # Segment with no overlap for easier verification
        options = SegmentationOptions(overlap_percentage=0.0)
        segmentation_result = segmenter.segment_text(original_text, options)
        
        # Reconstruct text from segments
        reconstructed = "".join(seg.text for seg in segmentation_result.segments)
        
        # Should match original (allowing for whitespace normalization)
        assert reconstructed.strip() == original_text.strip()
