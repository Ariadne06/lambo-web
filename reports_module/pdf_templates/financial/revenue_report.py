"""
Revenue Report Generator.
Generates PDF report showing financial/revenue statistics.
"""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from ..base import BasePDFGenerator
from ...utils.database_helpers import get_revenue_report, format_currency


class RevenueReport(BasePDFGenerator):
    """Generate revenue/financial PDF report."""
    
    def __init__(self, date_from=None, date_to=None):
        """
        Initialize revenue report.
        
        Args:
            date_from: Start date filter (optional)
            date_to: End date filter (optional)
        """
        super().__init__(title="Revenue Report")
        self.date_from = date_from
        self.date_to = date_to
    
    def generate(self):
        """
        Generate the revenue PDF.
        
        Returns:
            BytesIO buffer containing the PDF
        """
        # Create document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.pagesize,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1.5*inch,
            bottomMargin=1*inch
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("REVENUE REPORT", self.styles['CustomTitle']))
        
        # Date range subtitle
        if self.date_from or self.date_to:
            date_range = f"Period: {self.date_from or 'Beginning'} to {self.date_to or 'Present'}"
            story.append(Paragraph(date_range, self.styles['CustomSubtitle']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Get data from database
        try:
            revenue_data = get_revenue_report(
                date_from=self.date_from,
                date_to=self.date_to
            )
            
            if revenue_data and len(revenue_data) > 0:
                data = revenue_data[0]
                
                # Revenue summary
                story.append(Paragraph("Financial Summary", self.styles['CustomHeader']))
                
                summary_data = [
                    ['Metric', 'Value'],
                    ['Total Transactions', str(data.get('total_transactions', 0))],
                    ['Total Revenue', format_currency(data.get('total_revenue', 0))],
                    ['Paid Transactions', str(data.get('paid_count', 0))],
                    ['Pending Transactions', str(data.get('pending_count', 0))],
                ]
                
                summary_table = self.create_table(summary_data, col_widths=[3*inch, 2.5*inch])
                story.append(summary_table)
                story.append(Spacer(1, 0.3*inch))
                
                # Highlight total revenue
                revenue_amount = format_currency(data.get('total_revenue', 0))
                story.append(Paragraph(
                    f"<b>Total Revenue Collected: {revenue_amount}</b>",
                    self.styles['CustomHeader']
                ))
                
            else:
                story.append(Paragraph("No revenue data available for the selected period.", 
                                     self.styles['CustomBody']))
        
        except Exception as e:
            story.append(Paragraph(f"Error generating report: {str(e)}", 
                                 self.styles['CustomBody']))
        
        # Build PDF
        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        
        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer
