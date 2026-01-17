"""
PDF text cleaning service.

Provides robust text cleaning to remove non-semantic noise while preserving meaning.
"""

import re
from typing import List, Dict, Optional
from collections import Counter
from difflib import SequenceMatcher

from app.schemas.extraction_result import (
    PageResult,
    CleaningOptions,
    CleaningMetadata,
)


class PDFCleaner:
    """
    PDF text cleaning service for removing noise while preserving semantic content.
    
    Removes:
    - Headers and footers (repeated text at top/bottom of pages)
    - Page numbers (various formats)
    - Repeated artifacts (watermarks, navigation elements)
    - Formatting remnants (orphaned bullets, table borders)
    """
    
    def __init__(self):
        """Initialize the PDF cleaner."""
        # Page number patterns
        self.page_number_patterns = [
            r'^\s*Page\s+\d+\s*$',  # "Page 1"
            r'^\s*Page\s+\d+\s+of\s+\d+\s*$',  # "Page 1 of 10"
            r'^\s*\d+\s+of\s+\d+\s*$',  # "1 of 10"
            r'^\s*[-–—]\s*\d+\s*[-–—]\s*$',  # "- 5 -"
            r'^\s*[ivxlcdm]+\s*$',  # Roman numerals (i, ii, iii, etc.)
        ]
        
        # Formatting remnant patterns
        self.formatting_patterns = [
            r'^\s*[•\-\*◦▪▫]\s*$',  # Orphaned bullets
            r'^[\|─┼├┤┬┴┌┐└┘│]+$',  # Table borders
            r'^[\.,:;!?]{3,}$',  # Excessive punctuation
        ]
    
    def detect_headers_footers(self, pages: List[PageResult]) -> Dict[str, List[str]]:
        """
        Detect headers and footers by analyzing repeated lines at top/bottom of pages.
        
        Args:
            pages: List of page results with text
            
        Returns:
            Dict with 'headers' and 'footers' lists of detected patterns
        """
        if not pages or len(pages) < 2:
            return {'headers': [], 'footers': []}
        
        # Collect individual header and footer lines from each page
        all_first_lines = []
        all_last_lines = []
        
        for page in pages:
            if not page.text or not page.text.strip():
                continue
            
            lines = [line.strip() for line in page.text.split('\n') if line.strip()]
            if not lines:
                continue
            
            # Collect first line (potential header)
            if lines:
                all_first_lines.append(lines[0])
            
            # Collect last line (potential footer)
            if len(lines) > 1:
                all_last_lines.append(lines[-1])
        
        # Find patterns that appear on most pages (>70%)
        threshold = max(2, int(len(pages) * 0.7))
        
        # Find repeated headers
        headers = self._find_repeated_patterns(all_first_lines, threshold)
        
        # Find repeated footers
        footers = self._find_repeated_patterns(all_last_lines, threshold)
        
        return {'headers': headers, 'footers': footers}
    
    def _combine_blocks_on_line(self, blocks: List) -> str:
        """Combine text blocks that are on the same line."""
        if not blocks:
            return ""
        
        # Group blocks by similar y-coordinate (within 5 units)
        lines = []
        current_line = []
        current_y = None
        
        for block in blocks:
            if current_y is None or abs(block.y1 - current_y) < 5:
                current_line.append(block.text.strip())
                current_y = block.y1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [block.text.strip()]
                current_y = block.y1
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return ' '.join(lines)
    
    def _find_repeated_patterns(self, texts: List[str], threshold: int) -> List[str]:
        """Find text patterns that appear frequently using fuzzy matching."""
        if not texts:
            return []
        
        # Count exact matches first
        text_counts = Counter(texts)
        patterns = []
        
        # Add exact matches that meet threshold
        for text, count in text_counts.items():
            if count >= threshold and len(text) > 3:
                patterns.append(text)
        
        # If no exact matches, try fuzzy matching
        if not patterns:
            # Group similar texts using fuzzy matching
            groups = []
            for text in texts:
                if len(text) <= 3:
                    continue
                
                # Find if this text is similar to any existing group
                found_group = False
                for group in groups:
                    # Check similarity with first item in group
                    similarity = SequenceMatcher(None, text, group[0]).ratio()
                    if similarity >= 0.85:
                        group.append(text)
                        found_group = True
                        break
                
                if not found_group:
                    groups.append([text])
            
            # Find groups that meet threshold
            for group in groups:
                if len(group) >= threshold:
                    # Use the most common variant in the group
                    patterns.append(max(set(group), key=group.count))
        
        return patterns
    
    def detect_page_numbers(self, text: str, footers: List[str] = None) -> List[str]:
        """
        Detect page numbers in various formats.
        
        Args:
            text: Input text
            footers: Optional list of footer text to extract page numbers from
            
        Returns:
            List of detected page number strings
        """
        page_numbers = []
        
        # First, extract page numbers from footers if provided
        if footers:
            for footer in footers:
                # Look for "Page X of Y" pattern in footer
                matches = re.findall(r'Page\s+\d+\s+of\s+\d+', footer, re.IGNORECASE)
                page_numbers.extend(matches)
        
        # Then look for standalone page numbers in text
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) > 20:  # Skip very long lines
                continue
            
            # Check against page number patterns
            # Skip single-letter roman numerals to avoid false positives
            for pattern in self.page_number_patterns:
                if pattern == r'^\s*[ivxlcdm]+\s*$':
                    # Only match roman numerals if they're 2+ characters
                    if re.match(r'^\s*[ivxlcdm]{2,}\s*$', line_stripped, re.IGNORECASE):
                        page_numbers.append(line_stripped)
                        break
                elif re.match(pattern, line_stripped, re.IGNORECASE):
                    page_numbers.append(line_stripped)
                    break
        
        return page_numbers
    
    def remove_repeated_artifacts(
        self,
        pages: List[PageResult],
        threshold: float = 0.7
    ) -> List[str]:
        """
        Detect and return repeated artifacts (watermarks, etc.) across pages.
        
        Args:
            pages: List of page results
            threshold: Minimum frequency (0.0-1.0) for artifact detection
            
        Returns:
            List of detected artifact patterns
        """
        if not pages or len(pages) < 2:
            return []
        
        # Collect all text blocks with their content
        all_text_blocks = []
        single_letters = []
        
        for page in pages:
            for block in page.text_blocks:
                text = block.text.strip()
                if text:
                    all_text_blocks.append(text)
                    # Track single letters separately (potential watermark letters)
                    if len(text) == 1 and text.isalpha():
                        single_letters.append(text)
        
        if not all_text_blocks:
            return []
        
        # Count occurrences
        text_counts = Counter(all_text_blocks)
        
        # Find text appearing on more than threshold% of pages
        min_count = len(pages) * threshold
        artifacts = [
            text for text, count in text_counts.items()
            if count >= min_count and len(text) > 2  # Ignore very short text
        ]
        
        # Check for single-letter watermarks that might spell a word
        if single_letters:
            letter_counts = Counter(single_letters)
            # If we have repeated single letters, check if they spell common watermarks
            repeated_letters = [
                letter for letter, count in letter_counts.items()
                if count >= min_count
            ]
            
            # Check if repeated letters spell "DRAFT"
            if set(repeated_letters) >= set(['D', 'R', 'A', 'F', 'T']):
                artifacts.append('DRAFT')
        
        return artifacts
    
    def clean_formatting_remnants(self, text: str) -> str:
        """
        Remove formatting remnants like orphaned bullets and table borders.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                cleaned_lines.append(line)
                continue
            
            # Check if line matches any formatting pattern (entire line is formatting)
            is_formatting = False
            for pattern in self.formatting_patterns:
                if re.match(pattern, line_stripped):
                    is_formatting = True
                    break
            
            # Keep line if it's not just formatting
            if not is_formatting:
                # Remove excessive punctuation at end of line
                line_stripped = re.sub(r'\.{3,}$', '', line_stripped)
                line_stripped = re.sub(r'[,:;!?]{3,}$', '', line_stripped)
                cleaned_lines.append(line_stripped)
        
        return '\n'.join(cleaned_lines)
    
    def clean_text(
        self,
        text: str,
        pages: List[PageResult],
        options: CleaningOptions
    ) -> str:
        """
        Apply full cleaning pipeline to text.
        
        Args:
            text: Input text to clean
            pages: List of page results for pattern detection
            options: Cleaning configuration options
            
        Returns:
            Cleaned text string
        """
        cleaned_text, _ = self.clean_text_with_metadata(text, pages, options)
        return cleaned_text
    
    def clean_text_with_metadata(
        self,
        text: str,
        pages: List[PageResult],
        options: CleaningOptions
    ) -> tuple[str, CleaningMetadata]:
        """
        Apply full cleaning pipeline to text and return metadata.
        
        Args:
            text: Input text to clean
            pages: List of page results for pattern detection
            options: Cleaning configuration options
            
        Returns:
            Tuple of (cleaned_text, cleaning_metadata)
        """
        cleaned = text
        headers_removed = []
        footers_removed = []
        page_numbers_removed = []
        artifacts_removed = []
        formatting_cleaned = False
        
        # 1. Remove headers and footers
        if options.remove_headers_footers and pages:
            header_footer_dict = self.detect_headers_footers(pages)
            headers_removed = header_footer_dict['headers']
            footers_removed = header_footer_dict['footers']
            
            # If page number removal is disabled, filter out footers containing page numbers
            if not options.remove_page_numbers:
                footers_to_keep = []
                footers_to_remove = []
                for footer in footers_removed:
                    # Check if footer contains page number pattern
                    if re.search(r'Page\s+\d+\s+of\s+\d+', footer, re.IGNORECASE):
                        footers_to_keep.append(footer)
                    else:
                        footers_to_remove.append(footer)
                footers_removed = footers_to_remove
            
            # Remove lines containing detected headers/footers
            lines = cleaned.split('\n')
            filtered_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    filtered_lines.append(line)
                    continue
                
                # Check if line matches any header
                is_header = False
                for header in headers_removed:
                    # Use fuzzy matching for headers
                    similarity = SequenceMatcher(None, line_stripped, header).ratio()
                    if similarity >= 0.8 or header in line_stripped:
                        is_header = True
                        break
                
                # Check if line matches any footer
                is_footer = False
                for footer in footers_removed:
                    # Use fuzzy matching for footers
                    similarity = SequenceMatcher(None, line_stripped, footer).ratio()
                    if similarity >= 0.8 or footer in line_stripped:
                        is_footer = True
                        break
                
                # Keep line if it's not a header or footer
                if not is_header and not is_footer:
                    filtered_lines.append(line)
            
            cleaned = '\n'.join(filtered_lines)
        
        # 2. Remove page numbers
        if options.remove_page_numbers:
            page_numbers_removed = self.detect_page_numbers(cleaned, footers_removed)
            for page_num in page_numbers_removed:
                # Use regex to remove page numbers (whole line)
                pattern = re.escape(page_num)
                cleaned = re.sub(f'^\\s*{pattern}\\s*$', '', cleaned, flags=re.MULTILINE)
        
        # 3. Remove repeated artifacts
        if options.remove_repeated_artifacts and pages:
            artifacts_removed = self.remove_repeated_artifacts(
                pages,
                options.artifact_threshold
            )
            for artifact in artifacts_removed:
                # Only remove if it's not already in headers/footers
                if artifact not in headers_removed and artifact not in footers_removed:
                    cleaned = cleaned.replace(artifact, '')
        
        # 4. Clean formatting remnants
        if options.clean_formatting:
            cleaned = self.clean_formatting_remnants(cleaned)
            formatting_cleaned = True
        
        # 5. Final cleanup - normalize excessive whitespace
        # Remove multiple blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        # Remove trailing whitespace from lines
        lines = cleaned.split('\n')
        cleaned = '\n'.join(line.rstrip() for line in lines)
        # Remove leading/trailing whitespace from entire text
        cleaned = cleaned.strip()
        
        # Create metadata
        total_removals = (
            len(headers_removed) +
            len(footers_removed) +
            len(page_numbers_removed) +
            len(artifacts_removed)
        )
        
        metadata = CleaningMetadata(
            headers_removed=headers_removed,
            footers_removed=footers_removed,
            page_numbers_removed=page_numbers_removed,
            artifacts_removed=artifacts_removed,
            formatting_cleaned=formatting_cleaned,
            total_removals=total_removals
        )
        
        return cleaned, metadata
