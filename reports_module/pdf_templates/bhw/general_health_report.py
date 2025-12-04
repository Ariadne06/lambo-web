"""
BHW General Health Report PDF Generator
Generates filtered general health reports
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
from bhw_module.models import GeneralHealth


class GeneralHealthReportCanvas(canvas.Canvas):
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


class GeneralHealthReportPDF:
    """Generates BHW general health report PDF."""
    
    def __init__(self, report_type='all', start_date=None, end_date=None):
        """Initialize the general health report generator."""
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        
        # Report type labels
        self.type_labels = {
            'all': 'All Health Records',
            'hypertension': 'Hypertension Cases',
            'diabetes': 'Diabetes Cases',
            'tb': 'Tuberculosis Cases'
        }
    
    def _get_health_data(self):
        """Fetch health data from database."""
        if self.report_type == 'hypertension':
            return GeneralHealth.sp_get_hypertension_cases(
                start_date=self.start_date,
                end_date=self.end_date
            )
        elif self.report_type == 'diabetes':
            return GeneralHealth.sp_get_diabetes_cases(
                start_date=self.start_date,
                end_date=self.end_date
            )
        elif self.report_type == 'tb':
            return GeneralHealth.sp_get_tb_cases(
                start_date=self.start_date,
                end_date=self.end_date
            )
        else:
            return GeneralHealth.sp_get_all_health_records(
                start_date=self.start_date,
                end_date=self.end_date
            )
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        records = self._get_health_data()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title='General Health Report',
            author='LAMBO System',
            subject='Barangay Health Worker General Health Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=19,
            textColor=colors.HexColor('#991B1B'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        filter_style = ParagraphStyle(
            'FilterStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName='Times-Roman'
        )
        
        # Title
        title_text = self.type_labels.get(self.report_type, 'General Health Report')
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Applied Filters Section
        if self.start_date or self.end_date:
            elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
            elements.append(Spacer(1, 0.05*inch))
            
            filter_data = []
            
            if self.start_date:
                date_str = self.start_date.strftime('%B %d, %Y') if hasattr(self.start_date, 'strftime') else str(self.start_date)
                filter_data.append(['Start Date:', date_str])
            
            if self.end_date:
                date_str = self.end_date.strftime('%B %d, %Y') if hasattr(self.end_date, 'strftime') else str(self.end_date)
                filter_data.append(['End Date:', date_str])
            
            # Convert filter values to Paragraphs for wrapping
            formatted_filter_data = []
            for label, value in filter_data:
                value_paragraph = Paragraph(value, ParagraphStyle(
                    'FilterValue',
                    parent=styles['Normal'],
                    fontSize=9,
                    fontName='Times-Roman',
                    leading=10
                ))
                formatted_filter_data.append([label, value_paragraph])
            
            filter_table = Table(formatted_filter_data, colWidths=[1.5*inch, 5.5*inch], hAlign='LEFT')
            filter_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ]))
            elements.append(filter_table)
            elements.append(Spacer(1, 0.15*inch))
        
        # Metadata
        current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_LEFT,
            fontName='Times-Roman'
        )
        
        elements.append(Paragraph(f"<b>Generated:</b> {current_date}", metadata_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Data Table
        if records:
            if self.report_type == 'all':
                # All health records table
                table_data = [['Full Name', 'Sex', 'Age', 'Household No.', 'Sitio', 'Medical Conditions', 'Class']]
                
                for rec in records:
                    # Use Paragraph for full name to handle wrapping
                    full_name = rec.get('full_name') or '—'
                    name_paragraph = Paragraph(full_name, ParagraphStyle(
                        'NameStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    # Use Paragraph for sitio to handle wrapping
                    sitio_name = rec.get('sitio_name') or '—'
                    sitio_paragraph = Paragraph(sitio_name, ParagraphStyle(
                        'SitioStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    # Use Paragraph for medical conditions to handle wrapping
                    medical_conditions = rec.get('medical_conditions') or 'None'
                    conditions_paragraph = Paragraph(medical_conditions, ParagraphStyle(
                        'ConditionsStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    # Use Paragraph for class to handle wrapping
                    class_name = rec.get('class_name') or '—'
                    class_paragraph = Paragraph(class_name, ParagraphStyle(
                        'ClassStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    table_data.append([
                        name_paragraph,
                        rec.get('sex') or '—',
                        rec.get('age_display') or '—',
                        rec.get('household_number') or '—',
                        sitio_paragraph,
                        conditions_paragraph,
                        class_paragraph
                    ])
                
                col_widths = [1.3*inch, 0.5*inch, 0.6*inch, 0.9*inch, 0.9*inch, 1.5*inch, 1.3*inch]
                
            else:
                # Specific condition tables (hypertension/diabetes/tb)
                table_data = [['Full Name', 'Sex', 'Age', 'Household No.', 'Sitio', 'Class', 'Smoker', 'Alcohol']]
                
                for rec in records:
                    # Use Paragraph for full name to handle wrapping
                    full_name = rec.get('full_name') or '—'
                    name_paragraph = Paragraph(full_name, ParagraphStyle(
                        'NameStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    # Use Paragraph for sitio to handle wrapping
                    sitio_name = rec.get('sitio_name') or '—'
                    sitio_paragraph = Paragraph(sitio_name, ParagraphStyle(
                        'SitioStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    # Use Paragraph for class to handle wrapping
                    class_name = rec.get('class_name') or '—'
                    class_paragraph = Paragraph(class_name, ParagraphStyle(
                        'ClassStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Times-Roman',
                        leading=8
                    ))
                    
                    table_data.append([
                        name_paragraph,
                        rec.get('sex') or '—',
                        rec.get('age_display') or '—',
                        rec.get('household_number') or '—',
                        sitio_paragraph,
                        class_paragraph,
                        rec.get('smoker') or '—',
                        rec.get('alcohol_drinker') or '—'
                    ])
                
                col_widths = [1.4*inch, 0.5*inch, 0.6*inch, 0.9*inch, 0.9*inch, 1.0*inch, 0.6*inch, 0.6*inch]
            
            health_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            health_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Full Name
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'), # All other columns
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
                
                # Line at split for page breaks
                ('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 1, colors.HexColor('#991B1B')),
            ]))
            elements.append(health_table)
            
            # Add metadata after table
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f"<b>Total Records:</b> {len(records)}", metadata_style))
        else:
            # No records found
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph("No health records found matching the specified criteria.", no_data_style))
        
        # Page footer function (matching child_report.py and household_report.py)
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas (matching child_report.py and household_report.py)
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=GeneralHealthReportCanvas)
        buffer.seek(0)
        return buffer
