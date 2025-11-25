"""
Base PDF Generator using ReportLab.
Provides common utilities and styling for all PDF reports.
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime


class BasePDFGenerator:
    """Base class for all PDF report generators."""
    
    def __init__(self, title="Report", pagesize=A4):
        """
        Initialize PDF generator.
        
        Args:
            title: Report title
            pagesize: Page size (default: A4)
        """
        self.title = title
        self.pagesize = pagesize
        self.width, self.height = pagesize
        self.styles = getSampleStyleSheet()
        self.buffer = BytesIO()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for the report."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        # Small text
        self.styles.add(ParagraphStyle(
            name='CustomSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6b7280'),
            fontName='Helvetica'
        ))
    
    def create_header(self, canvas, doc):
        """
        Create page header.
        
        Args:
            canvas: ReportLab canvas
            doc: Document object
        """
        canvas.saveState()
        
        # Add barangay logo if available
        # logo_path = 'static/images/barangay_logo.png'
        # try:
        #     canvas.drawImage(logo_path, 0.75*inch, self.height - 1.5*inch, 
        #                     width=1*inch, height=1*inch, preserveAspectRatio=True)
        # except:
        #     pass
        
        # Header text
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawCentredString(self.width / 2, self.height - 0.75*inch, 
                                'BARANGAY CANASAGA')
        
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(self.width / 2, self.height - 0.95*inch, 
                                'Consolacion, Cebu')
        
        # Horizontal line
        canvas.setStrokeColor(colors.HexColor('#e5e7eb'))
        canvas.setLineWidth(1)
        canvas.line(0.75*inch, self.height - 1.1*inch, 
                   self.width - 0.75*inch, self.height - 1.1*inch)
        
        canvas.restoreState()
    
    def create_footer(self, canvas, doc):
        """
        Create page footer.
        
        Args:
            canvas: ReportLab canvas
            doc: Document object
        """
        canvas.saveState()
        
        # Footer line
        canvas.setStrokeColor(colors.HexColor('#e5e7eb'))
        canvas.setLineWidth(1)
        canvas.line(0.75*inch, 0.75*inch, self.width - 0.75*inch, 0.75*inch)
        
        # Page number
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6b7280'))
        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.width - 0.75*inch, 0.5*inch, page_num)
        
        # Generation timestamp
        timestamp = datetime.now().strftime('%B %d, %Y %I:%M %p')
        canvas.drawString(0.75*inch, 0.5*inch, f"Generated: {timestamp}")
        
        canvas.restoreState()
    
    def create_table(self, data, col_widths=None, style=None):
        """
        Create a styled table.
        
        Args:
            data: List of lists containing table data
            col_widths: List of column widths (optional)
            style: Custom TableStyle (optional)
        
        Returns:
            Table object
        """
        if not style:
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ])
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(style)
        return table
    
    def generate(self):
        """
        Generate the PDF document.
        Must be implemented by subclasses.
        
        Returns:
            BytesIO buffer containing the PDF
        """
        raise NotImplementedError("Subclasses must implement generate()")
