"""
Treasurer Financial Report PDF Generator
Generates detailed financial report with OR numbers and transactions
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
from decimal import Decimal as D
from ..base import draw_barangay_header, get_standard_styles, draw_watermark


class FinancialReportCanvas(canvas.Canvas):
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


class FinancialReportPDF:
    """Generates a treasurer financial report PDF."""
    
    def __init__(self, financial_data, filters_applied):
        """
        Initialize with financial data and filter parameters.
        
        Args:
            financial_data: List of transaction dictionaries from treasurer_get_financial_report
            filters_applied: Dictionary containing filter information
                {
                    'year': int or None,
                    'month': int or None,
                    'month_name': str or None,
                    'start_date': str or None,
                    'end_date': str or None
                }
        """
        self.financial_data = financial_data
        self.filters = filters_applied
        
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Build title based on filters
        year = self.filters.get('year')
        month_name = self.filters.get('month_name')
        start_date = self.filters.get('start_date')
        end_date = self.filters.get('end_date')
        
        if month_name and year:
            doc_title = f"Financial Report - {month_name} {year}"
        elif year:
            doc_title = f"Financial Report - {year}"
        elif start_date and end_date:
            doc_title = f"Financial Report - {start_date} to {end_date}"
        else:
            doc_title = "Financial Report"
        
        # Create document - Use portrait orientation
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title=doc_title,
            author='LAMBO System',
            subject='Treasurer Financial Report'
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
        elements.append(Paragraph("TREASURER FINANCIAL REPORT", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Applied Filters Section
        filter_data = []
        
        # Year filter
        if year:
            filter_data.append(['Year:', str(year)])
        
        # Month filter
        if month_name:
            filter_data.append(['Month:', month_name])
        
        # Date range filters
        if start_date:
            filter_data.append(['Start Date:', start_date])
        if end_date:
            filter_data.append(['End Date:', end_date])
        
        if filter_data:
            elements.append(Paragraph("<b>Applied Filters:</b>", filter_style))
            elements.append(Spacer(1, 0.05*inch))
            
            # Convert filter values to Paragraphs for wrapping
            formatted_filter_data = []
            for label, value in filter_data:
                formatted_filter_data.append([
                    Paragraph(f"<b>{label}</b>", filter_style),
                    Paragraph(str(value), filter_style)
                ])
            
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
            elements.append(Paragraph("<b>Filters:</b> None (All Transactions)", filter_style))
            elements.append(Spacer(1, 0.15*inch))
        
        # Financial Data Table
        if self.financial_data:
            # Table headers
            table_data = [[
                'OR Number',
                'Purpose',
                'Issued By',
                'Date Issued',
                'Amount'
            ]]
            
            # Calculate total
            total_amount = D('0')
            
            # Table rows
            for record in self.financial_data:
                or_number = str(record.get('or_number', '___') or '___')
                purpose = str(record.get('purpose', '___') or '___')
                issued_by = str(record.get('issued_by', '___') or '___')
                
                # Format date
                issued_at = record.get('issued_at')
                if issued_at:
                    try:
                        if isinstance(issued_at, str):
                            from dateutil import parser
                            issued_at = parser.parse(issued_at)
                        date_str = issued_at.strftime('%b %d, %Y')
                    except:
                        date_str = str(issued_at)[:10]
                else:
                    date_str = '___'
                
                # Amount
                amount = record.get('total_amount', D('0')) or D('0')
                try:
                    if isinstance(amount, str):
                        amount = D(amount)
                    total_amount += amount
                except:
                    amount = D('0')
                
                table_data.append([
                    or_number,
                    purpose,
                    issued_by,
                    date_str,
                    f'Php {float(amount):,.2f}'
                ])
            
            # Add totals row
            table_data.append([
                '',
                '',
                '',
                Paragraph('<b>TOTAL:</b>', filter_style),
                f'Php {float(total_amount):,.2f}'
            ])
            
            # Create table with proper column widths for portrait
            col_widths = [1.0*inch, 1.8*inch, 1.5*inch, 1.0*inch, 1.7*inch]
            
            financial_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
            
            # Table styling (matching resident and household lists)
            financial_table.setStyle(TableStyle([
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
                ('FONTNAME', (0, 1), (-1, -2), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                ('ALIGN', (1, 1), (1, -2), 'LEFT'),
                ('ALIGN', (2, 1), (2, -2), 'LEFT'),
                ('ALIGN', (3, 1), (3, -2), 'CENTER'),
                ('ALIGN', (4, 1), (4, -2), 'RIGHT'),
                ('VALIGN', (0, 1), (-1, -2), 'MIDDLE'),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F9FAFB')]),
                
                # Totals row (last row)
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, -1), (-1, -1), 'Times-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                ('ALIGN', (3, -1), (3, -1), 'RIGHT'),
                ('ALIGN', (4, -1), (4, -1), 'RIGHT'),
                ('TOPPADDING', (0, -1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#991B1B')),
                
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -2), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -2), 5),
                
                # Line below last row before split
                ('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 1, colors.HexColor('#991B1B')),
            ]))
            
            elements.append(financial_table)
        else:
            # No data found
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph("No financial data found matching the specified filters.", no_data_style))
        
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(self.financial_data)}", metadata_style))
        
        # Footer with page numbers
        def add_page_number(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = f"Page {canvas_obj.getPageNumber()}"
            canvas_obj.drawRightString(A4[0] - 0.5*inch, 0.5*inch, page_num)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas
        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number,
                  canvasmaker=FinancialReportCanvas)
        
        buffer.seek(0)
        return buffer


def generate_financial_report_pdf(financial_data, filters_applied):
    """
    Convenience function to generate financial report PDF.
    
    Args:
        financial_data: List of transaction dictionaries
        filters_applied: Dictionary of filter information
    
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = FinancialReportPDF(financial_data, filters_applied)
    return generator.generate()
