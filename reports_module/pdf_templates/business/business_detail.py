"""
Business Detail PDF Report Generator
Generates detailed business profile with complete information
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
from decimal import Decimal
from ..base import draw_barangay_header, get_standard_styles, draw_watermark
from django.db import connection


class BusinessDetailCanvas(canvas.Canvas):
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


def _get_data_table_style():
    """Return standard table style for data tables."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ])


class BusinessDetailPDF:
    """Generates a detailed business profile PDF report."""
    
    def __init__(self, business_id):
        """Initialize with business ID."""
        self.business_id = int(business_id)
    
    def _get_business(self):
        """Fetch business details using database function."""
        with connection.cursor() as cursor:
            cursor.callproc('get_business_detail', [self.business_id])
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            if rows:
                return dict(zip(cols, rows[0]))
            return None
    
    def _generate_error_pdf(self, buffer, error_message):
        """Generate an error PDF when business is not found."""
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = get_standard_styles()
        
        error_style = ParagraphStyle(
            'Error',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.red,
            alignment=TA_CENTER
        )
        
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph(error_message, error_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        business = self._get_business()
        if not business:
            return self._generate_error_pdf(buffer, "Business not found")
        
        # Build document title
        business_name = business.get('business_name', 'Unknown')
        doc_title = f"{business_name} - Business Profile"
        
        # Create document with custom header/footer
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title=doc_title,
            author='LAMBO System',
            subject='Business Profile Report'
        )
        
        # Build elements
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
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Bold'
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Roman'
        )
        
        # Title
        elements.append(Paragraph("BUSINESS PROFILE", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # SECTION 1: Business Information
        header_table = Table([[Paragraph("BUSINESS INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        business_info = [
            ["Business ID:", str(business.get('business_id', '—'))],
            ["Business Name:", business.get('business_name', '—')],
            ["Owner Name:", business.get('owner_name', '—')],
            ["Business Type:", business.get('business_type_name') or business.get('business_type', '—')],
            ["Nature of Business:", business.get('nature_of_business', '—')],
            ["Ownership:", business.get('ownership_name') or business.get('ownership', '—')],
            ["Status:", business.get('business_status_name') or business.get('status', '—')],
        ]
        
        business_table_data = []
        for label, value in business_info:
            business_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        business_table = Table(business_table_data, colWidths=[1.8*inch, 5.2*inch])
        business_table.setStyle(_get_data_table_style())
        elements.append(business_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 2: Financial Information
        header_table = Table([[Paragraph("FINANCIAL INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Format gross income
        gross_income = business.get('total_gross_income')
        if gross_income:
            if isinstance(gross_income, Decimal):
                gross_income_str = f"Php {gross_income:,.2f}"
            else:
                try:
                    gross_income_str = f"Php {float(gross_income):,.2f}"
                except:
                    gross_income_str = str(gross_income)
        else:
            gross_income_str = "—"
        
        financial_info = [
            ["Total Gross Income:", gross_income_str],
            ["Clearance Category:", business.get('clearance_category_name') or business.get('clearance_category', '—')],
        ]
        
        financial_table_data = []
        for label, value in financial_info:
            financial_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        financial_table = Table(financial_table_data, colWidths=[1.8*inch, 5.2*inch])
        financial_table.setStyle(_get_data_table_style())
        elements.append(financial_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 3: Registration Details
        header_table = Table([[Paragraph("REGISTRATION DETAILS", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Format clearance date
        clearance_date = business.get('clearance_date_issued')
        if clearance_date:
            if hasattr(clearance_date, 'strftime'):
                clearance_date_str = clearance_date.strftime('%B %d, %Y')
            else:
                clearance_date_str = str(clearance_date)
        else:
            clearance_date_str = "—"
        
        registration_info = [
            ["DTI/SEC/CDA Reg. Number:", business.get('dti_sec_cda_reg_number') or business.get('reg_number', '—')],
            ["Clearance Date Issued:", clearance_date_str],
        ]
        
        # Add unit information if applicable
        total_units = business.get('total_units')
        if total_units and total_units > 0:
            registration_info.append(["Total Units:", str(total_units)])
        
        # Add amusement device counts if applicable
        videoke_count = business.get('videoke_count')
        billiard_count = business.get('billiard_count')
        other_device_count = business.get('other_device_count')
        
        if any([videoke_count, billiard_count, other_device_count]):
            if videoke_count:
                registration_info.append(["Videoke Count:", str(videoke_count)])
            if billiard_count:
                registration_info.append(["Billiard Count:", str(billiard_count)])
            if other_device_count:
                registration_info.append(["Other Device Count:", str(other_device_count)])
        
        registration_table_data = []
        for label, value in registration_info:
            registration_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        registration_table = Table(registration_table_data, colWidths=[1.8*inch, 5.2*inch])
        registration_table.setStyle(_get_data_table_style())
        elements.append(registration_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 4: Location Information
        header_table = Table([[Paragraph("LOCATION INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        location_info = [
            ["Complete Address:", business.get('address', '—')],
        ]
        
        location_table_data = []
        for label, value in location_info:
            location_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        location_table = Table(location_table_data, colWidths=[1.8*inch, 5.2*inch])
        location_table.setStyle(_get_data_table_style())
        elements.append(location_table)
        
        # Footer info
        elements.append(Spacer(1, 0.05*inch))
        footer_info_style = ParagraphStyle(
            'FooterInfo',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_LEFT,
            fontName='Times-Roman'
        )
        
        generated_date = datetime.now().strftime('%B %d, %Y %I:%M %p')
        elements.append(Paragraph(f"<b>Generated:</b> {generated_date}", footer_info_style))
        
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
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=BusinessDetailCanvas)
        buffer.seek(0)
        return buffer
