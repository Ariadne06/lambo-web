"""
Child Health List Filtered PDF Report Generator
Generates filtered list of child health records with applied filters display
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
from household_module.models import Household


class ChildHealthListCanvas(canvas.Canvas):
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


class ChildHealthListFilteredPDF:
    """Generates a filtered child health list PDF report."""
    
    def __init__(self, query=None, sitio_id=None, sex=None):
        """Initialize with filter parameters."""
        # Convert empty strings to None
        self.query = query if query and query.strip() else None
        self.sitio_id = int(sitio_id) if sitio_id and str(sitio_id).strip().isdigit() else None
        self.sex = sex if sex and sex.strip() else None
        
    def _get_child_records(self):
        """Fetch child health records from database."""
        return Child.sp_view_all_child_health_record(
            query=self.query,
            sitio_id=self.sitio_id,
            sex=self.sex,
            limit=10000,
            offset=0
        )
    
    def _get_sitios(self):
        """Fetch all sitios."""
        return Household.sp_get_sitio()
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        child_records = self._get_child_records()
        sitios = self._get_sitios()
        
        # Create document - Use portrait orientation like resident list and household list
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,  # Match household_list spacing for header
            bottomMargin=0.75*inch,
            title='Child Health List',
            author='LAMBO System',
            subject='Child Health Records Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles using Times-Roman (matching resident list and household list)
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
        elements.append(Paragraph("CHILD HEALTH LIST", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Applied Filters Section
        if any([self.query, self.sitio_id, self.sex]):
            elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
            elements.append(Spacer(1, 0.05*inch))
            
            filter_data = []
            
            # Search query filter
            if self.query:
                filter_data.append(['Search Query:', self.query])
            
            # Sitio filter
            if self.sitio_id:
                sitio_name = next((s['sitio_name'] for s in sitios if s['sitio_id'] == self.sitio_id), 'Unknown')
                filter_data.append(['Sitio:', sitio_name])
            
            # Sex filter
            if self.sex:
                filter_data.append(['Sex:', self.sex.capitalize()])
            
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
            
            # Match the width of the main data table (total: 7.0 inches)
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
            elements.append(Paragraph("<b>Filters:</b> None (All Child Records)", filter_style))
            elements.append(Spacer(1, 0.15*inch))
        
        # Check if we have child records (filter out sentinel row with household_id=0)
        # Note: household_id can be None for valid records, only filter out explicit 0
        valid_records = [c for c in child_records if c.get('household_id') != 0]
        
        # Child Health List Table
        if valid_records:
            # Table headers
            table_data = [[
                'Child Health ID',
                'Full Name',
                'Sex',
                'DOB',
                'Age',
                "Mother's Name",
                'Household No.'
            ]]
            
            # Table rows
            for child in valid_records:
                # Format DOB
                dob = str(child.get('dob', ''))[:10] if child.get('dob') else '—'
                
                table_data.append([
                    str(child.get('child_health_id', '—')),
                    child.get('child_full_name') or '—',
                    child.get('sex') or '—',
                    dob,
                    str(child.get('age', '—')),
                    child.get('mother_full_name') or '—',
                    child.get('household_number') or '—',
                ])
            
            # Create table with proper column widths for portrait
            col_widths = [1.0*inch, 1.5*inch, 0.5*inch, 0.9*inch, 0.5*inch, 1.5*inch, 1.1*inch]
            
            child_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
            
            # Table styling (matching resident list and household list)
            child_table.setStyle(TableStyle([
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
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Child Health ID
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Full Name
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Sex
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # DOB
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Age
                ('ALIGN', (5, 1), (5, -1), 'LEFT'),    # Mother's Name
                ('ALIGN', (6, 1), (6, -1), 'LEFT'),    # Household No.
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
            
            elements.append(child_table)
        else:
            # No child records found
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph("No child health records found matching the specified filters.", no_data_style))
        
        # Add metadata at the bottom (matching resident_list and household_list)
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
        
        # Page footer function (matching household_list and resident_list)
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas (matching resident_list and household_list)
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=ChildHealthListCanvas)
        
        buffer.seek(0)
        return buffer
