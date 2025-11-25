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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime


def generate_resident_detail_pdf(resident_data):
    """
    Generate a well-designed PDF report for individual resident details.
    
    Args:
        resident_data: Dictionary from get_specific_resident() containing all resident info
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#991B1B'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.white,
        spaceAfter=8,
        spaceBefore=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#991B1B'),
        leftIndent=10,
        rightIndent=10,
        spaceAfter=0
    )
    
    field_label_style = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6B7280'),
        fontName='Helvetica-Bold',
        spaceAfter=2
    )
    
    field_value_style = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#111827'),
        fontName='Helvetica',
        spaceAfter=8
    )
    
    header_info_style = ParagraphStyle(
        'HeaderInfo',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_RIGHT,
        fontName='Helvetica'
    )
    
    # Header
    elements.append(Paragraph("RESIDENT INFORMATION PROFILE", title_style))
    elements.append(Paragraph("Official Barangay Document", subtitle_style))
    
    # Generate date
    current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
    elements.append(Paragraph(f"Generated: {current_date}", header_info_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Resident ID Badge (prominent display)
    id_data = [
        ['Resident ID:', str(resident_data.get('resident_id', '—'))],
        ['Resident Code:', resident_data.get('resident_code', '—')],
        ['Status:', resident_data.get('resident_status', '—')]
    ]
    
    id_table = Table(id_data, colWidths=[1.5*inch, 4.5*inch])
    id_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF2F2')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#991B1B')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#991B1B')),
        ('LINEBELOW', (0, 0), (-1, 1), 0.5, colors.HexColor('#FECACA')),
    ]))
    elements.append(id_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # SECTION 1: Personal Information
    section_title = Paragraph("PERSONAL INFORMATION", section_header_style)
    elements.append(section_title)
    elements.append(Spacer(1, 2))
    
    personal_data = [
        ['First Name', resident_data.get('first_name', '—'), 'Middle Name', resident_data.get('middle_name', '—')],
        ['Last Name', resident_data.get('last_name', '—'), 'Suffix', resident_data.get('suffix', '—')],
        ['Sex', resident_data.get('sex', '—'), 'Date of Birth', _format_date(resident_data.get('dob'))],
        ['Age', str(resident_data.get('age', '—')), '', '']
    ]
    
    personal_table = Table(personal_data, colWidths=[1.4*inch, 1.9*inch, 1.4*inch, 1.9*inch])
    personal_table.setStyle(_get_data_table_style())
    elements.append(personal_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # SECTION 2: Contact Information
    section_title = Paragraph("CONTACT INFORMATION", section_header_style)
    elements.append(section_title)
    elements.append(Spacer(1, 2))
    
    contact_data = [
        ['Phone Number', resident_data.get('phone_number', '—'), 'Email Address', resident_data.get('email', '—')]
    ]
    
    contact_table = Table(contact_data, colWidths=[1.4*inch, 1.9*inch, 1.4*inch, 1.9*inch])
    contact_table.setStyle(_get_data_table_style())
    elements.append(contact_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # SECTION 3: Demographics
    section_title = Paragraph("DEMOGRAPHICS", section_header_style)
    elements.append(section_title)
    elements.append(Spacer(1, 2))
    
    demographics_data = [
        ['Civil Status', resident_data.get('civil_status', '—'), 'Nationality', resident_data.get('nationality', '—')],
        ['Religion', resident_data.get('religion', '—'), 'Educational Attainment', resident_data.get('educational_attainment', '—')],
        ['Occupation', resident_data.get('occupation', '—'), 'Employment Status', resident_data.get('employment_status', '—')]
    ]
    
    demographics_table = Table(demographics_data, colWidths=[1.4*inch, 1.9*inch, 1.4*inch, 1.9*inch])
    demographics_table.setStyle(_get_data_table_style())
    elements.append(demographics_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # SECTION 4: Residency Information
    section_title = Paragraph("RESIDENCY INFORMATION", section_header_style)
    elements.append(section_title)
    elements.append(Spacer(1, 2))
    
    residency_data = [
        ['Household Number', resident_data.get('household_number', '—'), 'Family Code', resident_data.get('family_code', '—')],
        ['Full Address', resident_data.get('full_address', '—'), '', '']
    ]
    
    residency_table = Table(residency_data, colWidths=[1.4*inch, 1.9*inch, 1.4*inch, 1.9*inch])
    residency_table.setStyle(_get_data_table_style())
    elements.append(residency_table)
    
    # Footer Section
    elements.append(Spacer(1, 0.5*inch))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    elements.append(Paragraph(
        "This document is an official record of the Barangay Management System.<br/>"
        "For verification purposes, please contact the Barangay Secretary's Office.",
        footer_style
    ))
    
    # Page number footer
    def add_page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#9CA3AF'))
        
        # Page number
        page_num = f"Page {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - 0.75*inch, 0.5*inch, page_num)
        
        # Confidential notice
        canvas.drawString(0.75*inch, 0.5*inch, "CONFIDENTIAL - Barangay Use Only")
        
        canvas.restoreState()
    
    # Build PDF
    doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
    
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
        # Header cells (column 0 and 2)
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 9),
        ('FONTSIZE', (2, 0), (2, -1), 9),
        
        # Value cells (column 1 and 3)
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
        ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor('#111827')),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 10),
        ('FONTSIZE', (3, 0), (3, -1), 10),
        
        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('ALIGN', (3, 0), (3, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D1D5DB')),
    ])
