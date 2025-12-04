"""
Maternal Health List Filtered PDF Report Generator
Generates filtered list of maternal health records with applied filters display
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
from bhw_module.models import Maternal


class MaternalHealthListCanvas(canvas.Canvas):
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


class MaternalHealthListFilteredPDF:
    """Generates a filtered maternal health list PDF report."""
    
    def __init__(self, query=None, record_status_id=None):
        """Initialize with filter parameters."""
        # Convert empty strings to None
        self.query = query if query and query.strip() else None
        self.record_status_id = int(record_status_id) if record_status_id and str(record_status_id).strip().isdigit() else None
        
    def _get_maternal_records(self):
        """Fetch maternal health records from database."""
        return Maternal.sp_view_all_maternal_record(
            name_query=self.query,
            record_status_id=self.record_status_id,
            limit=10000,
            offset=0
        )
    
    def _get_record_statuses(self):
        """Fetch all record statuses."""
        return Maternal.sp_get_record_status()
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        maternal_records = self._get_maternal_records()
        record_statuses = self._get_record_statuses()
        
        # Create document - Use portrait orientation
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title='Maternal Health List',
            author='LAMBO System',
            subject='Maternal Health Records Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles using Times-Roman
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
        
        # Header
        elements.append(Paragraph("MATERNAL HEALTH LIST", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Applied Filters Section
        if any([self.query, self.record_status_id]):
            elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
            elements.append(Spacer(1, 0.05*inch))
            
            filter_data = []
            
            # Search query filter
            if self.query:
                filter_data.append(['Search Query:', self.query])
            
            # Record Status filter
            if self.record_status_id:
                status_name = next((s['record_name'] for s in record_statuses if s['record_status_id'] == self.record_status_id), 'Unknown')
                filter_data.append(['Record Status:', status_name])
            
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
            
            # Match the width of the main data table
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
        else:
            elements.append(Paragraph("<b>Filters:</b> None (All Maternal Records)", filter_style))
            elements.append(Spacer(1, 0.15*inch))
        
        # Check if we have maternal records
        valid_records = [m for m in maternal_records if m.get('maternal_health_id', 0) != 0]
        
        # Maternal Health List Table
        if valid_records:
            # Table headers
            table_data = [[
                'Maternal ID',
                'Full Name',
                'DOB',
                'Family Code',
                'Record Status',
                'Date Created'
            ]]
            
            # Table rows
            for maternal in valid_records:
                # Format DOB
                dob = str(maternal.get('dob', ''))[:10] if maternal.get('dob') else '—'
                
                # Format Date Created
                date_created = ''
                if maternal.get('date_created'):
                    try:
                        if hasattr(maternal['date_created'], 'strftime'):
                            date_created = maternal['date_created'].strftime('%b %d, %Y')
                        else:
                            date_created = str(maternal['date_created'])[:10]
                    except:
                        date_created = '—'
                else:
                    date_created = '—'
                
                table_data.append([
                    str(maternal.get('maternal_health_id', '—')),
                    maternal.get('maternal_full_name') or '—',
                    dob,
                    maternal.get('family_code') or '—',
                    maternal.get('record_status') or '—',
                    date_created,
                ])
            
            # Create table with proper column widths for portrait
            col_widths = [0.9*inch, 1.8*inch, 0.9*inch, 1.2*inch, 1.2*inch, 1.0*inch]
            
            maternal_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
            
            # Table styling
            maternal_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Maternal ID
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Full Name
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # DOB
                ('ALIGN', (3, 1), (3, -1), 'LEFT'),    # Family Code
                ('ALIGN', (4, 1), (4, -1), 'LEFT'),    # Record Status
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Date Created
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
                
                # Line at split for page breaks
                ('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 1, colors.HexColor('#991B1B')),
            ]))
            
            elements.append(maternal_table)
        else:
            # No maternal records found
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph("No maternal health records found matching the specified filters.", no_data_style))
        
        # Add metadata at the bottom
        elements.append(Spacer(1, 0.1*inch))
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(valid_records)}", metadata_style))
        
        # Page footer function
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
                  canvasmaker=MaternalHealthListCanvas)
        
        buffer.seek(0)
        return buffer
