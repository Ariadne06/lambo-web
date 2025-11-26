"""
Resident Statistics Report Generator.
Generates PDF report showing resident demographics and statistics.
"""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from ..base import BasePDFGenerator
from ...utils.database_helpers import get_resident_statistics, format_datetime_for_report


class ResidentStatisticsReport(BasePDFGenerator):
    """Generate resident statistics PDF report."""
    
    def __init__(self, date_from=None, date_to=None):
        """
        Initialize resident statistics report.
        
        Args:
            date_from: Start date filter (optional)
            date_to: End date filter (optional)
        """
        super().__init__(title="Resident Statistics Report")
        self.date_from = date_from
        self.date_to = date_to
    
    def generate(self):
        """
        Generate the resident statistics PDF.
        
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
        story.append(Paragraph("RESIDENT STATISTICS REPORT", self.styles['CustomTitle']))
        
        # Date range subtitle
        if self.date_from or self.date_to:
            date_range = f"Period: {self.date_from or 'Beginning'} to {self.date_to or 'Present'}"
            story.append(Paragraph(date_range, self.styles['CustomSubtitle']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Get data from database
        try:
            stats = get_resident_statistics(
                date_from=self.date_from,
                date_to=self.date_to
            )
            
            if stats and len(stats) > 0:
                data = stats[0]
                
                # Summary section
                story.append(Paragraph("Summary", self.styles['CustomHeader']))
                
                summary_data = [
                    ['Metric', 'Count'],
                    ['Total Residents', str(data.get('total_residents', 0))],
                    ['Male', str(data.get('male_count', 0))],
                    ['Female', str(data.get('female_count', 0))],
                    ['Registered Voters', str(data.get('registered_voters', 0))],
                ]
                
                summary_table = self.create_table(summary_data, col_widths=[3*inch, 2*inch])
                story.append(summary_table)
                story.append(Spacer(1, 0.3*inch))
                
                # Additional statistics can be added here
                
            else:
                story.append(Paragraph("No data available for the selected period.", 
                                     self.styles['CustomBody']))
        
        except Exception as e:
            story.append(Paragraph(f"Error generating report: {str(e)}", 
                                 self.styles['CustomBody']))
        
        # Build PDF
        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        
        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer
