"""
Demographic Dashboard PDF Report Generator
Generates comprehensive demographic statistics report
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
from secretary_module.models import Dashboard


class DemographicDashboardCanvas(canvas.Canvas):
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


class DemographicDashboardPDF:
    """Generates demographic dashboard PDF report."""
    
    def __init__(self):
        """Initialize the demographic report generator."""
        pass
    
    def _get_demographic_data(self):
        """Fetch demographic statistics from database using Dashboard model functions."""
        # Get total counts using Dashboard.sp_dashboard_totals()
        totals = Dashboard.sp_dashboard_totals()
        
        # Get residents per sitio using Dashboard.sp_residents_per_sitio_json()
        per_sitio_rows = Dashboard.sp_residents_per_sitio_json()
        # Convert to tuple format for consistency with original code
        per_sitio = [(row.get('sitio_name', 'Unknown'), row.get('resident_count', 0)) for row in per_sitio_rows]
        
        # Get age distribution using Dashboard.sp_age_bracket_distribution()
        age_rows = Dashboard.sp_age_bracket_distribution()
        # Clean age distribution data (handle jsonb_build_object wrapper)
        cleaned_age = []
        for item in age_rows or []:
            if isinstance(item, dict) and "jsonb_build_object" in item:
                cleaned_age.append(item["jsonb_build_object"])
            else:
                cleaned_age.append(item)
        # Convert to tuple format (age_group, count)
        age_distribution = [(row.get('bracket', 'Unknown'), row.get('count', 0)) for row in cleaned_age]
        
        return {
            'totals': totals,
            'age_distribution': age_distribution,
            'per_sitio': per_sitio
        }
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch demographic data
        data = self._get_demographic_data()
        totals = data['totals']
        
        # Create document in portrait orientation (matching resident_list and household_list)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,  # Match household_list spacing for header
            bottomMargin=0.75*inch,
            title='Demographic Dashboard Report',
            author='LAMBO System',
            subject='Demographic Statistics Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles (matching resident_list and household_list fonts - Times-Roman)
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=19,
            textColor=colors.HexColor('#991B1B'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=10,
            textColor=colors.white,
            spaceBefore=12,
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName='Times-Bold',
            backColor=colors.HexColor('#991B1B'),
            leftIndent=8,
            rightIndent=8
        )
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Bold'
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Roman',
            leading=8
        )
        
        # Title
        elements.append(Paragraph("DEMOGRAPHIC DASHBOARD REPORT", title_style))
        generated_date = datetime.now().strftime('%B %d, %Y %I:%M %p')
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER,
            fontName='Times-Italic'
        )
        elements.append(Paragraph(f"Generated: {generated_date}", date_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 1: Population Overview
        header_table = Table([[Paragraph("POPULATION OVERVIEW", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        total_population = totals['total_resident'] + totals['total_non_resident']
        
        # Population summary cards in a table (adjusted for portrait width)
        population_data = [
            [
                Paragraph("<b>TOTAL</b>", label_style),
                Paragraph("<b>RESIDENTS</b>", label_style),
                Paragraph("<b>NON-RESIDENTS</b>", label_style),
                Paragraph("<b>PENDING</b>", label_style),
            ],
            [
                Paragraph(f"<font size=12 color='#111827'><b>{total_population}</b></font>", value_style),
                Paragraph(f"<font size=12 color='#059669'><b>{totals['total_resident']}</b></font>", value_style),
                Paragraph(f"<font size=12 color='#64748b'><b>{totals['total_non_resident']}</b></font>", value_style),
                Paragraph(f"<font size=12 color='#d97706'><b>{totals['total_pending']}</b></font>", value_style),
            ],
            [
                Paragraph("<font size=7 color='#6B7280'>Total registered</font>", value_style),
                Paragraph("<font size=7 color='#6B7280'>Within barangay</font>", value_style),
                Paragraph("<font size=7 color='#6B7280'>Outside barangay</font>", value_style),
                Paragraph("<font size=7 color='#6B7280'>For review</font>", value_style),
            ]
        ]
        
        population_table = Table(population_data, colWidths=[1.75*inch, 1.75*inch, 1.75*inch, 1.75*inch])
        population_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#ECFDF5')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F8FAFC')),
            ('BACKGROUND', (3, 0), (3, -1), colors.HexColor('#FEF3C7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(population_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 2: Gender Breakdown
        header_table = Table([[Paragraph("GENDER BREAKDOWN", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        total_gender = totals['total_male'] + totals['total_female']
        male_pct = round((totals['total_male'] / total_gender * 100) if total_gender > 0 else 0, 1)
        female_pct = round((totals['total_female'] / total_gender * 100) if total_gender > 0 else 0, 1)
        
        gender_data = [
            [
                Paragraph("<b>MALE</b>", label_style),
                Paragraph("<b>FEMALE</b>", label_style),
            ],
            [
                Paragraph(f"<font size=12 color='#2563eb'><b>{totals['total_male']}</b></font>", value_style),
                Paragraph(f"<font size=12 color='#ec4899'><b>{totals['total_female']}</b></font>", value_style),
            ],
            [
                Paragraph(f"<font size=8 color='#6B7280'>{male_pct}% of residents</font>", value_style),
                Paragraph(f"<font size=8 color='#6B7280'>{female_pct}% of residents</font>", value_style),
            ]
        ]
        
        gender_table = Table(gender_data, colWidths=[3.5*inch, 3.5*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EFF6FF')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#FCE7F3')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(gender_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 3: Age Distribution
        header_table = Table([[Paragraph("RESIDENT AGE DISTRIBUTION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        age_table_data = [
            [
                Paragraph("<b>Age Group</b>", label_style),
                Paragraph("<b>Count</b>", label_style),
                Paragraph("<b>Percentage</b>", label_style),
            ]
        ]
        
        total_age_count = sum(row[1] for row in data['age_distribution'])
        for age_group, count in data['age_distribution']:
            pct = round((count / total_age_count * 100) if total_age_count > 0 else 0, 1)
            age_table_data.append([
                Paragraph(str(age_group), value_style),
                Paragraph(f"<b>{count}</b>", value_style),
                Paragraph(f"{pct}%", value_style),
            ])
        
        if not data['age_distribution']:
            age_table_data.append([
                Paragraph("<i>No data available</i>", value_style),
                Paragraph("—", value_style),
                Paragraph("—", value_style),
            ])
        
        age_table = Table(age_table_data, colWidths=[2.3*inch, 2.3*inch, 2.4*inch], hAlign='LEFT', repeatRows=1)
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        elements.append(age_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 4: Residents per Sitio
        header_table = Table([[Paragraph("RESIDENTS PER PUROK/SITIO", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        sitio_table_data = [
            [
                Paragraph("<b>Purok/Sitio</b>", label_style),
                Paragraph("<b>Resident Count</b>", label_style),
                Paragraph("<b>Percentage</b>", label_style),
            ]
        ]
        
        total_sitio_count = sum(row[1] for row in data['per_sitio'])
        for sitio_name, count in data['per_sitio']:
            pct = round((count / total_sitio_count * 100) if total_sitio_count > 0 else 0, 1)
            sitio_table_data.append([
                Paragraph(str(sitio_name), value_style),
                Paragraph(f"<b>{count}</b>", value_style),
                Paragraph(f"{pct}%", value_style),
            ])
        
        if not data['per_sitio']:
            sitio_table_data.append([
                Paragraph("<i>No data available</i>", value_style),
                Paragraph("—", value_style),
                Paragraph("—", value_style),
            ])
        
        sitio_table = Table(sitio_table_data, colWidths=[2.3*inch, 2.3*inch, 2.4*inch], hAlign='LEFT', repeatRows=1)
        sitio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 1, colors.HexColor('#991B1B')),
        ]))
        elements.append(sitio_table)
        
        # Metadata at the bottom (matching resident_list and household_list)
        elements.append(Spacer(1, 0.1*inch))
        
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_LEFT,
            fontName='Times-Roman'
        )
        
        elements.append(Paragraph(f"<b>Total Population:</b> {total_population}", metadata_style))
        elements.append(Paragraph(f"<b>Total Residents:</b> {totals['total_resident']}", metadata_style))
        
        # Page footer function (matching household_list and resident_list)
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
                  canvasmaker=DemographicDashboardCanvas)
        buffer.seek(0)
        return buffer
