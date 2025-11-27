"""
Household Detail PDF Report Generator
Generates detailed household profile with family information
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
from ..base import draw_barangay_header, get_standard_styles, draw_watermark
from ...utils.database_helpers import get_specific_household, get_household_family_summaries, get_quarter_info


class HouseholdDetailCanvas(canvas.Canvas):
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


class HouseholdDetailPDF:
    """Generates a detailed household profile PDF report."""
    
    def __init__(self, household_id, quarter_id=None):
        """Initialize with household ID and optional quarter."""
        self.household_id = int(household_id)
        self.quarter_id = int(quarter_id) if quarter_id and str(quarter_id).isdigit() else None
    
    def _get_household(self):
        """Fetch household details using database helper."""
        return get_specific_household(self.household_id, self.quarter_id)
    
    def _get_families(self):
        """Fetch families for this household using database helper."""
        return get_household_family_summaries(self.household_id, self.quarter_id)
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        household = self._get_household()
        if not household or household.get('household_id') == 0:
            # Return empty PDF or error PDF
            return self._generate_error_pdf(buffer, "Household not found")
        
        families = self._get_families()
        
        # Build document title
        household_number = household.get('household_number', 'Unknown')
        doc_title = f"{household_number} - Household Profile"
        
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
            subject='Household Profile Report'
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
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Bold'
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Roman'
        )
        
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_LEFT,
            fontName='Times-Roman'
        )
        
        # Title
        elements.append(Paragraph("HOUSEHOLD PROFILE", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # SECTION 1: Household Information
        header_table = Table([[Paragraph("HOUSEHOLD INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        household_info = [
            ["Household Number:", household.get('household_number', '—')],
            ["Household Head:", household.get('household_head', '—')],
            ["Respondent:", household.get('respondent', '—')],
            ["Relationship to Head:", household.get('respondent_rth', '—')],
            ["Full Address:", household.get('full_address', '—')],
            ["House Ownership:", household.get('house_ownership', '—')],
            ["House Type:", household.get('house_type', '—')],
            ["Active Status:", 'Active' if household.get('is_active') else 'Inactive'],
        ]
        
        household_table_data = []
        for label, value in household_info:
            household_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        household_table = Table(household_table_data, colWidths=[1.5*inch, 5.5*inch])
        household_table.setStyle(_get_data_table_style())
        elements.append(household_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 2: Visitation Information
        header_table = Table([[Paragraph("VISITATION INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        visitation_info = [
            ["Visited:", 'Yes' if household.get('is_visited') else 'No'],
        ]
        
        if household.get('is_visited'):
            if household.get('date_visited'):
                visited_date = household['date_visited']
                if hasattr(visited_date, 'strftime'):
                    visitation_info.append(["Date Visited:", visited_date.strftime('%B %d, %Y')])
                else:
                    visitation_info.append(["Date Visited:", str(visited_date)])
            
            if household.get('visited_by'):
                visitation_info.append(["Visited By:", household.get('visited_by', '—')])
            
            # Add quarter information for visited households
            if self.quarter_id:
                quarter_info = get_quarter_info(self.quarter_id)
                if quarter_info:
                    quarter_text = f"Q{quarter_info['quarter_number']} {quarter_info['year']}"
                    visitation_info.append(["Quarter Visited:", quarter_text])
        
        visitation_table_data = []
        for label, value in visitation_info:
            visitation_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        visitation_table = Table(visitation_table_data, colWidths=[1.5*inch, 5.5*inch])
        visitation_table.setStyle(_get_data_table_style())
        elements.append(visitation_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 3: Families Residing
        header_table = Table([[Paragraph("FAMILIES RESIDING", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        if families:
            # Family table with grey header
            family_table_data = [
                [
                    Paragraph("<b>Family Code</b>", label_style),
                    Paragraph("<b>Family Head</b>", label_style),
                    Paragraph("<b>Total Members</b>", label_style),
                    Paragraph("<b>Visited</b>", label_style)
                ]
            ]
            
            for family in families:
                family_table_data.append([
                    Paragraph(str(family.get('family_code', '—')), value_style),
                    Paragraph(str(family.get('family_head', '—')), value_style),
                    Paragraph(str(family.get('total_members', 0)), value_style),
                    Paragraph('Yes' if family.get('is_visited') else 'No', value_style)
                ])
            
            # Create the family table with grey header
            family_table = Table(family_table_data, colWidths=[1.75*inch, 2.5*inch, 1.5*inch, 1.25*inch])
            family_table.setStyle(TableStyle([
                # Grey header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                # Alignment
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ]))
            elements.append(family_table)
            elements.append(Spacer(1, 0.15*inch))
            
            # Summary totals at the bottom (only if there are families)
            families_count = len(families)
            total_members = sum(f.get('total_members', 0) for f in families)
            
            summary_info = [
                ["Total Families:", str(families_count)],
                ["Total Members:", str(total_members)],
            ]
            
            summary_table_data = []
            for label, value in summary_info:
                summary_table_data.append([
                    Paragraph(label, label_style),
                    Paragraph(str(value), value_style)
                ])
            
            summary_table = Table(summary_table_data, colWidths=[1.5*inch, 5.5*inch])
            summary_table.setStyle(_get_data_table_style())
            elements.append(summary_table)
        else:
            # Centered message when no families
            no_families_style = ParagraphStyle(
                'NoFamilies',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#6B7280'),
                fontName='Times-Italic',
                alignment=TA_CENTER
            )
            elements.append(Paragraph("No families registered in this household.", no_families_style))
            elements.append(Spacer(1, 0.15*inch))
        
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
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=HouseholdDetailCanvas)
        buffer.seek(0)
        return buffer
    
    def _generate_error_pdf(self, buffer, message):
        """Generate a simple error PDF."""
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
        elements.append(Paragraph(f"<b>Error:</b> {message}", error_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer


def _get_data_table_style():
    """Returns consistent table style for data sections"""
    return TableStyle([
        # Labels background
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
    ])
