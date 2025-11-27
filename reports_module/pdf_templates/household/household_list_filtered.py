"""
Household List Filtered PDF Report Generator
Generates filtered list of households with applied filters display
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
from ..base import draw_barangay_header, get_standard_styles, draw_watermark
from ...utils.database_helpers import get_all_households, get_all_quarters, get_sitios


class HouseholdListCanvas(canvas.Canvas):
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


class HouseholdListFilteredPDF:
    """Generates a filtered household list PDF report."""
    
    def __init__(self, query=None, status=None, sitio_id=None, quarter_id=None):
        """Initialize with filter parameters."""
        self.query = query
        self.status = status or 'all'
        self.sitio_id = int(sitio_id) if sitio_id and str(sitio_id).isdigit() else None
        self.quarter_id = int(quarter_id) if quarter_id and str(quarter_id).isdigit() else None
        
    def _get_households(self):
        """Fetch households from database using database helper."""
        return get_all_households(
            query=self.query,
            barangay=None,
            sitio_id=self.sitio_id,
            status=self.status,
            quarter_id=self.quarter_id,
            limit=10000,
            offset=0
        )
    
    def _get_quarters(self):
        """Fetch all quarters using database helper."""
        return get_all_quarters()
    
    def _get_sitios(self):
        """Fetch all sitios using database helper."""
        return get_sitios()
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        households = self._get_households()
        quarters = self._get_quarters()
        sitios = self._get_sitios()
        
        # Build title based on quarter
        quarter_info = None
        if self.quarter_id:
            quarter_info = next((q for q in quarters if q['quarter_id'] == self.quarter_id), None)
        
        if quarter_info:
            doc_title = f"Household List - Q{quarter_info['quarter_number']} {quarter_info['year']}"
        else:
            doc_title = "Household List - Current Quarter"
        
        # Create document - Use portrait orientation like resident list
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,  # Match resident list spacing for header
            bottomMargin=0.75*inch,
            title=doc_title,
            author='LAMBO System',
            subject='Household List Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles using Times-Roman (matching resident list)
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=19,
            textColor=colors.HexColor('#991B1B'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Times-Roman'
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
        elements.append(Paragraph("HOUSEHOLD LIST", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Applied Filters Section
        if any([self.query, self.status != 'all', self.sitio_id, quarter_info]):
            elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
            elements.append(Spacer(1, 0.05*inch))
            
            filter_data = []
            
            # Quarter filter (always show)
            if quarter_info:
                filter_data.append(['Quarter:', f"Q{quarter_info['quarter_number']} {quarter_info['year']}"])
            else:
                filter_data.append(['Quarter:', "Current Quarter (Live Data)"])
            
            # Search query filter
            if self.query:
                filter_data.append(['Search Query:', self.query])
            
            # Status filter
            if self.status and self.status != 'all':
                filter_data.append(['Status:', self.status.capitalize()])
            
            # Sitio filter
            if self.sitio_id:
                sitio_name = next((s['sitio_name'] for s in sitios if s['sitio_id'] == self.sitio_id), 'Unknown')
                filter_data.append(['Sitio:', sitio_name])
            
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
            elements.append(Paragraph("<b>Filters:</b> None (All Households)", filter_style))
            elements.append(Spacer(1, 0.15*inch))
        
        # Check if we have households (filter out sentinel row)
        valid_households = [h for h in households if h.get('household_id', 0) != 0]
        
        # Household List Table
        if valid_households:
            # Table headers
            table_data = [[
                'Household No.',
                'Household Head',
                'Address',
                'Status',
                'Visited'
            ]]
            
            # Table rows
            for household in valid_households:
                # Use Paragraph for address to handle wrapping
                address = household.get('full_address') or '—'
                address_paragraph = Paragraph(address, ParagraphStyle(
                    'AddressStyle',
                    parent=styles['Normal'],
                    fontSize=8,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                table_data.append([
                    household.get('household_number') or '—',
                    household.get('household_head') or '—',
                    address_paragraph,
                    'Active' if household.get('is_active') else 'Inactive',
                    'Yes' if household.get('is_visited') else 'No',
                ])
            
            # Create table with proper column widths for portrait
            col_widths = [1.3*inch, 1.8*inch, 2.5*inch, 0.7*inch, 0.7*inch]
            
            household_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
            
            # Table styling (matching resident list)
            household_table.setStyle(TableStyle([
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
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Household No
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Household Head
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Address
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Status
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Visited
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
            
            elements.append(household_table)
        else:
            # No households found
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph("No households found matching the specified filters.", no_data_style))
        
        # Add metadata at the bottom (matching resident list)
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(valid_households)}", metadata_style))
        
        # Footer with page numbers (matching resident list)
        def add_page_number(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas (matching resident list)
        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number,
                  canvasmaker=HouseholdListCanvas)
        
        buffer.seek(0)
        return buffer
