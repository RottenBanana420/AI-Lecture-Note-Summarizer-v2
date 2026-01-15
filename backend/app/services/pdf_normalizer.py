"""
PDF text normalization utilities.

Provides functions for cleaning and normalizing extracted PDF text.
"""

import re
import unicodedata
from typing import Optional


class PDFNormalizer:
    """Utility class for normalizing extracted PDF text."""
    
    def __init__(self):
        """Initialize the normalizer."""
        # Smart quote mappings
        self.quote_map = {
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u2032': "'",  # Prime
            '\u2033': '"',  # Double prime
        }
        
        # Dash mappings
        self.dash_map = {
            '\u2013': '-',  # En dash
            '\u2014': '--',  # Em dash
            '\u2015': '--',  # Horizontal bar
        }
    
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text.
        
        - Converts tabs to spaces
        - Collapses multiple spaces to single space
        - Normalizes line endings
        - Preserves paragraph breaks (double newlines)
        - Removes leading/trailing whitespace
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Convert carriage returns to newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Convert tabs to spaces
        text = text.replace('\t', ' ')
        
        # Collapse multiple spaces to single space (but preserve newlines)
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Collapse multiple spaces within line
            line = re.sub(r' +', ' ', line)
            # Remove leading/trailing whitespace from line
            line = line.strip()
            normalized_lines.append(line)
        
        # Join lines back together
        text = '\n'.join(normalized_lines)
        
        # Collapse excessive newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from entire text
        text = text.strip()
        
        return text
    
    def normalize_unicode(self, text: str) -> str:
        """
        Normalize unicode characters.
        
        - Applies NFC normalization
        - Handles combining characters
        - Preserves or expands ligatures
        
        Args:
            text: Input text
            
        Returns:
            Unicode-normalized text
        """
        if not text:
            return ""
        
        # Apply NFC normalization (canonical composition)
        text = unicodedata.normalize('NFC', text)
        
        return text
    
    def normalize_special_characters(self, text: str) -> str:
        """
        Normalize special characters.
        
        - Converts smart quotes to straight quotes
        - Normalizes dashes
        - Preserves bullet points and other symbols
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized special characters
        """
        if not text:
            return ""
        
        # Replace smart quotes
        for smart, straight in self.quote_map.items():
            text = text.replace(smart, straight)
        
        # Replace dashes
        for fancy_dash, simple_dash in self.dash_map.items():
            text = text.replace(fancy_dash, simple_dash)
        
        return text
    
    def normalize_text(self, text: str) -> str:
        """
        Apply full normalization pipeline.
        
        Applies all normalization steps in order:
        1. Unicode normalization
        2. Special character normalization
        3. Whitespace normalization
        
        Args:
            text: Input text
            
        Returns:
            Fully normalized text
        """
        if not text:
            return ""
        
        # Apply normalizations in order
        text = self.normalize_unicode(text)
        text = self.normalize_special_characters(text)
        text = self.normalize_whitespace(text)
        
        return text
    
    def detect_paragraphs(self, text: str) -> list[str]:
        """
        Detect paragraph boundaries in text.
        
        Args:
            text: Input text
            
        Returns:
            List of paragraphs
        """
        if not text:
            return []
        
        # Split on double newlines (paragraph breaks)
        paragraphs = text.split('\n\n')
        
        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
