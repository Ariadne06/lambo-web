"""
BHW Child Health Report PDF Generator
Generates filtered child health reports
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
from bhw_module.models import Child


class ChildReportCanvas(canvas.Canvas):
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


class ChildHealthReportPDF:
    """Generates BHW child health report PDF."""
    
    def __init__(self, report_type='all', start_date=None, end_date=None):
        """Initialize the child health report generator."""
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        
        # Report type labels
        self.type_labels = {
            'all': 'All Children Records',
            'immunization': 'Child Immunization Summary',
            'schedule': 'Vaccination Schedule'
        }
    
    def _get_child_data(self):
        """Fetch child health data from database."""
        if self.report_type == 'immunization':
            return Child.sp_get_child_immunization_summary(
                start_date=self.start_date,
                end_date=self.end_date
            )
        elif self.report_type == 'schedule':
            return Child.sp_get_child_vaccination_schedule(
                start_date=self.start_date,
                end_date=self.end_date
            )
        else:
            return Child.sp_get_all_children_records(
                start_date=self.start_date,
                end_date=self.end_date
            )
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        records = self._get_child_data()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title='Child Health Report',
            author='LAMBO System',
            subject='Barangay Health Worker Child Health Report'
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
        title_text = self.type_labels.get(self.report_type, 'Child Health Report')
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(records)}", metadata_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Data Table
        if records:
            if self.report_type == 'immunization':
                table_data = [['Child Name', 'Sex', 'Age', 'Total Vaccines', 'Last Vaccine', 'Mother Name', 'Household No.']]
                for rec in records:
                    child_name = rec.get('child_full_name') or '—'
                    name_paragraph = Paragraph(child_name, ParagraphStyle(
                        'NameStyle', parent=styles['Normal'], fontSize=7, fontName='Times-Roman', leading=8
                    ))
                    
                    mother_name = rec.get('mother_full_name') or '—'
                    mother_paragraph = Paragraph(mother_name, ParagraphStyle(
                        'MotherStyle', parent=styles['Normal'], fontSize=7, fontName='Times-Roman', leading=8
                    ))
                    
                    last_vaccine = '—'
                    if rec.get('last_vaccine_date'):
                        try:
                            if hasattr(rec['last_vaccine_date'], 'strftime'):
                                last_vaccine = rec['last_vaccine_date'].strftime('%Y-%m-%d')
                            else:
                                last_vaccine = str(rec['last_vaccine_date'])[:10]
                        except:
                            pass
                    
                    table_data.append([
                        name_paragraph,
                        rec.get('sex') or '—',
                        rec.get('age_display') or '—',
                        str(rec.get('total_vaccines_completed') or 0),
                        last_vaccine,
                        mother_paragraph,
                        rec.get('household_number') or '—'
                    ])
                col_widths = [1.4*inch, 0.45*inch, 0.7*inch, 0.8*inch, 0.95*inch, 1.4*inch, 1.3*inch]
                
            elif self.report_type == 'schedule':
                table_data = [['Child Name', 'Age', 'Vaccine Name', 'Next Dose', 'Scheduled Date', 'Household No.']]
                for rec in records:
                    child_name = rec.get('child_full_name') or '—'
                    name_paragraph = Paragraph(child_name, ParagraphStyle(
                        'NameStyle', parent=styles['Normal'], fontSize=7, fontName='Times-Roman', leading=8
                    ))
                    
                    vaccine_name = rec.get('vaccine_name') or '—'
                    vaccine_paragraph = Paragraph(vaccine_name, ParagraphStyle(
                        'VaccineStyle', parent=styles['Normal'], fontSize=7, fontName='Times-Roman', leading=8
                    ))
                    
                    scheduled_date = '—'
                    if rec.get('scheduled_date'):
                        try:
                            if hasattr(rec['scheduled_date'], 'strftime'):
                                scheduled_date = rec['scheduled_date'].strftime('%Y-%m-%d')
                            else:
                                scheduled_date = str(rec['scheduled_date'])[:10]
                        except:
                            pass
                    
                    table_data.append([
                        name_paragraph,
                        rec.get('age_display') or '—',
                        vaccine_paragraph,
                        str(rec.get('next_dose') or '—'),
                        scheduled_date,
                        rec.get('household_number') or '—'
                    ])
                col_widths = [1.6*inch, 0.7*inch, 1.8*inch, 1.0*inch, 1.0*inch, 1.0*inch]
                
            else:  # all
                table_data = [['Child Name', 'Sex', 'DOB', 'Age', 'Mother Name', 'Household No.', 'Sitio']]
                for rec in records:
                    child_name = rec.get('child_full_name') or '—'
                    name_paragraph = Paragraph(child_name, ParagraphStyle(
                        'NameStyle', parent=styles['Normal'], fontSize=7, fontName='Times-Roman', leading=8
                    ))
                    
                    mother_name = rec.get('mother_full_name') or '—'
                    mother_paragraph = Paragraph(mother_name, ParagraphStyle(
                        'MotherStyle', parent=styles['Normal'], fontSize=7, fontName='Times-Roman', leading=8
                    ))
                    
                    dob_str = '—'
                    if rec.get('dob'):
                        try:
                            if hasattr(rec['dob'], 'strftime'):
                                dob_str = rec['dob'].strftime('%Y-%m-%d')
                            else:
                                dob_str = str(rec['dob'])[:10]
                        except:
                            pass
                    
                    table_data.append([
                        name_paragraph,
                        rec.get('sex') or '—',
                        dob_str,
                        rec.get('age_display') or '—',
                        mother_paragraph,
                        rec.get('household_number') or '—',
                        rec.get('sitio_name') or '—'
                    ])
                col_widths = [1.3*inch, 0.45*inch, 0.85*inch, 0.7*inch, 1.4*inch, 1.1*inch, 1.2*inch]
            
            child_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            child_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
                ('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 1, colors.HexColor('#991B1B')),
            ]))
            
            elements.append(child_table)
        else:
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph("No child health records found matching the specified criteria.", no_data_style))
        
        # Page footer function
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
                  canvasmaker=ChildReportCanvas)
        buffer.seek(0)
        return buffer
