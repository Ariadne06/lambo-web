"""
Harmonized Family/Household Profile PDF Report Generator
Generates comprehensive family profile with household, family, and member health information
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
from ...utils.database_helpers import get_harmonized_family_profile, get_quarter_info


class HarmonizedFamilyProfileCanvas(canvas.Canvas):
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


class HarmonizedFamilyProfilePDF:
    """Generates a harmonized family/household profile PDF report."""
    
    def __init__(self, family_id, quarter_id=None):
        """Initialize with family ID and optional quarter."""
        self.family_id = int(family_id)
        self.quarter_id = int(quarter_id) if quarter_id and str(quarter_id).isdigit() else None
    
    def _get_profile_data(self):
        """Fetch harmonized family profile data using database helper."""
        return get_harmonized_family_profile(self.family_id, self.quarter_id)
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        profile = self._get_profile_data()
        if not profile:
            return self._generate_error_pdf(buffer, "Family profile not found")
        
        household = profile.get('household', {})
        family = profile.get('family', {})
        members = profile.get('members', [])
        quarter_id = profile.get('quarter_id')
        
        # Build document title
        family_code = family.get('family_code', 'Unknown')
        doc_title = f"{family_code} - Harmonized Family Profile"
        
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
            subject='Harmonized Family/Household Profile Report'
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
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Times-Roman'
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
            fontSize=11,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Bold'
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Roman'
        )
        
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_LEFT,
            fontName='Times-Roman'
        )
        
        # Title
        elements.append(Paragraph("HARMONIZED FAMILY/HOUSEHOLD PROFILE", title_style))
        
        # Quarter information
        if quarter_id:
            quarter_info = get_quarter_info(quarter_id)
            if quarter_info:
                quarter_text = f"Quarter {quarter_info['quarter_number']} {quarter_info['year']}"
                elements.append(Paragraph(quarter_text, subtitle_style))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # SECTION 1: Household Information
        header_table = Table([[Paragraph("HOUSEHOLD INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        household_info = [
            ["Household Number:", household.get('household_number', '—')],
            ["Household Head:", household.get('household_head', '—')],
            ["Full Address:", household.get('full_address', '—')],
            ["House Ownership:", household.get('house_ownership', '—')],
            ["House Type:", household.get('house_type', '—')],
            ["Active Status:", 'Active' if household.get('is_active') else 'Inactive'],
        ]
        
        household_table_data = []
        for label, value in household_info:
            household_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        household_table = Table(household_table_data, colWidths=[1.5*inch, 5.5*inch])
        household_table.setStyle(_get_data_table_style())
        elements.append(household_table)
        elements.append(Spacer(1, 0.1*inch))
        
        # SECTION 2: Family Information (Compact 2-column layout)
        header_table = Table([[Paragraph("FAMILY INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Compact family info in 2 columns (4 cells per row: label1, value1, label2, value2)
        family_compact_data = []
        
        # Row 1
        family_compact_data.append([
            Paragraph("<b>Family Code:</b>", label_style),
            Paragraph(family.get('family_code') or '—', value_style),
            Paragraph("<b>Family Head:</b>", label_style),
            Paragraph(family.get('family_head') or '—', value_style),
        ])
        
        # Row 2
        family_compact_data.append([
            Paragraph("<b>Respondent:</b>", label_style),
            Paragraph(family.get('respondent') or '—', value_style),
            Paragraph("<b>Respondent Rel.:</b>", label_style),
            Paragraph(family.get('respondent_relationship') or '—', value_style),
        ])
        
        # Row 3
        family_compact_data.append([
            Paragraph("<b>Family Head Rel. to HH:</b>", label_style),
            Paragraph(family.get('relationship_of_family_head_to_hh') or '—', value_style),
            Paragraph("<b>Household Type:</b>", label_style),
            Paragraph(family.get('household_type') or '—', value_style),
        ])
        
        # Row 4
        family_compact_data.append([
            Paragraph("<b>NHTS Status:</b>", label_style),
            Paragraph('Yes' if family.get('nhts_status') else 'No', value_style),
            Paragraph("<b>IP Status:</b>", label_style),
            Paragraph('Yes' if family.get('ip_status') else 'No', value_style),
        ])
        
        # Row 5 - IP Tribe (if applicable) or Water Source
        if family.get('ip_status') and family.get('ip_tribe'):
            family_compact_data.append([
                Paragraph("<b>IP Tribe:</b>", label_style),
                Paragraph(family.get('ip_tribe') or '—', value_style),
                Paragraph("<b>Water Source:</b>", label_style),
                Paragraph(family.get('water_source') or '—', value_style),
            ])
        else:
            family_compact_data.append([
                Paragraph("<b>Water Source:</b>", label_style),
                Paragraph(family.get('water_source') or '—', value_style),
                Paragraph("<b>Waste Management:</b>", label_style),
                Paragraph(family.get('waste_management') or '—', value_style),
            ])
        
        # Row 6
        if family.get('ip_status') and family.get('ip_tribe'):
            family_compact_data.append([
                Paragraph("<b>Waste Management:</b>", label_style),
                Paragraph(family.get('waste_management') or '—', value_style),
                Paragraph("<b>Toilet Facility:</b>", label_style),
                Paragraph(family.get('toilet_facility') or '—', value_style),
            ])
        else:
            family_compact_data.append([
                Paragraph("<b>Toilet Facility:</b>", label_style),
                Paragraph(family.get('toilet_facility') or '—', value_style),
                Paragraph("", value_style),
                Paragraph("", value_style),
            ])
        
        family_table = Table(family_compact_data, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
        family_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(family_table)
        elements.append(Spacer(1, 0.1*inch))
        
        # SECTION 3: Family Members
        header_table = Table([[Paragraph("FAMILY MEMBERS", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        if members:
            for idx, member in enumerate(members, 1):
                gh = member.get('general_health', {})
                
                # Member header with name
                member_name = member.get('resident_full_name') or '—'
                member_code = member.get('family_member_code') or '—'
                member_header_text = f"{idx}. {member_name} ({member_code})"
                
                member_header_para = Paragraph(f"<b>{member_header_text}</b>", label_style)
                member_header_table = Table([[member_header_para]], colWidths=[7.0*inch])
                member_header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E5E7EB')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(member_header_table)
                elements.append(Spacer(1, 2))
                
                # Compact member information in 3 columns
                member_data = []
                
                # Row 1: Basic Demographics
                member_data.append([
                    Paragraph("<b>Age:</b>", label_style),
                    Paragraph(str(gh.get('age')) if gh.get('age') is not None else '—', value_style),
                    Paragraph("<b>Sex:</b>", label_style),
                    Paragraph(str(gh.get('sex', '—')).capitalize() if gh.get('sex') else '—', value_style),
                    Paragraph("<b>Classification:</b>", label_style),
                    Paragraph(gh.get('class_description') or '—', value_style),
                ])
                
                # Row 2: Relationships
                member_data.append([
                    Paragraph("<b>RTH:</b>", label_style),
                    Paragraph(member.get('rth_name') or '—', value_style),
                    Paragraph("<b>RTF:</b>", label_style),
                    Paragraph(member.get('rtf_name') or '—', value_style),
                    Paragraph("<b>Nutritional Status:</b>", label_style),
                    Paragraph(member.get('nutrition_status_name') or '—', value_style),
                ])
                
                # Row 3: PhilHealth Information
                membership_type = 'Member' if member.get('membership_type') == 'M' else 'Dependent' if member.get('membership_type') == 'D' else '—'
                member_data.append([
                    Paragraph("<b>PhilHealth #:</b>", label_style),
                    Paragraph(member.get('philhealthid_number') or '—', value_style),
                    Paragraph("<b>Type:</b>", label_style),
                    Paragraph(membership_type, value_style),
                    Paragraph("<b>Category:</b>", label_style),
                    Paragraph(member.get('philhealth_category_name') or '—', value_style),
                ])
                
                # Row 4: Health Behaviors
                if gh:
                    member_data.append([
                        Paragraph("<b>Smoker:</b>", label_style),
                        Paragraph('Yes' if gh.get('smoker') else 'No', value_style),
                        Paragraph("<b>Alcohol Drinker:</b>", label_style),
                        Paragraph('Yes' if gh.get('alcohol_drinker') else 'No', value_style),
                        Paragraph("<b>Sexually Active:</b>", label_style),
                        Paragraph('Yes' if gh.get('sexually_active') else 'No', value_style),
                    ])
                    
                    # Row 5: Medical History (spans all columns)
                    med_history = gh.get('medical_history_names', [])
                    med_history_text = ', '.join(med_history) if med_history else 'None'
                    member_data.append([
                        Paragraph("<b>Medical History:</b>", label_style),
                        Paragraph(med_history_text, value_style),
                        Paragraph("", value_style),
                        Paragraph("", value_style),
                        Paragraph("", value_style),
                        Paragraph("", value_style),
                    ])
                    
                    # Female-specific health info
                    if gh.get('sex', '').lower() == 'female':
                        female_info_added = False
                        female_row = []
                        
                        # Age of Menarche
                        if gh.get('age_of_menarche') is not None:
                            female_row.extend([
                                Paragraph("<b>Age of Menarche:</b>", label_style),
                                Paragraph(str(gh.get('age_of_menarche')), value_style),
                            ])
                            female_info_added = True
                        else:
                            female_row.extend([Paragraph("", value_style), Paragraph("", value_style)])
                        
                        # FP Status
                        if gh.get('fp_status_name'):
                            female_row.extend([
                                Paragraph("<b>FP Status:</b>", label_style),
                                Paragraph(gh.get('fp_status_name') or '—', value_style),
                            ])
                            female_info_added = True
                        else:
                            female_row.extend([Paragraph("", value_style), Paragraph("", value_style)])
                        
                        # FP Method
                        if gh.get('fp_method_yn') is not None:
                            fp_method = gh.get('fp_method_name') if gh.get('fp_method_yn') else 'Not using'
                            female_row.extend([
                                Paragraph("<b>FP Method:</b>", label_style),
                                Paragraph(fp_method or '—', value_style),
                            ])
                            female_info_added = True
                        else:
                            female_row.extend([Paragraph("", value_style), Paragraph("", value_style)])
                        
                        if female_info_added:
                            member_data.append(female_row)
                        
                        # LMP in separate row if exists
                        if gh.get('last_menstrual_period'):
                            lmp = gh.get('last_menstrual_period')
                            if isinstance(lmp, str):
                                try:
                                    dt = datetime.fromisoformat(lmp.replace('Z', '+00:00'))
                                    lmp_formatted = dt.strftime('%B %d, %Y')
                                except:
                                    lmp_formatted = lmp
                            else:
                                lmp_formatted = lmp.strftime('%B %d, %Y') if hasattr(lmp, 'strftime') else str(lmp)
                            
                            member_data.append([
                                Paragraph("<b>Last Menstrual Period:</b>", label_style),
                                Paragraph(lmp_formatted, value_style),
                                Paragraph("", value_style),
                                Paragraph("", value_style),
                                Paragraph("", value_style),
                                Paragraph("", value_style),
                            ])
                
                # Create compact table with 6 columns (label-value pairs)
                col_widths = [1.0*inch, 1.3*inch, 0.8*inch, 1.3*inch, 1.1*inch, 1.5*inch]
                member_table = Table(member_data, colWidths=col_widths)
                member_table.setStyle(TableStyle([
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ]))
                elements.append(member_table)
                
                # Add spacing between members (except after last)
                if idx < len(members):
                    elements.append(Spacer(1, 0.08*inch))
        else:
            elements.append(Paragraph("<i>No family members registered.</i>", value_style))
        
        elements.append(Spacer(1, 0.1*inch))
        
        # SECTION 4: Visitation Information
        header_table = Table([[Paragraph("VISITATION INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B'))]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        visitation_info = [
            ["Visited:", 'Yes' if family.get('is_visited') else 'No'],
        ]
        
        if family.get('is_visited') and family.get('date_visited'):
            visited_date = family['date_visited']
            if isinstance(visited_date, str):
                # Parse ISO format datetime
                try:
                    dt = datetime.fromisoformat(visited_date.replace('Z', '+00:00'))
                    visitation_info.append(["Date Visited:", dt.strftime('%B %d, %Y')])
                except:
                    visitation_info.append(["Date Visited:", visited_date])
            else:
                visitation_info.append(["Date Visited:", visited_date.strftime('%B %d, %Y') if hasattr(visited_date, 'strftime') else str(visited_date)])
            
            if family.get('visited_by_full_name'):
                visitation_info.append(["Visited By:", family.get('visited_by_full_name', '—')])
        
        visitation_table_data = []
        for label, value in visitation_info:
            visitation_table_data.append([
                Paragraph(label, label_style),
                Paragraph(str(value), value_style)
            ])
        
        visitation_table = Table(visitation_table_data, colWidths=[1.5*inch, 5.5*inch])
        visitation_table.setStyle(_get_data_table_style())
        elements.append(visitation_table)
        elements.append(Spacer(1, 0.1*inch))
        
        # Footer Metadata
        elements.append(Spacer(1, 0.05*inch))
        current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
        elements.append(Paragraph(f"<b>Generated:</b> {current_date}", metadata_style))
        
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
        
        # Build PDF with custom canvas
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=HarmonizedFamilyProfileCanvas)
        buffer.seek(0)
        return buffer
    
    def _generate_error_pdf(self, buffer, message):
        """Generate a simple error PDF."""
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
        elements.append(Paragraph(f"<b>Error:</b> {message}", error_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer


def _get_data_table_style():
    """Returns consistent table style for data sections"""
    return TableStyle([
        # Labels background
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
    ])
