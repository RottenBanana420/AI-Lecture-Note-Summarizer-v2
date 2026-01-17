"""
PDF text segmentation service.

Provides robust text segmentation for downstream AI processing (RAG, summarization).
Segments text into semantically coherent chunks with configurable size and overlap.
"""

import time
import hashlib
import re
from typing import List, Optional, Tuple
import spacy
from spacy.language import Language

from app.schemas.extraction_result import (
    SegmentationOptions,
    TextSegment,
    SegmentationMetadata,
    SegmentationResult,
)


class PDFSegmenter:
    """
    PDF text segmentation service for creating AI-ready chunks.
    
    Features:
    - Sentence-level segmentation using spaCy
    - Semantic chunking with configurable size and overlap
    - Token counting for model constraints
    - Paragraph and section boundary detection
    - Deterministic segmentation behavior
    """
    
    def __init__(self):
        """Initialize the PDF segmenter."""
        self._nlp: Optional[Language] = None
        self._current_model: str = ""
    
    def _load_spacy_model(self, model_name: str) -> Language:
        """
        Load spaCy model with caching.
        
        Args:
            model_name: Name of spaCy model to load
            
        Returns:
            Loaded spaCy Language model
        """
        if self._nlp is None or self._current_model != model_name:
            try:
                # Load model with only sentence segmentation component
                self._nlp = spacy.load(model_name, disable=["ner", "lemmatizer", "textcat"])
                self._current_model = model_name
            except OSError:
                # Fallback to blank model with sentencizer if model not found
                self._nlp = spacy.blank("en")
                self._nlp.add_pipe("sentencizer")
                self._current_model = "blank_en"
        
        return self._nlp
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count using whitespace-based approximation.
        
        Uses the rule: 1 token ≈ 4 characters (common for English text).
        This is a lightweight approximation suitable for chunking.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        if not text or not text.strip():
            return 0
        
        # Use character-based estimation: 1 token ≈ 4 characters
        # This is a common approximation for English text
        char_count = len(text.strip())
        token_estimate = max(1, char_count // 4)
        
        return token_estimate
    
    def _segment_sentences(self, text: str, model_name: str) -> List[str]:
        """
        Segment text into sentences using spaCy.
        
        Args:
            text: Input text
            model_name: spaCy model to use
            
        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []
        
        nlp = self._load_spacy_model(model_name)
        doc = nlp(text)
        
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        return sentences
    
    def _detect_semantic_boundaries(self, text: str, sentences: List[str]) -> List[int]:
        """
        Detect semantic boundaries (paragraph breaks, section headers) between sentences.
        
        Args:
            text: Input text
            sentences: List of sentences to check for boundaries
            
        Returns:
            List of sentence indices where semantic boundaries occur (after the sentence)
        """
        boundaries = []
        
        # Find paragraph breaks in original text
        paragraph_break_positions = set()
        for match in re.finditer(r'\n\s*\n', text):
            paragraph_break_positions.add(match.start())
            paragraph_break_positions.add(match.end())
        
        # Check each sentence to see if there's a paragraph break after it
        current_pos = 0
        for i, sentence in enumerate(sentences):
            # Find sentence in text
            sent_start = text.find(sentence, current_pos)
            if sent_start != -1:
                sent_end = sent_start + len(sentence)
                
                # Check if there's a paragraph break after this sentence
                # Look ahead up to 10 characters for paragraph break
                for pos in range(sent_end, min(sent_end + 10, len(text))):
                    if pos in paragraph_break_positions:
                        boundaries.append(i)
                        break
                
                current_pos = sent_end
        
        return boundaries
    
    def _create_chunks(
        self,
        sentences: List[str],
        text: str,
        options: SegmentationOptions
    ) -> Tuple[List[TextSegment], int]:
        """
        Create chunks from sentences with overlap.
        
        Args:
            sentences: List of sentences
            text: Original text for character position tracking
            options: Segmentation configuration
            
        Returns:
            Tuple of (list of TextSegment objects, semantic_boundaries_used count)
        """
        if not sentences:
            return [], 0
        
        chunks = []
        semantic_boundaries_used = 0
        current_chunk_sentences = []
        current_chunk_tokens = 0
        
        # Detect semantic boundaries (sentence indices where paragraph breaks occur)
        semantic_boundary_indices = set(self._detect_semantic_boundaries(text, sentences))
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self._estimate_token_count(sentence)
            
            # Check if adding this sentence would exceed max chunk size
            would_exceed_max = (current_chunk_tokens + sentence_tokens) > options.max_chunk_size
            
            # Check if we should create a chunk
            should_create_chunk = False
            has_semantic_boundary = False
            
            if would_exceed_max and current_chunk_sentences:
                # Must create chunk to avoid exceeding max
                should_create_chunk = True
            elif current_chunk_tokens + sentence_tokens >= options.chunk_size_tokens:
                # Reached target size
                should_create_chunk = True
                if options.prefer_semantic_boundaries:
                    # Check if there's a semantic boundary after this sentence
                    if i in semantic_boundary_indices:
                        has_semantic_boundary = True
                        semantic_boundaries_used += 1
            
            # Add sentence to current chunk
            current_chunk_sentences.append(sentence)
            current_chunk_tokens += sentence_tokens
            
            # Create chunk if needed
            if should_create_chunk or i == len(sentences) - 1:
                # Don't create tiny chunks unless it's the last one
                if current_chunk_tokens >= options.min_chunk_size or i == len(sentences) - 1:
                    # For single-chunk documents or last chunk, check if ANY semantic boundaries exist within the chunk
                    if not has_semantic_boundary and options.prefer_semantic_boundaries:
                        # Count semantic boundaries within this chunk's sentences
                        chunk_start_idx = i - len(current_chunk_sentences) + 1
                        chunk_end_idx = i
                        for sent_idx in range(chunk_start_idx, chunk_end_idx + 1):
                            if sent_idx in semantic_boundary_indices:
                                has_semantic_boundary = True
                                semantic_boundaries_used += 1
                                break  # Only count one boundary per chunk
                    
                    chunk_text = " ".join(current_chunk_sentences)
                    
                    # Find character positions in original text
                    start_char = text.find(current_chunk_sentences[0])
                    if start_char == -1:
                        start_char = 0
                    
                    end_char = start_char + len(chunk_text)
                    
                    # Calculate overlap with previous chunk
                    overlap_with_previous = None
                    overlap_with_next = None
                    
                    if chunks:  # Not the first chunk
                        # Calculate overlap from the PREVIOUS chunk's end
                        prev_chunk = chunks[-1]
                        overlap_size_tokens = int(prev_chunk.token_count * options.overlap_percentage)
                        
                        if overlap_size_tokens > 0:
                            # Take last N sentences from previous chunk
                            prev_sentences = prev_chunk.text.split(". ")
                            prev_sentences = [s.strip() + "." if not s.endswith(".") else s.strip() for s in prev_sentences if s.strip()]
                            
                            overlap_sentences = []
                            overlap_tokens = 0
                            
                            for sent in reversed(prev_sentences):
                                sent_tokens = self._estimate_token_count(sent)
                                if overlap_tokens + sent_tokens <= overlap_size_tokens:
                                    overlap_sentences.insert(0, sent)
                                    overlap_tokens += sent_tokens
                                else:
                                    break
                            
                            if overlap_sentences:
                                overlap_with_previous = " ".join(overlap_sentences)
                    
                    # Generate deterministic segment ID
                    segment_id = self._generate_segment_id(chunk_text, len(chunks))
                    
                    segment = TextSegment(
                        segment_id=segment_id,
                        text=chunk_text,
                        start_char=start_char,
                        end_char=end_char,
                        token_count=current_chunk_tokens,
                        sentence_count=len(current_chunk_sentences),
                        has_semantic_boundary=has_semantic_boundary,
                        overlap_with_previous=overlap_with_previous,
                        overlap_with_next=None,  # Will be set when next chunk is created
                    )
                    
                    chunks.append(segment)
                    
                    # Update previous chunk's overlap_with_next
                    if len(chunks) > 1 and overlap_with_previous:
                        # Need to recreate previous segment with overlap_with_next
                        prev_segment = chunks[-2]
                        chunks[-2] = TextSegment(
                            segment_id=prev_segment.segment_id,
                            text=prev_segment.text,
                            start_char=prev_segment.start_char,
                            end_char=prev_segment.end_char,
                            token_count=prev_segment.token_count,
                            sentence_count=prev_segment.sentence_count,
                            has_semantic_boundary=prev_segment.has_semantic_boundary,
                            overlap_with_previous=prev_segment.overlap_with_previous,
                            overlap_with_next=overlap_with_previous,
                        )
                    
                    # Reset for next chunk
                    if i < len(sentences) - 1:
                        # Start fresh for next chunk (overlap will be calculated from this chunk)
                        current_chunk_sentences = []
                        current_chunk_tokens = 0
        
        return chunks, semantic_boundaries_used
    
    def _generate_segment_id(self, text: str, index: int) -> str:
        """
        Generate deterministic segment ID.
        
        Args:
            text: Segment text
            index: Segment index
            
        Returns:
            Unique segment identifier
        """
        # Create hash of text for determinism
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"seg_{index:04d}_{text_hash}"
    
    def segment_text(
        self,
        text: str,
        options: Optional[SegmentationOptions] = None
    ) -> SegmentationResult:
        """
        Segment text into chunks suitable for AI processing.
        
        Args:
            text: Input text to segment
            options: Optional segmentation configuration
            
        Returns:
            SegmentationResult with segments and metadata
        """
        start_time = time.time()
        
        # Use default options if not provided
        if options is None:
            options = SegmentationOptions()
        
        # Handle empty text
        if not text or not text.strip():
            metadata = SegmentationMetadata(
                total_segments=0,
                total_sentences=0,
                avg_segment_size=0.0,
                min_segment_size=0,
                max_segment_size=0,
                semantic_boundaries_used=0,
                segmentation_time_ms=0.0,
            )
            return SegmentationResult(
                segments=[],
                metadata=metadata,
                source_text_length=0,
            )
        
        # Segment into sentences
        sentences = self._segment_sentences(text, options.sentence_segmentation_model)
        
        if not sentences:
            # No sentences detected, treat entire text as one segment
            token_count = self._estimate_token_count(text)
            segment_id = self._generate_segment_id(text, 0)
            
            segment = TextSegment(
                segment_id=segment_id,
                text=text,
                start_char=0,
                end_char=len(text),
                token_count=token_count,
                sentence_count=1,
                has_semantic_boundary=False,
                overlap_with_previous=None,
                overlap_with_next=None,
            )
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            metadata = SegmentationMetadata(
                total_segments=1,
                total_sentences=1,
                avg_segment_size=float(token_count),
                min_segment_size=token_count,
                max_segment_size=token_count,
                semantic_boundaries_used=0,
                segmentation_time_ms=processing_time_ms,
            )
            
            return SegmentationResult(
                segments=[segment],
                metadata=metadata,
                source_text_length=len(text),
            )
        
        # Create chunks from sentences
        segments, semantic_boundaries_used = self._create_chunks(sentences, text, options)
        
        # Calculate metadata
        processing_time_ms = (time.time() - start_time) * 1000
        
        if segments:
            token_counts = [seg.token_count for seg in segments]
            avg_segment_size = sum(token_counts) / len(token_counts)
            min_segment_size = min(token_counts)
            max_segment_size = max(token_counts)
        else:
            avg_segment_size = 0.0
            min_segment_size = 0
            max_segment_size = 0
        
        metadata = SegmentationMetadata(
            total_segments=len(segments),
            total_sentences=len(sentences),
            avg_segment_size=avg_segment_size,
            min_segment_size=min_segment_size,
            max_segment_size=max_segment_size,
            semantic_boundaries_used=semantic_boundaries_used,
            segmentation_time_ms=processing_time_ms,
        )
        
        return SegmentationResult(
            segments=segments,
            metadata=metadata,
            source_text_length=len(text),
        )
