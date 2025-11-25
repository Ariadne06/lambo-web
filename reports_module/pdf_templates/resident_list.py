"""
Resident List Report Generator.
Generates PDF report listing all residents with full details.
"""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from datetime import datetime
from .base import BasePDFGenerator
from ..utils.database_helpers import get_resident_list_report


class ResidentListReport(BasePDFGenerator):
    """Generate resident list PDF report."""
    
    def __init__(self):
        """Initialize resident list report."""
        super().__init__(title="Resident List Report")
    
    def generate(self):
        """
        Generate the resident list PDF.
        
        Returns:
            BytesIO buffer containing the PDF
        """
        # Create document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.pagesize,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.5*inch,
            bottomMargin=1*inch
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("RESIDENT LIST REPORT", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Get data from database
        try:
            residents = get_resident_list_report()
            
            if residents and len(residents) > 0:
                # Generation date and time - left aligned, small spacing
                generation_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
                story.append(Paragraph(
                    f"Generated on: {generation_time}",
                    self.styles['CustomSmall']
                ))
                story.append(Spacer(1, 0.1*inch))
                
                # Create a custom style that matches the table data appearance
                table_data_style = ParagraphStyle(
                    'TableData',
                    parent=self.styles['Normal'],
                    fontSize=9,
                    textColor=colors.black,
                    fontName='Helvetica',
                    alignment=TA_LEFT,
                    leading=11,
                    leftIndent=0,
                    rightIndent=0,
                    spaceAfter=0,
                    spaceBefore=0
                )
                
                # Residents table
                table_data = [[
                    'Resident Code',
                    'Full Name',
                    'Date of Birth',
                    'Address',
                    'Phone',
                    'Email'
                ]]
                
                for resident in residents:
                    # Format DOB
                    dob = str(resident.get('dob', ''))[:10] if resident.get('dob') else 'N/A'
                    
                    # Get fields
                    resident_code = str(resident.get('resident_code', ''))
                    full_name = str(resident.get('full_name', ''))
                    address = str(resident.get('full_address', ''))
                    phone = str(resident.get('phone_number', '') or 'N/A')
                    email = str(resident.get('email', '') or 'N/A')
                    
                    # Use Paragraph for all text fields to enable wrapping
                    # All use the same style for consistent appearance
                    table_data.append([
                        Paragraph(resident_code, table_data_style),
                        Paragraph(full_name, table_data_style),
                        Paragraph(dob, table_data_style),
                        Paragraph(address, table_data_style),
                        Paragraph(phone, table_data_style),
                        Paragraph(email, table_data_style)
                    ])
                
                # Create table with adjusted column widths for portrait
                # Total width available: ~7 inches in portrait A4
                residents_table = self.create_table(
                    table_data,
                    col_widths=[1.1*inch, 1.1*inch, 0.9*inch, 2.0*inch, 0.7*inch, 1.2*inch]
                )
                
                # Additional styling for better readability
                additional_style = TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 9),  # Same font size for all
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Headers bold
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),  # Data same as DOB
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),  # Same color for all data
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ])
                residents_table.setStyle(additional_style)
                
                story.append(residents_table)
                story.append(Spacer(1, 0.3*inch))
                
                # Total count at the end
                story.append(Paragraph(
                    f"<b>Total Residents: {len(residents)}</b>",
                    self.styles['CustomHeader']
                ))
                story.append(Spacer(1, 0.1*inch))
                
                # Footer note
                story.append(Paragraph(
                    f"<i>Report contains {len(residents)} registered residents with status 'Resident'.</i>",
                    self.styles['CustomSmall']
                ))
                
            else:
                story.append(Paragraph(
                    "No residents found in the system.",
                    self.styles['CustomBody']
                ))
        
        except Exception as e:
            story.append(Paragraph(
                f"Error generating report: {str(e)}",
                self.styles['CustomBody']
            ))
        
        # Build PDF
        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        
        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer
