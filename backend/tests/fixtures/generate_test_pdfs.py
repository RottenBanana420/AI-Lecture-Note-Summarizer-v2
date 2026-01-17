"""
Script to generate test PDF fixtures for PDF extraction testing.

This script creates various PDF files with different characteristics to test
the robustness of the PDF extraction logic.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Frame, PageTemplate
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from pathlib import Path
import io

OUTPUT_DIR = Path(__file__).parent / "pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)


def create_clean_simple_pdf():
    """Create a simple, clean single-column PDF."""
    filepath = OUTPUT_DIR / "clean_simple.pdf"
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    story.append(Paragraph("Introduction to Machine Learning", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Content
    content = """
    Machine learning is a subset of artificial intelligence that focuses on the development
    of algorithms and statistical models that enable computers to improve their performance
    on a specific task through experience.
    
    The three main types of machine learning are supervised learning, unsupervised learning,
    and reinforcement learning. Each approach has its own strengths and use cases.
    """
    story.append(Paragraph(content, styles['BodyText']))
    
    doc.build(story)
    print(f"✓ Created: {filepath}")


def create_multi_column_pdf():
    """Create a two-column academic paper layout."""
    filepath = OUTPUT_DIR / "multi_column.pdf"
    
    def two_column_layout(canvas_obj, doc):
        """Custom page template with two columns."""
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica-Bold', 16)
        canvas_obj.drawCentredString(letter[0] / 2, letter[1] - 50, "Two-Column Academic Paper")
        canvas_obj.restoreState()
    
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    
    # Create two-column frame layout
    frame_width = (letter[0] - 3 * inch) / 2
    frame1 = Frame(inch, inch, frame_width, letter[1] - 2 * inch, id='col1')
    frame2 = Frame(inch + frame_width + inch, inch, frame_width, letter[1] - 2 * inch, id='col2')
    
    template = PageTemplate(id='TwoCol', frames=[frame1, frame2], onPage=two_column_layout)
    doc.addPageTemplates([template])
    
    story = []
    styles = getSampleStyleSheet()
    
    # Abstract
    story.append(Paragraph("Abstract", styles['Heading2']))
    story.append(Paragraph(
        "This paper presents a comprehensive analysis of neural network architectures. " * 5,
        styles['BodyText']
    ))
    story.append(Spacer(1, 12))
    
    # Introduction
    story.append(Paragraph("1. Introduction", styles['Heading2']))
    story.append(Paragraph(
        "Neural networks have revolutionized the field of machine learning. " * 10,
        styles['BodyText']
    ))
    
    # Methodology
    story.append(Paragraph("2. Methodology", styles['Heading2']))
    story.append(Paragraph(
        "Our approach utilizes convolutional neural networks for image classification. " * 10,
        styles['BodyText']
    ))
    
    doc.build(story)
    print(f"✓ Created: {filepath}")


def create_encoding_issues_pdf():
    """Create PDF with special characters and unicode."""
    filepath = OUTPUT_DIR / "encoding_issues.pdf"
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title with special characters
    story.append(Paragraph("Spëcîål Çhårāctërs & Ûñîçødé", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Content with various unicode characters
    special_content = """
    Mathematical symbols: α, β, γ, δ, ε, ∑, ∫, ∂, √, ∞, ≈, ≠, ≤, ≥
    
    Currency: $, €, £, ¥, ₹, ₽
    
    Accented characters: café, naïve, résumé, Zürich, São Paulo
    
    Quotes: "smart quotes" and 'apostrophes' — em dash – en dash
    
    Ligatures: fi fl ffi ffl
    
    Emoji and symbols: © ® ™ § ¶ † ‡ • ◦ ▪ ▫
    """
    story.append(Paragraph(special_content.replace('\n', '<br/>'), styles['BodyText']))
    
    doc.build(story)
    print(f"✓ Created: {filepath}")


def create_excessive_whitespace_pdf():
    """Create PDF with irregular spacing and line breaks."""
    filepath = OUTPUT_DIR / "excessive_whitespace.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Title
    c.drawString(100, 750, "Document    with    Excessive    Whitespace")
    
    # Content with irregular spacing
    y = 700
    lines = [
        "This  document  has  multiple  spaces  between  words.",
        "",
        "",
        "And     excessive     line     breaks.",
        "",
        "Some lines have trailing spaces.    ",
        "   And leading spaces.",
        "",
        "",
        "",
        "Multiple blank lines above.",
        "Tabs\t\tbetween\t\twords.",
    ]
    
    for line in lines:
        c.drawString(100, y, line)
        y -= 20
    
    c.save()
    print(f"✓ Created: {filepath}")


def create_mixed_content_pdf():
    """Create PDF with text, tables, and mixed content."""
    filepath = OUTPUT_DIR / "mixed_content.pdf"
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    story.append(Paragraph("Quarterly Report", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Text content
    story.append(Paragraph("Executive Summary", styles['Heading2']))
    story.append(Paragraph(
        "This report summarizes the key findings from Q4 2025. " * 5,
        styles['BodyText']
    ))
    story.append(Spacer(1, 12))
    
    # Table
    data = [
        ['Metric', 'Q3', 'Q4', 'Change'],
        ['Revenue', '$1.2M', '$1.5M', '+25%'],
        ['Users', '10,000', '15,000', '+50%'],
        ['Retention', '85%', '90%', '+5%'],
    ]
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 12))
    
    # More text
    story.append(Paragraph("Conclusion", styles['Heading2']))
    story.append(Paragraph(
        "The results demonstrate strong growth across all key metrics. " * 3,
        styles['BodyText']
    ))
    
    doc.build(story)
    print(f"✓ Created: {filepath}")


def create_empty_pages_pdf():
    """Create PDF with some empty pages."""
    filepath = OUTPUT_DIR / "empty_pages.pdf"
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Page 1: Content
    story.append(Paragraph("Page 1 - Content", styles['Title']))
    story.append(Paragraph("This page has content. " * 20, styles['BodyText']))
    story.append(PageBreak())
    
    # Page 2: Empty
    story.append(PageBreak())
    
    # Page 3: Content
    story.append(Paragraph("Page 3 - More Content", styles['Title']))
    story.append(Paragraph("This page also has content. " * 20, styles['BodyText']))
    story.append(PageBreak())
    
    # Page 4: Empty
    story.append(PageBreak())
    
    # Page 5: Content
    story.append(Paragraph("Page 5 - Final Content", styles['Title']))
    story.append(Paragraph("Last page with content. " * 10, styles['BodyText']))
    
    doc.build(story)
    print(f"✓ Created: {filepath}")


def create_complex_layout_pdf():
    """Create PDF with complex layout including text boxes and sidebars."""
    filepath = OUTPUT_DIR / "complex_layout.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter
    
    # Main title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 50, "Complex Layout Document")
    
    # Sidebar (right side)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.rect(width - 150, 100, 130, height - 200, fill=True, stroke=True)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 140, height - 80, "Quick Facts")
    c.setFont("Helvetica", 8)
    c.drawString(width - 140, height - 100, "• Fact 1")
    c.drawString(width - 140, height - 115, "• Fact 2")
    c.drawString(width - 140, height - 130, "• Fact 3")
    
    # Main content area
    c.setFont("Helvetica", 11)
    y = height - 100
    main_text = [
        "This document has a complex layout with a sidebar on the right.",
        "The main content flows in the left column.",
        "",
        "Reading order should be preserved correctly:",
        "1. Main title at the top",
        "2. Main content in the left area",
        "3. Sidebar content on the right",
        "",
        "Text extraction must handle this layout intelligently.",
    ]
    
    for line in main_text:
        c.drawString(50, y, line)
        y -= 15
    
    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width / 2, 50, "Page 1 of 1")
    
    c.save()
    print(f"✓ Created: {filepath}")


def create_multipage_pdf():
    """Create a multi-page PDF to test page ordering."""
    filepath = OUTPUT_DIR / "multipage.pdf"
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    for page_num in range(1, 6):
        story.append(Paragraph(f"Page {page_num}", styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            f"This is the content of page {page_num}. " * 30,
            styles['BodyText']
        ))
        if page_num < 5:
            story.append(PageBreak())
    
    doc.build(story)
    print(f"✓ Created: {filepath}")


def create_pdf_with_noise():
    """Create PDF with realistic noise patterns for testing cleaning logic."""
    filepath = OUTPUT_DIR / "pdf_with_noise.pdf"
    
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter
    
    # Create 5 pages with consistent noise patterns
    for page_num in range(1, 6):
        # Header (consistent across all pages)
        c.setFont("Helvetica", 9)
        c.drawString(50, height - 30, "CS 101 - Introduction to Machine Learning")
        c.drawString(width - 150, height - 30, "Fall 2025")
        
        # Watermark (repeated artifact)
        c.setFont("Helvetica-Bold", 60)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.saveState()
        c.translate(width / 2, height / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "DRAFT")
        c.restoreState()
        c.setFillColorRGB(0, 0, 0)
        
        # Main content
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 80, f"Lecture {page_num}: Neural Networks")
        
        c.setFont("Helvetica", 11)
        y = height - 120
        
        content_lines = [
            "This lecture covers the fundamentals of neural networks.",
            "",
            "Key Topics:",
            "• Perceptrons and activation functions",
            "• Backpropagation algorithm",
            "• Gradient descent optimization",
            "",
            "Neural networks are computational models inspired by biological",
            "neural networks. They consist of interconnected nodes (neurons)",
            "organized in layers. Each connection has an associated weight",
            "that adjusts during the learning process.",
            "",
            "The learning process involves:",
            "1. Forward propagation of inputs",
            "2. Calculation of error/loss",
            "3. Backward propagation of gradients",
            "4. Weight updates using optimization algorithms",
        ]
        
        for line in content_lines:
            c.drawString(50, y, line)
            y -= 15
        
        # Footer (consistent across all pages)
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(50, 40, "© 2025 University of AI | Confidential")
        c.drawCentredString(width / 2, 40, f"Page {page_num} of 5")
        c.drawString(width - 100, 40, "Do Not Distribute")
        
        c.showPage()
    
    c.save()
    print(f"✓ Created: {filepath}")


if __name__ == "__main__":
    print("Generating test PDF fixtures...")
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    try:
        create_clean_simple_pdf()
        create_multi_column_pdf()
        create_encoding_issues_pdf()
        create_excessive_whitespace_pdf()
        create_mixed_content_pdf()
        create_empty_pages_pdf()
        create_complex_layout_pdf()
        create_multipage_pdf()
        create_pdf_with_noise()
        
        print(f"\n✓ Successfully generated {len(list(OUTPUT_DIR.glob('*.pdf')))} test PDFs")
    except Exception as e:
        print(f"\n✗ Error generating PDFs: {e}")
        raise
