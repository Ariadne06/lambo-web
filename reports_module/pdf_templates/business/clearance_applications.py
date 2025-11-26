"""
Clearance Applications Report Generator.
Generates PDF report listing clearance applications with filters.
"""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from ..base import BasePDFGenerator
from ...utils.database_helpers import (
    get_clearance_applications_report, 
    format_datetime_for_report,
    format_currency
)


class ClearanceApplicationsReport(BasePDFGenerator):
    """Generate clearance applications PDF report."""
    
    def __init__(self, date_from=None, date_to=None, status=None):
        """
        Initialize clearance applications report.
        
        Args:
            date_from: Start date filter (optional)
            date_to: End date filter (optional)
            status: Application status filter (optional)
        """
        super().__init__(title="Clearance Applications Report")
        self.date_from = date_from
        self.date_to = date_to
        self.status = status
    
    def generate(self):
        """
        Generate the clearance applications PDF.
        
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
        story.append(Paragraph("CLEARANCE APPLICATIONS REPORT", self.styles['CustomTitle']))
        
        # Filters subtitle
        filters = []
        if self.date_from:
            filters.append(f"From: {self.date_from}")
        if self.date_to:
            filters.append(f"To: {self.date_to}")
        if self.status:
            filters.append(f"Status: {self.status}")
        
        if filters:
            story.append(Paragraph(" | ".join(filters), self.styles['CustomSubtitle']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Get data from database
        try:
            applications = get_clearance_applications_report(
                date_from=self.date_from,
                date_to=self.date_to,
                status=self.status
            )
            
            if applications and len(applications) > 0:
                # Applications table
                story.append(Paragraph("Applications List", self.styles['CustomHeader']))
                
                table_data = [['Code', 'Applicant', 'Status', 'Payment', 'Amount', 'Date']]
                
                total_amount = 0
                for app in applications:
                    table_data.append([
                        app.get('application_code', ''),
                        app.get('applicant_name', '')[:25],  # Truncate long names
                        app.get('application_status', ''),
                        app.get('payment_status', ''),
                        format_currency(app.get('total_amount', 0)),
                        str(app.get('created_at', ''))[:10] if app.get('created_at') else ''
                    ])
                    total_amount += float(app.get('total_amount', 0))
                
                # Add total row
                table_data.append(['', '', '', 'TOTAL', format_currency(total_amount), ''])
                
                applications_table = self.create_table(
                    table_data,
                    col_widths=[1.2*inch, 1.8*inch, 1*inch, 1*inch, 1*inch, 1*inch]
                )
                story.append(applications_table)
                story.append(Spacer(1, 0.2*inch))
                
                # Summary
                story.append(Paragraph(f"Total Applications: {len(applications)}", 
                                     self.styles['CustomBody']))
                
            else:
                story.append(Paragraph("No applications found for the selected filters.", 
                                     self.styles['CustomBody']))
        
        except Exception as e:
            story.append(Paragraph(f"Error generating report: {str(e)}", 
                                 self.styles['CustomBody']))
        
        # Build PDF
        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        
        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer
