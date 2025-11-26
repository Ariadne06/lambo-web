"""
PDF template for generating individual resident detail reports.
Uses get_specific_resident() function to retrieve all resident information.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime
from ..base import draw_barangay_header, get_standard_styles, draw_watermark


class ResidentDetailCanvas(canvas.Canvas):
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
        """Draw header and watermark on each page."""
        width, height = A4
        draw_watermark(self, width, height, "OFFICIAL DOCUMENT")
        draw_barangay_header(self, width, height, top_margin=0.5*inch)


def generate_resident_detail_pdf(resident_data):
    """
    Generate a well-designed PDF report for individual resident details.
    
    Args:
        resident_data: Dictionary from get_specific_resident() containing all resident info
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    # Build document title from resident name
    name_parts = [
        resident_data.get('first_name', ''),
        resident_data.get('last_name', '')
    ]
    resident_name = ' '.join(part for part in name_parts if part and part != 'None').strip() or 'Resident'
    doc_title = f"{resident_name} - Resident Profile"
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=1.75*inch,  # Reduced to match list design
        bottomMargin=0.75*inch,
        title=doc_title,
        author='LAMBO System',
        subject='Resident Profile Report'
    )
    
    elements = []
    styles = get_standard_styles()
    
    # Custom styles using Times-Roman
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=17,
        textColor=colors.HexColor('#991B1B'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Times-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Times-Roman'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.white,
        spaceBefore=10,
        spaceAfter=2,
        alignment=TA_LEFT,
        fontName='Times-Bold',
        backColor=colors.HexColor('#991B1B'),
        leftIndent=6,
        rightIndent=6
    )
    
    metadata_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_LEFT,
        fontName='Times-Roman'
    )
    
    # Label style for table headers
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#374151'),
        fontName='Times-Bold'
    )
    
    # Value style for table data
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#374151'),
        fontName='Times-Roman'
    )
    
    # Header
    elements.append(Paragraph("RESIDENT PROFILE", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # SECTION 1: Personal Information
    header_table = Table([[Paragraph("PERSONAL INFORMATION", section_header_style)]], colWidths=[7.0*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0)
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    
    # Build full name without None values
    name_parts = [
        resident_data.get('first_name', ''),
        resident_data.get('middle_name', ''),
        resident_data.get('last_name', ''),
        resident_data.get('suffix', '')
    ]
    full_name = ' '.join(part for part in name_parts if part and part != 'None').strip() or '—'
    
    # Resident Code - 2 column table
    resident_code_data = [
        [Paragraph('Resident Code:', label_style), Paragraph(str(resident_data.get('resident_code', '—')), value_style)]
    ]
    resident_code_table = Table(resident_code_data, colWidths=[1.5*inch, 5.5*inch])
    resident_code_table.setStyle(_get_data_table_style())
    elements.append(resident_code_table)
    
    # Full Name - 2 column table
    full_name_data = [
        [Paragraph('Full Name:', label_style), Paragraph(full_name, value_style)]
    ]
    full_name_table = Table(full_name_data, colWidths=[1.5*inch, 5.5*inch])
    full_name_table.setStyle(_get_data_table_style())
    elements.append(full_name_table)
    
    # Rest of personal data - 4 column table
    personal_data = [
        [Paragraph('Sex:', label_style), Paragraph(str(resident_data.get('sex', '—')), value_style), Paragraph('Date of Birth:', label_style), Paragraph(_format_date(resident_data.get('dob')), value_style)],
        [Paragraph('Age:', label_style), Paragraph(str(resident_data.get('age', '—')), value_style), Paragraph('Status:', label_style), Paragraph(str(resident_data.get('resident_status', '—')), value_style)]
    ]
    
    personal_table = Table(personal_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
    personal_table.setStyle(_get_data_table_style())
    elements.append(personal_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # SECTION 2: Contact Information
    header_table = Table([[Paragraph("CONTACT INFORMATION", section_header_style)]], colWidths=[7.0*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    
    contact_data = [
        [Paragraph('Phone Number:', label_style), Paragraph(str(resident_data.get('phone_number', '—')), value_style), Paragraph('Email:', label_style), Paragraph(str(resident_data.get('email', '—')), value_style)]
    ]
    
    contact_table = Table(contact_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
    contact_table.setStyle(_get_data_table_style())
    elements.append(contact_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # SECTION 3: Demographics
    header_table = Table([[Paragraph("DEMOGRAPHICS", section_header_style)]], colWidths=[7.0*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    
    demographics_data = [
        [Paragraph('Civil Status:', label_style), Paragraph(str(resident_data.get('civil_status', '—')), value_style), Paragraph('Nationality:', label_style), Paragraph(str(resident_data.get('nationality', '—')), value_style)],
        [Paragraph('Religion:', label_style), Paragraph(str(resident_data.get('religion', '—')), value_style), Paragraph('Education:', label_style), Paragraph(str(resident_data.get('educational_attainment', '—')), value_style)],
        [Paragraph('Occupation:', label_style), Paragraph(str(resident_data.get('occupation', '—')), value_style), Paragraph('Employment:', label_style), Paragraph(str(resident_data.get('employment_status', '—')), value_style)]
    ]
    
    demographics_table = Table(demographics_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
    demographics_table.setStyle(_get_data_table_style())
    elements.append(demographics_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # SECTION 4: Residency Information
    header_table = Table([[Paragraph("RESIDENCY INFORMATION", section_header_style)]], colWidths=[7.0*inch])
    header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    
    # Filter out None values
    household_num = resident_data.get('household_number')
    household_display = str(household_num) if household_num and str(household_num) != 'None' else '—'
    
    family_code = resident_data.get('family_code')
    family_display = str(family_code) if family_code and str(family_code) != 'None' else '—'
    
    full_address = resident_data.get('full_address')
    address_display = str(full_address) if full_address and str(full_address) != 'None' else '—'
    
    # Household and Family Code - 4 column table
    residency_data = [
        [Paragraph('Household Number:', label_style), Paragraph(household_display, value_style), Paragraph('Family Code:', label_style), Paragraph(family_display, value_style)]
    ]
    residency_table = Table(residency_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
    residency_table.setStyle(_get_data_table_style())
    elements.append(residency_table)
    
    # Full Address - 2 column table
    address_data = [
        [Paragraph('Full Address:', label_style), Paragraph(address_display, value_style)]
    ]
    address_table = Table(address_data, colWidths=[1.5*inch, 5.5*inch])
    address_table.setStyle(_get_data_table_style())
    elements.append(address_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # SECTION 5: Businesses (if any)
    businesses = resident_data.get('businesses')
    if businesses:
        # Handle JSONB data
        if isinstance(businesses, str):
            import json
            try:
                businesses = json.loads(businesses)
            except:
                businesses = None
        
        if businesses and len(businesses) > 0:
            header_table = Table([[Paragraph("BUSINESS OWNERSHIP", section_header_style)]], colWidths=[7.0*inch])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0)
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 4))
            
            # Create table with headers
            table_data = [[
                Paragraph('<b>Business Name</b>', label_style),
                Paragraph('<b>Category</b>', label_style),
                Paragraph('<b>Address</b>', label_style),
                Paragraph('<b>Status</b>', label_style)
            ]]
            
            # Add business rows
            for biz in businesses:
                biz_name = str(biz.get('business_name', '—'))
                category = str(biz.get('clearance_category_name', '—'))
                # Replace peso sign with PHP text for PDF compatibility
                category = category.replace('₱', 'PHP ')
                biz_address = str(biz.get('full_address', '—'))
                biz_status = str(biz.get('business_status_name', '—'))
                
                table_data.append([
                    Paragraph(biz_name, value_style),
                    Paragraph(category, value_style),
                    Paragraph(biz_address, value_style),
                    Paragraph(biz_status, value_style)
                ])
            
            # Create table with appropriate column widths
            business_table = Table(table_data, colWidths=[1.8*inch, 1.5*inch, 2.5*inch, 1.2*inch])
            business_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                
                # Alignment
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#991B1B')),
                
                # Alternating row colors for data rows
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
            ]))
            elements.append(business_table)
            elements.append(Spacer(1, 0.05*inch))
    
    # Footer Metadata
    elements.append(Spacer(1, 0.05*inch))
    current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
    elements.append(Paragraph(f"<b>Generated:</b> {current_date}", metadata_style))
    
    elements.append(Spacer(1, 0.05*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER,
        fontName='Times-Italic'
    )
    elements.append(Paragraph(
        "This document is an official record of the LAMBO System. "
        "For verification purposes, please contact the Barangay Secretary's Office.",
        footer_style
    ))
    
    # Page number footer
    def add_page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Times-Roman', 8)
        canvas.setFillColor(colors.HexColor('#6B7280'))
        
        # Page number
        page_num = f"Page {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
        
        # Confidential notice
        canvas.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
        
        canvas.restoreState()
    
    # Build PDF with custom canvas
    doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer, 
              canvasmaker=ResidentDetailCanvas)
    
    buffer.seek(0)
    return buffer


def _format_date(date_value):
    """Format date for display"""
    if not date_value:
        return '—'
    if hasattr(date_value, 'strftime'):
        return date_value.strftime('%B %d, %Y')
    return str(date_value)


def _get_data_table_style():
    """Returns consistent table style for data sections"""
    return TableStyle([
        # Header cells (column 0 and 2) - labels
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        
        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding - increased to prevent overlap
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
    ])
