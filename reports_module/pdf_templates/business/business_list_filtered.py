"""
Business List Filtered PDF Report Generator
Generates filtered list of businesses with applied filters display
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
from django.db import connection


class BusinessListCanvas(canvas.Canvas):
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


class BusinessListFilteredPDF:
    """Generates a filtered business list PDF report."""
    
    def __init__(self, query=None, business_type_id=None, clearance_category_id=None, 
                 ownership_id=None, business_status_id=None):
        """Initialize with filter parameters."""
        self.query = query
        self.business_type_id = int(business_type_id) if business_type_id and str(business_type_id).isdigit() else None
        self.clearance_category_id = int(clearance_category_id) if clearance_category_id and str(clearance_category_id).isdigit() else None
        self.ownership_id = int(ownership_id) if ownership_id and str(ownership_id).isdigit() else None
        self.business_status_id = int(business_status_id) if business_status_id and str(business_status_id).isdigit() else None
        
    def _get_businesses(self):
        """Fetch businesses from database."""
        with connection.cursor() as cursor:
            cursor.callproc('get_all_businesses', [
                self.query,
                self.business_type_id,
                self.clearance_category_id,
                self.ownership_id,
                self.business_status_id,
                10000,  # limit
                0       # offset
            ])
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(cols, row)) for row in rows]
    
    def _get_business_types(self):
        """Fetch all business types."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT business_type_id, type_name FROM Business_Type ORDER BY type_name")
            return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    def _get_clearance_categories(self):
        """Fetch all clearance categories."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT clearance_category_id, category_name FROM Business_Clearance_Category ORDER BY category_name")
            return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    def _get_ownerships(self):
        """Fetch all ownerships."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT ownership_id, ownership_name FROM Ownership ORDER BY ownership_name")
            return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    def _get_business_statuses(self):
        """Fetch all business statuses."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT business_status_id, status_name FROM Business_Status ORDER BY status_name")
            return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        businesses = self._get_businesses()
        business_types = self._get_business_types()
        clearance_categories = self._get_clearance_categories()
        ownerships = self._get_ownerships()
        business_statuses = self._get_business_statuses()
        
        # Build title
        doc_title = "Business List"
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title=doc_title,
            author='LAMBO System',
            subject='Business List Report'
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
        elements.append(Paragraph("BUSINESS LIST", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Applied Filters Section
        if any([self.query, self.business_type_id, self.clearance_category_id, 
                self.ownership_id, self.business_status_id]):
            elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
            elements.append(Spacer(1, 0.05*inch))
            
            filter_data = []
            
            # Search query filter
            if self.query:
                filter_data.append(['Search Query:', self.query])
            
            # Business type filter
            if self.business_type_id:
                type_name = next((t['name'] for t in business_types if t['id'] == self.business_type_id), 'Unknown')
                filter_data.append(['Business Type:', type_name])
            
            # Clearance category filter
            if self.clearance_category_id:
                category_name = next((c['name'] for c in clearance_categories if c['id'] == self.clearance_category_id), 'Unknown')
                filter_data.append(['Clearance Category:', category_name])
            
            # Ownership filter
            if self.ownership_id:
                ownership_name = next((o['name'] for o in ownerships if o['id'] == self.ownership_id), 'Unknown')
                filter_data.append(['Ownership:', ownership_name])
            
            # Status filter
            if self.business_status_id:
                status_name = next((s['name'] for s in business_statuses if s['id'] == self.business_status_id), 'Unknown')
                filter_data.append(['Status:', status_name])
            
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
        else:
            elements.append(Paragraph("<b>Filters:</b> None (All Businesses)", filter_style))
            elements.append(Spacer(1, 0.15*inch))
        
        # Business List Table
        if businesses:
            # Table headers
            table_data = [[
                'Business Name',
                'Owner',
                'Type',
                'Category',
                'Address',
                'Ownership',
                'Status'
            ]]
            
            # Table rows
            for business in businesses:
                # Use Paragraph for business name to handle wrapping
                business_name = business.get('business_name') or '—'
                business_name_paragraph = Paragraph(business_name, ParagraphStyle(
                    'BusinessNameStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                owner_name = business.get('owner_name') or '—'
                owner_paragraph = Paragraph(owner_name, ParagraphStyle(
                    'OwnerStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                business_type = business.get('business_type_name') or '—'
                type_paragraph = Paragraph(business_type, ParagraphStyle(
                    'TypeStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                clearance_category = business.get('clearance_category_name') or '—'
                # Replace peso sign with 'Php' for better PDF compatibility
                if clearance_category != '—':
                    clearance_category = clearance_category.replace('₱', 'Php ')
                category_paragraph = Paragraph(clearance_category, ParagraphStyle(
                    'CategoryStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                address = business.get('address') or '—'
                address_paragraph = Paragraph(address, ParagraphStyle(
                    'AddressStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                ownership = business.get('ownership_name') or '—'
                ownership_paragraph = Paragraph(ownership, ParagraphStyle(
                    'OwnershipStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                status = business.get('business_status_name') or '—'
                status_paragraph = Paragraph(status, ParagraphStyle(
                    'StatusStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                table_data.append([
                    business_name_paragraph,
                    owner_paragraph,
                    type_paragraph,
                    category_paragraph,
                    address_paragraph,
                    ownership_paragraph,
                    status_paragraph,
                ])
            
            # Create table with proper column widths (total: 7.0 inches for A4 with 0.5" margins)
            col_widths = [1.3*inch, 1.1*inch, 0.85*inch, 0.75*inch, 1.5*inch, 0.75*inch, 0.75*inch]
            
            business_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
            
            # Table styling
            business_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 1), (-1, -1), 4),
                ('RIGHTPADDING', (0, 1), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ]))
            
            elements.append(business_table)
        else:
            # No businesses found
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Roman'
            )
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("No businesses found matching the applied filters.", no_data_style))
        
        # Footer info
        elements.append(Spacer(1, 0.1*inch))
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(businesses)}", footer_info_style))
        
        # Footer with page numbers (matching household list)
        def add_page_number(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF
        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number,
                  canvasmaker=BusinessListCanvas)
        buffer.seek(0)
        return buffer
