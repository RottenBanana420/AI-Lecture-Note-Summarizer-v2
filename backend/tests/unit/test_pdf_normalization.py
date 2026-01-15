"""
Unit tests for PDF text normalization.

These tests verify that text normalization logic correctly handles whitespace,
unicode, and special characters. Tests are IMMUTABLE.
"""

import pytest
from app.services.pdf_normalizer import PDFNormalizer


class TestWhitespaceNormalization:
    """Test whitespace normalization functions."""
    
    def test_multiple_spaces_collapsed(self):
        """Multiple consecutive spaces should collapse to single space."""
        normalizer = PDFNormalizer()
        
        text = "This  has   multiple    spaces"
        result = normalizer.normalize_whitespace(text)
        
        assert result == "This has multiple spaces"
        assert "  " not in result
    
    def test_tabs_converted_to_spaces(self):
        """Tabs should be converted to single spaces."""
        normalizer = PDFNormalizer()
        
        text = "Tab\tseparated\ttext"
        result = normalizer.normalize_whitespace(text)
        
        assert "\t" not in result
        assert "Tab separated text" == result
    
    def test_multiple_newlines_preserved_for_paragraphs(self):
        """Double newlines (paragraph breaks) should be preserved."""
        normalizer = PDFNormalizer()
        
        text = "Paragraph one.\n\nParagraph two."
        result = normalizer.normalize_whitespace(text)
        
        assert "\n\n" in result
    
    def test_excessive_newlines_collapsed(self):
        """More than 2 consecutive newlines should be collapsed."""
        normalizer = PDFNormalizer()
        
        text = "Line one.\n\n\n\n\nLine two."
        result = normalizer.normalize_whitespace(text)
        
        assert "\n\n\n" not in result
        # Should have at most double newlines
        assert result.count('\n') <= 2
    
    def test_leading_trailing_whitespace_removed(self):
        """Leading and trailing whitespace should be removed."""
        normalizer = PDFNormalizer()
        
        text = "   Text with spaces   "
        result = normalizer.normalize_whitespace(text)
        
        assert result == "Text with spaces"
    
    def test_carriage_returns_normalized(self):
        """Carriage returns should be normalized to newlines."""
        normalizer = PDFNormalizer()
        
        text = "Line one\r\nLine two\rLine three"
        result = normalizer.normalize_whitespace(text)
        
        assert "\r" not in result
        assert "Line one\nLine two\nLine three" == result


class TestUnicodeNormalization:
    """Test unicode normalization."""
    
    def test_nfc_normalization_applied(self):
        """Unicode should be normalized to NFC form."""
        normalizer = PDFNormalizer()
        
        # Combining characters: e + combining acute accent
        text = "cafe\u0301"  # café with combining accent
        result = normalizer.normalize_unicode(text)
        
        # Should be normalized to precomposed form
        assert result == "café"
    
    def test_combining_characters_normalized(self):
        """Combining characters should be normalized."""
        normalizer = PDFNormalizer()
        
        # Multiple combining characters
        text = "a\u0300\u0301"  # a with grave and acute accents
        result = normalizer.normalize_unicode(text)
        
        # Should be normalized (exact result depends on NFC rules)
        assert len(result) <= len(text)
    
    def test_ligatures_handled(self):
        """Ligatures should be handled appropriately."""
        normalizer = PDFNormalizer()
        
        # Common ligatures
        text = "ﬁ ﬂ ﬀ ﬃ ﬄ"  # fi, fl, ff, ffi, ffl ligatures
        result = normalizer.normalize_unicode(text)
        
        # Ligatures should either be preserved or expanded
        assert len(result) > 0


class TestSpecialCharacterHandling:
    """Test special character normalization."""
    
    def test_smart_quotes_normalized(self):
        """Smart quotes should be normalized to straight quotes."""
        normalizer = PDFNormalizer()
        
        text = "\u201csmart quotes\u201d and \u2018apostrophes\u2019"
        result = normalizer.normalize_special_characters(text)
        
        # Should convert to straight quotes
        assert '"smart quotes" and \'apostrophes\'' == result
    
    def test_em_dashes_preserved(self):
        """Em dashes should be preserved or normalized consistently."""
        normalizer = PDFNormalizer()
        
        text = "Text — with em dash"
        result = normalizer.normalize_special_characters(text)
        
        # Should contain either em dash or normalized equivalent
        assert "—" in result or " - " in result or "--" in result
    
    def test_bullet_points_preserved(self):
        """Bullet points should be preserved."""
        normalizer = PDFNormalizer()
        
        text = "• Item one\n• Item two"
        result = normalizer.normalize_special_characters(text)
        
        # Bullets should be preserved or converted to consistent format
        assert "•" in result or "*" in result or "-" in result


class TestFullNormalization:
    """Test complete normalization pipeline."""
    
    def test_normalize_text_applies_all_transformations(self):
        """Full normalization should apply all transformations."""
        normalizer = PDFNormalizer()
        
        text = "  Text  with\t\tmultiple   issues\n\n\n\nand  problems  "
        result = normalizer.normalize_text(text)
        
        # Should have no excessive whitespace
        assert "  " not in result
        assert "\t" not in result
        assert "\n\n\n" not in result
        assert result == result.strip()
    
    def test_empty_string_returns_empty(self):
        """Empty string should return empty string."""
        normalizer = PDFNormalizer()
        
        result = normalizer.normalize_text("")
        
        assert result == ""
    
    def test_whitespace_only_returns_empty(self):
        """Whitespace-only string should return empty string."""
        normalizer = PDFNormalizer()
        
        text = "   \t\n\n   "
        result = normalizer.normalize_text(text)
        
        assert result == ""
    
    def test_normalization_is_idempotent(self):
        """Normalizing already normalized text should not change it."""
        normalizer = PDFNormalizer()
        
        text = "This is already normalized text."
        result1 = normalizer.normalize_text(text)
        result2 = normalizer.normalize_text(result1)
        
        assert result1 == result2


class TestParagraphDetection:
    """Test paragraph structure detection and preservation."""
    
    def test_paragraph_breaks_detected(self):
        """Paragraph breaks should be detected from spacing."""
        normalizer = PDFNormalizer()
        
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = normalizer.normalize_text(text)
        
        # Should preserve paragraph structure
        paragraphs = result.split("\n\n")
        assert len(paragraphs) == 3
    
    def test_single_line_breaks_within_paragraphs_handled(self):
        """Single line breaks within paragraphs should be handled."""
        normalizer = PDFNormalizer()
        
        # PDF might break lines mid-sentence
        text = "This is a sentence that\nspans multiple lines\nin the PDF."
        result = normalizer.normalize_text(text)
        
        # Should either preserve or intelligently join
        assert len(result) > 0
        # Should not have excessive line breaks
        assert result.count('\n') <= text.count('\n')
