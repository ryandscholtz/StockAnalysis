#!/usr/bin/env python3
"""
Create a simple test PDF for Textract testing
"""
import os
import sys

def create_simple_pdf():
    """Create a simple PDF with text"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Create a simple PDF
        pdf_path = "simple_test.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Add some text
        c.drawString(100, 750, "Test Financial Statement")
        c.drawString(100, 700, "Revenue: $1,000,000")
        c.drawString(100, 650, "Net Income: $200,000")
        c.drawString(100, 600, "Total Assets: $5,000,000")
        
        # Add a simple table
        c.drawString(100, 500, "Income Statement")
        c.drawString(100, 480, "2024        2023")
        c.drawString(100, 460, "Revenue     $1,000,000  $900,000")
        c.drawString(100, 440, "Expenses    $800,000    $750,000")
        c.drawString(100, 420, "Net Income  $200,000    $150,000")
        
        c.save()
        
        print(f"Created simple PDF: {pdf_path}")
        return pdf_path
        
    except ImportError:
        print("reportlab not installed. Installing...")
        os.system("pip install reportlab")
        return create_simple_pdf()

if __name__ == "__main__":
    create_simple_pdf()