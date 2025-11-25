"""
PDF template for generating filtered resident list reports.
Uses get_all_residents() function with applied filters.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from .base import draw_barangay_header, get_standard_styles


class ResidentListCanvas(canvas.Canvas):
    """Custom canvas that draws the barangay header on each page."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
    
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def draw_page_decorations(self):
        """Draw header on each page."""
        width, height = A4
        draw_barangay_header(self, width, height, top_margin=0.5*inch)


def generate_resident_list_pdf(residents, filters_applied, total_count):
    """
    Generate a well-designed PDF report for resident list with filters.
    
    Args:
        residents: List of resident dictionaries from get_all_residents()
        filters_applied: Dictionary containing applied filter information
        total_count: Total number of residents matching filters
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    # Use portrait orientation
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=2.25*inch,  # Increased to accommodate header
        bottomMargin=0.75*inch
    )
    
    elements = []
    styles = get_standard_styles()
    
    # Custom styles using Times-Roman
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#991B1B'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Times-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Times-Roman'
    )
    
    filter_style = ParagraphStyle(
        'FilterStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        spaceAfter=4,
        alignment=TA_LEFT,
        fontName='Times-Roman'
    )
    
    header_info_style = ParagraphStyle(
        'HeaderInfo',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_RIGHT,
        fontName='Times-Roman'
    )
    
    # Header
    elements.append(Paragraph("BARANGAY RESIDENT LIST REPORT", title_style))
    elements.append(Paragraph("Official Document", subtitle_style))
    
    # Date and total count info
    current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
    elements.append(Paragraph(f"Generated: {current_date}", header_info_style))
    elements.append(Paragraph(f"Total Residents: <b>{total_count}</b>", header_info_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Applied Filters Section
    if filters_applied and any(filters_applied.values()):
        elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
        elements.append(Spacer(1, 0.05*inch))
        
        filter_data = []
        if filters_applied.get('search_query'):
            filter_data.append(['Search Query:', filters_applied['search_query']])
        if filters_applied.get('status'):
            filter_data.append(['Resident Status:', ', '.join(filters_applied['status'])])
        if filters_applied.get('sitio'):
            filter_data.append(['Sitio:', ', '.join(filters_applied['sitio'])])
        
        if filter_data:
            filter_table = Table(filter_data, colWidths=[1.3*inch, 5.2*inch])
            filter_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ]))
            elements.append(filter_table)
            elements.append(Spacer(1, 0.15*inch))
    else:
        elements.append(Paragraph("<b>Filters:</b> None (All Residents)", filter_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Resident List Table
    if residents:
        # Table headers
        table_data = [[
            'Code',
            'Full Name',
            'DOB',
            'Contact',
            'Address',
            'Status'
        ]]
        
        # Table rows
        for resident in residents:
            # Format DOB
            dob = resident.get('dob', '')
            if dob and hasattr(dob, 'strftime'):
                dob = dob.strftime('%m/%d/%Y')
            elif dob:
                dob = str(dob)
            else:
                dob = '—'
            
            # Format phone
            phone = resident.get('phone_number') or '—'
            
            # Use Paragraph for address to handle wrapping
            address = resident.get('full_address') or '—'
            if len(address) > 35:
                address = address[:32] + '...'
            
            # Format full name with age and sex
            full_name = resident.get('full_name') or '—'
            age = resident.get('age')
            sex = resident.get('sex')
            name_line = full_name
            if age or sex:
                details = []
                if age:
                    details.append(f"{age}yo")
                if sex:
                    details.append(sex)
                name_line = f"{full_name}\n({', '.join(details)})"
            
            table_data.append([
                resident.get('resident_code') or '—',
                name_line,
                dob,
                phone,
                address,
                resident.get('resident_status') or '—'
            ])
        
        # Create table with proper column widths for portrait
        col_widths = [0.9*inch, 2.0*inch, 0.9*inch, 1.0*inch, 1.6*inch, 0.9*inch]
        
        resident_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Table styling
        resident_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Code
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Name
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # DOB
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),    # Contact
            ('ALIGN', (4, 1), (4, -1), 'LEFT'),    # Address
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Status
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ]))
        
        elements.append(resident_table)
    else:
        # No residents found
        no_data_style = ParagraphStyle(
            'NoData',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER,
            fontName='Times-Italic'
        )
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("No residents found matching the specified filters.", no_data_style))
    
    # Footer with page numbers
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Times-Roman', 8)
        canvas.setFillColor(colors.HexColor('#6B7280'))
        page_num = f"Page {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
        canvas.drawString(0.5*inch, 0.5*inch, "Barangay Management System - Confidential Document")
        canvas.restoreState()
    
    # Build PDF with custom canvas
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number,
              canvasmaker=ResidentListCanvas)
    
    buffer.seek(0)
    return buffer
