"""
BHW Dashboard PDF Report Generator
Generates comprehensive health dashboard statistics report
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
from bhw_module.models import Dashboard


class BHWDashboardCanvas(canvas.Canvas):
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


class BHWDashboardReportPDF:
    """Generates BHW dashboard statistics PDF report."""
    
    def __init__(self, personnel_id=0, quarter_id=None):
        """Initialize the BHW dashboard report generator."""
        self.personnel_id = personnel_id
        self.quarter_id = quarter_id
    
    def _get_dashboard_data(self):
        """Fetch dashboard statistics from database."""
        # Use the same method as the dashboard view
        try:
            data = Dashboard.bhw_dashboard(personnel_id=self.personnel_id, quarter_id=self.quarter_id)
        except Exception:
            # Return default empty data if query fails
            data = {
                "total_households": 0,
                "total_families": 0,
                "total_active_maternal": 0,
                "total_active_maternal_by_bhw": 0,
                "total_children_upcoming_immun_5d": 0,
                "households_visited_today_by_bhw": 0,
                "hh_visited_count": 0,
                "hh_not_visited_count": 0,
                "hh_visited_percent": 0,
                "fam_visited_count": 0,
                "fam_not_visited_count": 0,
                "fam_visited_percent": 0,
                "households_per_purok": [],
                "age_group_0_5": 0,
                "age_group_6_12": 0,
                "age_group_13_17": 0,
                "age_group_18_59": 0,
                "age_group_60_plus": 0,
            }
        
        return data or {}
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch dashboard data
        data = self._get_dashboard_data()
        
        # Create document in portrait orientation
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title='BHW Dashboard Report',
            author='LAMBO System',
            subject='Barangay Health Worker Dashboard Statistics'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Get dashboard data
        data = self._get_dashboard_data()
        
        # Custom styles using Times-Roman (matching other reports)
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
        elements.append(Paragraph("COMMUNITY HEALTH DASHBOARD REPORT", title_style))
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
        if self.quarter_id:
            elements.append(Paragraph(f"Quarter ID: {self.quarter_id}", date_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 1: Key Performance Indicators
        header_table = Table([[Paragraph("KEY PERFORMANCE INDICATORS", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        # KPI data in simple table format
        kpi_data = [
            ['Households', str(data.get('total_households', 0)), 'Total registered'],
            ['Families', str(data.get('total_families', 0)), 'Within barangay'],
            ['Active Maternal (Barangay)', str(data.get('total_active_maternal', 0)), 'Across all BHWs'],
            ['Active Maternal (Your Records)', str(data.get('total_active_maternal_by_bhw', 0)), 'Assigned to you'],
            ['Upcoming Child Immunization', str(data.get('total_children_upcoming_immun_5d', 0)), 'Next 5 days'],
            ['Households Visited Today', str(data.get('households_visited_today_by_bhw', 0)), 'By you today'],
        ]
        
        # Convert to table format with Paragraphs
        kpi_table_data = []
        for label, value, description in kpi_data:
            kpi_table_data.append([
                Paragraph(f"<b>{label}</b>", label_style),
                Paragraph(f"<font size=14 color='#991B1B'><b>{value}</b></font>", value_style),
                Paragraph(f"<i>{description}</i>", value_style),
            ])
        
        kpi_table = Table(kpi_table_data, colWidths=[2.5*inch, 1.5*inch, 3.0*inch])
        kpi_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 2: Visitation Progress
        header_table = Table([[Paragraph("VISITATION PROGRESS", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        # Household visitation progress
        hh_visited = data.get('hh_visited_count', 0)
        hh_total = data.get('total_households', 0)
        hh_percent = data.get('hh_visited_percent', 0)
        
        # Family visitation progress
        fam_visited = data.get('fam_visited_count', 0)
        fam_total = data.get('total_families', 0)
        fam_percent = data.get('fam_visited_percent', 0)
        
        visit_data = [
            ['Metric', 'Progress', 'Percentage'],
            [
                Paragraph("<b>Household Visitation</b>", label_style),
                Paragraph(f"<b>{hh_visited}</b> / {hh_total}", value_style),
                Paragraph(f"<b>{round(hh_percent, 1)}%</b> completed", value_style),
            ],
            [
                Paragraph("<b>Family Visitation</b>", label_style),
                Paragraph(f"<b>{fam_visited}</b> / {fam_total}", value_style),
                Paragraph(f"<b>{round(fam_percent, 1)}%</b> completed", value_style),
            ]
        ]
        
        visit_table = Table(visit_data, colWidths=[2.5*inch, 2.0*inch, 2.5*inch])
        visit_table.setStyle(TableStyle([
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
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        elements.append(visit_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 3: Households per Purok/Sitio
        header_table = Table([[Paragraph("HOUSEHOLDS PER PUROK/SITIO", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        
        purok_table_data = [
            [
                Paragraph("<b>Purok/Sitio</b>", label_style),
                Paragraph("<b>Household Count</b>", label_style),
            ]
        ]
        
        # Get purok data from households_per_purok field
        per_purok = data.get('households_per_purok', [])
        for purok_item in per_purok:
            purok_name = purok_item.get('sitio_name', 'Unknown')
            purok_count = purok_item.get('total_households', 0)
            purok_table_data.append([
                Paragraph(str(purok_name), value_style),
                Paragraph(f"<b>{purok_count}</b>", value_style),
            ])
        
        if not per_purok:
            purok_table_data.append([
                Paragraph("<i>No data available</i>", value_style),
                Paragraph("—", value_style),
            ])
        
        purok_table = Table(purok_table_data, colWidths=[4.5*inch, 2.5*inch], hAlign='LEFT', repeatRows=1)
        purok_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        elements.append(purok_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 4: Age Distribution
        header_table = Table([[Paragraph("AGE DISTRIBUTION", section_header_style)]], colWidths=[7.0*inch])
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
        
        # Calculate total for percentages
        age_0_5 = data.get('age_group_0_5', 0)
        age_6_12 = data.get('age_group_6_12', 0)
        age_13_17 = data.get('age_group_13_17', 0)
        age_18_59 = data.get('age_group_18_59', 0)
        age_60_plus = data.get('age_group_60_plus', 0)
        total_age_count = age_0_5 + age_6_12 + age_13_17 + age_18_59 + age_60_plus
        
        # Build age distribution rows
        age_groups = [
            ('0-5 years', age_0_5),
            ('6-12 years', age_6_12),
            ('13-17 years', age_13_17),
            ('18-59 years', age_18_59),
            ('60+ years', age_60_plus),
        ]
        
        for age_label, count in age_groups:
            percentage = round((count / total_age_count * 100) if total_age_count > 0 else 0, 1)
            age_table_data.append([
                Paragraph(age_label, value_style),
                Paragraph(f"<b>{count}</b>", value_style),
                Paragraph(f"{percentage}%", value_style),
            ])
        
        if total_age_count == 0:
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
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        elements.append(age_table)
        
        # Footer
        elements.append(Spacer(1, 0.1*inch))
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
            "For verification purposes, please contact the Barangay Health Office.",
            footer_style
        ))
        
        # Build PDF with custom canvas
        doc.build(elements, canvasmaker=BHWDashboardCanvas)
        buffer.seek(0)
        return buffer
