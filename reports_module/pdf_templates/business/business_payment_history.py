"""
Business Payment History PDF Report Generator
Generates payment transaction history for a specific business with filter support
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
from decimal import Decimal
from ..base import draw_barangay_header, get_standard_styles, draw_watermark
from django.db import connection


class BusinessPaymentHistoryCanvas(canvas.Canvas):
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


def _get_data_table_style():
    """Return standard table style for data tables."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ])


class BusinessPaymentHistoryPDF:
    """Generates payment transaction history PDF for a business."""
    
    def __init__(self, business_id, query=None, payment_status=None, date_from=None, date_to=None):
        """Initialize with business ID and optional filters."""
        self.business_id = int(business_id)
        self.query = query
        self.payment_status = payment_status
        self.date_from = date_from
        self.date_to = date_to
    
    def _get_business(self):
        """Fetch business details using database function."""
        with connection.cursor() as cursor:
            cursor.callproc('get_business_detail', [self.business_id])
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            if rows:
                return dict(zip(cols, rows[0]))
            return None
    
    def _get_payment_history(self):
        """Fetch payment history using database function."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM get_specific_business_payment_history(%s,%s,%s,%s,%s,%s,%s)",
                [self.business_id, self.query, self.payment_status, self.date_from, self.date_to, 999999, 0]
            )
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
            # Debug: print column names to help diagnose
            if rows:
                print(f"DEBUG - Payment history columns: {cols}")
                print(f"DEBUG - First row data: {rows[0]}")
            return rows
    
    def _generate_error_pdf(self, buffer, error_message):
        """Generate an error PDF when business is not found."""
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = get_standard_styles()
        
        error_style = ParagraphStyle(
            'Error',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.red,
            alignment=TA_CENTER
        )
        
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph(error_message, error_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch business data
        business = self._get_business()
        if not business:
            return self._generate_error_pdf(buffer, "Business not found")
        
        # Fetch payment history
        payments = self._get_payment_history()
        
        # Build document title
        business_name = business.get('business_name', 'Unknown')
        doc_title = f"{business_name} - Payment History"
        
        # Create document with custom header/footer
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title=doc_title,
            author='LAMBO System',
            subject='Business Payment History Report'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles using Times-Roman
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=17,
            textColor=colors.HexColor('#991B1B'),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=11,
            textColor=colors.white,
            spaceBefore=10,
            spaceAfter=2,
            alignment=TA_LEFT,
            fontName='Times-Bold',
            backColor=colors.HexColor('#991B1B'),
            leftIndent=6,
            rightIndent=6
        )
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Bold'
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Roman'
        )
        
        filter_style = ParagraphStyle(
            'Filter',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_LEFT,
            fontName='Times-Italic',
            spaceAfter=6
        )
        
        # Title
        elements.append(Paragraph("BUSINESS PAYMENT HISTORY", title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # SECTION 1: Business Information
        header_table = Table([[Paragraph("BUSINESS INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        business_info = [
            ["Business ID:", str(business.get('business_id', '—'))],
            ["Business Name:", business.get('business_name', '—')],
            ["Owner Name:", business.get('owner_name', '—')],
            ["Business Type:", business.get('business_type_name') or business.get('business_type', '—')],
            ["Status:", business.get('business_status_name') or business.get('status', '—')],
            ["Address:", business.get('address', '—')],
        ]
        
        business_table_data = []
        for label, value in business_info:
            business_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        business_table = Table(business_table_data, colWidths=[1.5*inch, 5.5*inch])
        business_table.setStyle(_get_data_table_style())
        elements.append(business_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Filter Summary
        filter_parts = []
        if self.query:
            filter_parts.append(f"Search: '{self.query}'")
        if self.payment_status:
            filter_parts.append(f"Status: {self.payment_status}")
        if self.date_from:
            filter_parts.append(f"From: {self.date_from}")
        if self.date_to:
            filter_parts.append(f"To: {self.date_to}")
        
        if filter_parts:
            filter_text = "<b>Applied Filters:</b> " + " | ".join(filter_parts)
            elements.append(Paragraph(filter_text, filter_style))
            elements.append(Spacer(1, 0.05*inch))
        
        # SECTION 2: Payment Transactions
        header_table = Table([[Paragraph("PAYMENT TRANSACTIONS", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 8))
        
        if not payments:
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#6B7280'),
                alignment=TA_CENTER,
                fontName='Times-Italic'
            )
            elements.append(Paragraph("No payment transactions found with the specified filters.", no_data_style))
        else:
            # Payment table headers
            payment_table_data = []
            
            # Header row
            header_cell_style = ParagraphStyle(
                'HeaderCell',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.white,
                fontName='Times-Bold',
                alignment=TA_CENTER
            )
            
            payment_table_data.append([
                Paragraph("Date Paid", header_cell_style),
                Paragraph("Request", header_cell_style),
                Paragraph("App. Code", header_cell_style),
                Paragraph("OR Number", header_cell_style),
                Paragraph("Status", header_cell_style),
                Paragraph("Amount", header_cell_style),
            ])
            
            # Data rows
            data_cell_style = ParagraphStyle(
                'DataCell',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#374151'),
                fontName='Times-Roman',
                alignment=TA_LEFT
            )
            
            amount_cell_style = ParagraphStyle(
                'AmountCell',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#374151'),
                fontName='Times-Roman',
                alignment=TA_RIGHT
            )
            
            total_amount = 0
            for payment in payments:
                date_paid = payment.get('date_paid')
                if date_paid:
                    if hasattr(date_paid, 'strftime'):
                        date_paid_str = date_paid.strftime('%m/%d/%Y')
                    else:
                        date_paid_str = str(date_paid)[:10]
                else:
                    date_paid_str = "—"
                
                request_label = payment.get('request_label') or payment.get('fee_type_name') or payment.get('purpose') or "—"
                app_code = payment.get('application_code') or "—"
                or_number = payment.get('or_number') or "—"
                status = payment.get('payment_status') or "—"
                
                # Try multiple amount field names from the database function
                amount = payment.get('amount') or payment.get('total_amount') or payment.get('amount_paid')
                if amount:
                    try:
                        amount_val = float(amount)
                        if status and str(status).lower() == 'paid':
                            total_amount += amount_val
                        amount_str = f"Php {amount_val:,.2f}"
                    except:
                        amount_str = str(amount)
                else:
                    amount_str = "—"
                
                # Use plain strings for better alignment, no Paragraph wrapping
                payment_table_data.append([
                    date_paid_str,
                    str(request_label)[:40],  # Truncate long requests
                    str(app_code),
                    str(or_number),
                    str(status),
                    amount_str,
                ])
            
            # Total row - use plain strings instead of Paragraph to avoid wrapping
            # Span first 4 columns for empty space, then 2 columns for total
            payment_table_data.append([
                "",
                "",
                "",
                "",
                "TOTAL PAID:",
                f"Php {total_amount:,.2f}",
            ])
            
            # Column widths: Date(1.0) + Request(2.0) + AppCode(1.3) + OR(1.0) + Status(0.7) + Amount(1.0) = 7.0"
            payment_table = Table(payment_table_data, colWidths=[1.0*inch, 2.0*inch, 1.3*inch, 1.0*inch, 0.7*inch, 1.0*inch])
            
            payment_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                # Data rows styling
                ('FONTNAME', (0, 1), (-1, -2), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('TEXTCOLOR', (0, 1), (-1, -2), colors.HexColor('#374151')),
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),   # Date
                ('ALIGN', (1, 1), (1, -2), 'LEFT'),   # Request
                ('ALIGN', (2, 1), (2, -2), 'LEFT'),   # App Code
                ('ALIGN', (3, 1), (3, -2), 'LEFT'),   # OR Number
                ('ALIGN', (4, 1), (4, -2), 'CENTER'), # Status
                ('ALIGN', (5, 1), (5, -2), 'RIGHT'),  # Amount
                ('VALIGN', (0, 1), (-1, -2), 'MIDDLE'),
                # Total row styling - span first 4 columns, then 2 separate columns for label and amount
                ('SPAN', (0, -1), (3, -1)),  # Merge first 4 columns in total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, -1), (-1, -1), 'Times-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 10),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#374151')),
                ('ALIGN', (4, -1), (4, -1), 'RIGHT'),   # "TOTAL PAID:" label right-aligned
                ('ALIGN', (5, -1), (5, -1), 'RIGHT'),   # Amount right-aligned
                ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'),
                # Grid and padding
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                # Match vertical lines in total row to background color
                ('LINEAFTER', (0, -1), (3, -1), 0.5, colors.HexColor('#F3F4F6')),
                ('LINEBEFORE', (4, -1), (4, -1), 0.5, colors.HexColor('#F3F4F6')),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                # Alternating row colors (skip header and total)
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F9FAFB')]),
            ]))
            
            elements.append(payment_table)
        
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
        elements.append(Paragraph(f"<b>Total Records:</b> {len(payments)}", footer_info_style))
        
        elements.append(Spacer(1, 0.05*inch))
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
            "For verification purposes, please contact the Barangay Secretary's Office.",
            footer_style
        ))
        
        # Page number footer
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
                  canvasmaker=BusinessPaymentHistoryCanvas)
        buffer.seek(0)
        return buffer
