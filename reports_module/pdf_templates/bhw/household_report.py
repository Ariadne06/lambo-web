"""
BHW Household Report PDF Generator
Generates filtered household reports based on type (all/active/visited)
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
from household_module.models import Household


class HouseholdReportCanvas(canvas.Canvas):
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


class HouseholdReportPDF:
    """Generates BHW household report PDF."""
    
    def __init__(self, report_type='all', start_date=None, end_date=None):
        """Initialize the household report generator."""
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        
        # Report type labels
        self.type_labels = {
            'all': 'All Households Report',
            'active': 'Active Households Report',
            'visited': 'Recently Visited Households Report'
        }
    
    def _get_household_data(self):
        """Fetch household data from database."""
        if self.report_type == 'active':
            return Household.sp_get_active_households_report(
                start_date=self.start_date,
                end_date=self.end_date
            )
        elif self.report_type == 'visited':
            return Household.sp_get_visited_households_report(
                start_date=self.start_date,
                end_date=self.end_date
            )
        else:
            return Household.sp_get_all_households_report(
                start_date=self.start_date,
                end_date=self.end_date
            )
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        households = self._get_household_data()
        
        # Create document - Portrait orientation
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title='Household Report',
            author='LAMBO System',
            subject='Barangay Health Worker Household Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles using Times-Roman (matching other reports)
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
        title_text = self.type_labels.get(self.report_type, 'Household Report')
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(households)}", metadata_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Household List Table
        if households:
            # Table headers
            table_data = [[
                'Household No.',
                'Household Head',
                'Address',
                'Sitio',
                'Families',
                'Members',
                'Last Visit'
            ]]
            
            # Table rows
            for hh in households:
                # Format last visit date
                last_visit = '—'
                if hh.get('last_visit_date'):
                    try:
                        if hasattr(hh['last_visit_date'], 'strftime'):
                            last_visit = hh['last_visit_date'].strftime('%Y-%m-%d')
                        else:
                            last_visit_str = str(hh['last_visit_date'])
                            last_visit = last_visit_str[:10] if len(last_visit_str) >= 10 else last_visit_str
                    except:
                        last_visit = '—'
                
                # Use Paragraph for address and household head to handle wrapping
                address = hh.get('address') or '—'
                address_paragraph = Paragraph(address, ParagraphStyle(
                    'AddressStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                household_head = hh.get('household_head_name') or '—'
                head_paragraph = Paragraph(household_head, ParagraphStyle(
                    'HeadStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                # Use Paragraph for sitio to handle wrapping
                sitio_name = hh.get('sitio_name') or '—'
                sitio_paragraph = Paragraph(sitio_name, ParagraphStyle(
                    'SitioStyle',
                    parent=styles['Normal'],
                    fontSize=7,
                    fontName='Times-Roman',
                    leading=8
                ))
                
                table_data.append([
                    hh.get('household_number') or '—',
                    head_paragraph,
                    address_paragraph,
                    sitio_paragraph,
                    str(hh.get('total_families') or 0),
                    str(hh.get('total_members') or 0),
                    last_visit
                ])
            
            # Create table with proper column widths (A4 width is 8.27", minus 1.0" margins = 7.27" available)
            col_widths = [1.0*inch, 1.2*inch, 2.4*inch, 1.0*inch, 0.55*inch, 0.57*inch, 0.75*inch]
            
            household_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Table styling (matching other reports)
            household_table.setStyle(TableStyle([
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
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Household No
                ('ALIGN', (1, 1), (3, -1), 'LEFT'),    # Head, Address, Sitio
                ('ALIGN', (4, 1), (-1, -1), 'CENTER'), # Families, Members, Last Visit
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
            elements.append(Paragraph("No households found matching the specified criteria.", no_data_style))
        
        # Add metadata at the bottom (matching child_health_list and household_list)
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(households)}", metadata_style))
        
        # Page footer function (matching household_list and child_health_list)
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas (matching child_health_list and household_list)
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=HouseholdReportCanvas)
        buffer.seek(0)
        return buffer
