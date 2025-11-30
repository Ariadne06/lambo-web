"""
Child Health Detail PDF Report Generator
Generates detailed health record for a specific child
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
from ..base import draw_barangay_header, get_standard_styles, draw_watermark
from bhw_module.models import Child


class ChildHealthDetailCanvas(canvas.Canvas):
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


class ChildHealthDetailPDF:
    """Generates a detailed child health record PDF report."""
    
    def __init__(self, child_health_id):
        """Initialize with child health ID."""
        self.child_health_id = int(child_health_id)
        
    def _get_child_record(self):
        """Fetch child health record from database."""
        return Child.sp_view_specific_child_health_record(self.child_health_id)
    
    def _get_medical_conditions(self):
        """Fetch medical conditions."""
        return Child.sp_view_specific_child_all_medical_condition(self.child_health_id)
    
    def _get_surgical_history(self):
        """Fetch surgical history."""
        return Child.sp_view_specific_child_all_surgical_history(self.child_health_id)
    
    def _get_immunizations(self):
        """Fetch immunization records."""
        return Child.sp_view_specific_child_immunization_record(self.child_health_id)
    
    def _get_supplements(self):
        """Fetch supplement records."""
        return Child.sp_view_all_child_supplements(self.child_health_id)
    
    def _get_growth_monitoring(self):
        """Fetch growth monitoring records."""
        return Child.sp_view_specific_child_all_growth_monitoring(self.child_health_id)
    
    def _get_breastfeeding_track(self):
        """Fetch exclusive breastfeeding tracking."""
        return Child.sp_view_specific_child_exclusive_breastfeed_track(self.child_health_id)
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        child_record = self._get_child_record()
        
        if not child_record:
            # Handle case where child record is not found
            return self._generate_not_found_pdf(buffer)
        
        medical_conditions = self._get_medical_conditions() or []
        surgical_history = self._get_surgical_history() or []
        immunizations = self._get_immunizations() or []
        supplements = self._get_supplements() or []
        growth_monitoring = self._get_growth_monitoring() or []
        breastfeeding = self._get_breastfeeding_track() or []
        
        # Create document - Portrait orientation
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title=f'Child Health Record - {child_record.get("child_full_name", "Unknown")}',
            author='LAMBO System',
            subject='Child Health Record Detail'
        )
        
        # Build elements
        elements = []
        styles = get_standard_styles()
        
        # Custom styles using Times-Roman (matching resident_detail.py)
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
        
        # Header
        elements.append(Paragraph("CHILD HEALTH RECORD", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Child Information section header
        header_table = Table([[Paragraph("CHILD INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Compact header info similar to form
        # Get cell number: mother first, then father
        cell_number = child_record.get('mother_phone_number') or child_record.get('father_phone_number') or '_______________'
        
        header_info = [
            [
                f"Child's Name: {child_record.get('child_full_name') or '_______________'}",
                f"Gender: {child_record.get('sex') or '___'}",
                f"Date of Birth: {str(child_record.get('dob', ''))[:10] if child_record.get('dob') else '_______________'}"
            ],
            [
                f"Birthweight: {child_record.get('birth_weight_kg') or '___'} kg",
                f"Birth Length: {child_record.get('birth_length_cm') or '___'} cm",
                f"Time of Birth: {child_record.get('time_of_birth') or '_______________'}"
            ],
            [
                f"Place of Delivery: {child_record.get('place_of_delivery') or '_______________'}",
                f"Family Code: {child_record.get('family_code') or '_______________'}",
                ''
            ],
            [
                f"Mother's Name: {child_record.get('mother_full_name') or '_______________'}",
                f"Mother's Age: {child_record.get('mother_age_years') or '___'}",
                ''
            ],
            [
                f"Father's Name: {child_record.get('father_full_name') or '_______________'}",
                f"Father's Age: {child_record.get('father_age_years') or '___'}",
                ''
            ],
            [
                f"PhilHealth No: {child_record.get('philhealth_no') or '_______________'}",
                f"Cell Number: {cell_number}",
                ''
            ],
        ]
        
        header_table = Table(header_info, colWidths=[2.8*inch, 2.2*inch, 2.0*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(header_table)
        
        # Complete address in separate full-width row
        address_info = [[f"Complete Address: {child_record.get('complete_address') or '_______________'}"]]
        address_table = Table(address_info, colWidths=[7.0*inch])
        address_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(address_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Health status section (form-style)
        newborn_status = 'Done' if child_record.get('newborn_screening_status') else 'NOT done'
        newborn_date = str(child_record.get('newborn_screening_status_date', ''))[:10] if child_record.get('newborn_screening_status_date') else '_______________'
        
        health_info_data = [
            [
                f"TT status of Mother: {child_record.get('tt_status_name') or '_______________'}",
                f"Date TT status assessed: {str(child_record.get('tt_status_date', ''))[:10] if child_record.get('tt_status_date') else '_______________'}"
            ],
            [
                f"Newborn Screening Status: {newborn_status}, dated: {newborn_date}",
                ''
            ],
            [
                f"Feeding method: Breastfeeding / Bottle feeding / Mixed",
                f"{child_record.get('feeding_method_name') or 'Not specified'}"
            ],
        ]
        
        health_table = Table(health_info_data, colWidths=[4.0*inch, 3.0*inch])
        health_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(health_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # === EXCLUSIVE BREASTFEEDING SECTION ===
        header_table = Table([[Paragraph("EXCLUSIVE BREASTFEEDING TRACKING", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        if breastfeeding:
            # Create horizontal layout for months 1-6
            bf_header = ['1st month', '2nd month', '3rd month', '4th month', '5th month', '6th month']
            bf_dates = []
            
            # Populate dates for each month
            for month_num in range(1, 7):
                found = False
                for bf in breastfeeding:
                    if bf.get('month_number') == month_num:
                        date_val = str(bf.get('date_assessed', ''))[:10] if bf.get('date_assessed') else ''
                        bf_dates.append(date_val if date_val else '___')
                        found = True
                        break
                if not found:
                    bf_dates.append('___')
            
            bf_data = [bf_header, bf_dates]
            bf_table = Table(bf_data, colWidths=[1.17*inch]*6)
            bf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(bf_table)
        else:
            empty_bf = [
                ['1st month', '2nd month', '3rd month', '4th month', '5th month', '6th month'],
                ['___', '___', '___', '___', '___', '___']
            ]
            bf_table = Table(empty_bf, colWidths=[1.17*inch]*6)
            bf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(bf_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # === IMMUNIZATION RECORDS SECTION ===
        header_table = Table([[Paragraph("CHILD'S IMMUNIZATION RECORD", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        immun_data = [['Vaccine', 'At birth', '1st dose', '2nd dose', '3rd dose']]
        
        # Define standard vaccines in order with their aliases
        standard_vaccines = [
            'BCG',
            'Hepa B',
            'DPT-HepB-HiB',
            'Oral Polio',
            'IPV',
            'PCV 13',
            'MMR'
        ]
        
        # Mapping for matching database names to aliases
        vaccine_aliases = {
            'BCG': ['BCG'],
            'Hepa B': ['Hepatitis B', 'Hepa B', 'HepB', 'Hep B'],
            'DPT-HepB-HiB': ['Pentavalent', 'DPT-HepB-HiB', 'DPT-HepB-HIB', 'Pentavalent Vaccine'],
            'Oral Polio': ['Oral Polio', 'OPV', 'Oral Polio Vaccine'],
            'IPV': ['IPV', 'Inactivated Polio', 'Inactivated Polio Vaccine'],
            'PCV 13': ['PCV', 'PCV 13', 'PCV13', 'Pneumococcal', 'Pneumococcal Conjugate'],
            'MMR': ['MMR', 'Measles', 'Measles, Mumps, Rubella']
        }
        
        if immunizations:
            # Group immunizations by vaccine name
            vaccine_dict = {}
            processed_vaccines = set()
            
            for immun in immunizations:
                db_vaccine_name = immun.get('vaccine_name', 'Unknown')
                
                # Find matching alias
                matched_alias = None
                for alias, patterns in vaccine_aliases.items():
                    for pattern in patterns:
                        if pattern.lower() in db_vaccine_name.lower() or db_vaccine_name.lower() in pattern.lower():
                            matched_alias = alias
                            break
                    if matched_alias:
                        break
                
                # Use matched alias or original name
                vaccine_name = matched_alias if matched_alias else db_vaccine_name
                
                if vaccine_name not in vaccine_dict:
                    vaccine_dict[vaccine_name] = {
                        'at_birth': '',
                        'first': '',
                        'second': '',
                        'third': ''
                    }
                
                # Check which dose is given
                if immun.get('at_birth_given'):
                    vaccine_dict[vaccine_name]['at_birth'] = '✓'
                if immun.get('first_dose_given'):
                    vaccine_dict[vaccine_name]['first'] = '✓'
                if immun.get('second_dose_given'):
                    vaccine_dict[vaccine_name]['second'] = '✓'
                if immun.get('third_dose_given'):
                    vaccine_dict[vaccine_name]['third'] = '✓'
                
                processed_vaccines.add(vaccine_name)
            
            # Add standard vaccines in order
            for vaccine in standard_vaccines:
                if vaccine in vaccine_dict:
                    doses = vaccine_dict[vaccine]
                    row = [
                        vaccine,
                        doses['at_birth'],
                        doses['first'],
                        doses['second'],
                        doses['third']
                    ]
                    immun_data.append(row)
                else:
                    # Add empty row for standard vaccines not found
                    immun_data.append([vaccine, '', '', '', ''])
            
            # Add any additional vaccines not in standard list
            for vaccine_name, doses in vaccine_dict.items():
                if vaccine_name not in standard_vaccines:
                    row = [
                        vaccine_name,
                        doses['at_birth'],
                        doses['first'],
                        doses['second'],
                        doses['third']
                    ]
                    immun_data.append(row)
        else:
            # Add empty rows for standard vaccines if no immunizations
            for vaccine in standard_vaccines:
                immun_data.append([vaccine, '', '', '', ''])
        
        immun_table = Table(immun_data, colWidths=[2.5*inch, 1.125*inch, 1.125*inch, 1.125*inch, 1.125*inch])
        immun_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(immun_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # === SUPPLEMENTS SECTION ===
        header_table = Table([[Paragraph("VITAMIN A SUPPLEMENTATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Filter Vitamin A supplements
        vitamin_a_supplements = [s for s in supplements if 'vitamin a' in s.get('supplement_name', '').lower()]
        
        supp_data = [['Age (mos)', 'Date Given']]
        
        if vitamin_a_supplements:
            for supp in vitamin_a_supplements:
                age_mos = supp.get('age_in_months', '')
                date_given = str(supp.get('date_given', ''))[:10] if supp.get('date_given') else ''
                supp_data.append([
                    f"{age_mos} mos" if age_mos else '',
                    date_given
                ])
        else:
            supp_data.append(['No records', ''])
        
        supp_table = Table(supp_data, colWidths=[3.5*inch, 3.5*inch])
        supp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(supp_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # === MASS DRUG ADMINISTRATION (DEWORMING) SECTION ===
        header_table = Table([[Paragraph("MASS DRUG ADMINISTRATION (DEWORMING TABLET)", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Filter deworming supplements
        deworming_supplements = [s for s in supplements if 'deworming' in s.get('supplement_name', '').lower()]
        
        deworm_data = [['Age (mos)', 'Date Given']]
        
        if deworming_supplements:
            for supp in deworming_supplements:
                age_mos = supp.get('age_in_months', '')
                date_given = str(supp.get('date_given', ''))[:10] if supp.get('date_given') else ''
                deworm_data.append([
                    f"{age_mos} mos" if age_mos else '',
                    date_given
                ])
        else:
            deworm_data.append(['No records', ''])
        
        deworm_table = Table(deworm_data, colWidths=[3.5*inch, 3.5*inch])
        deworm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(deworm_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # === GROWTH MONITORING SECTION ===
        header_table = Table([[Paragraph("GROWTH MONITORING", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Create table header
        growth_header = [['Date of Visit', 'Age', 'Weight (kg)', 'Height (cm)', 'Vital Signs (Temp, RR, PR)', 'Notes']]
        
        if growth_monitoring:
            # Limit to first 15 entries for space
            for growth in growth_monitoring[:15]:
                # Format age
                age_years = growth.get('age_years', 0) or 0
                age_months = growth.get('age_months', 0) or 0
                
                if age_years > 0:
                    age_display = f"{age_years}y {age_months}mos"
                else:
                    age_display = f"{age_months}mos"
                
                growth_data_row = [
                    str(growth.get('date_of_visit', ''))[:10] if growth.get('date_of_visit') else '',
                    age_display,
                    str(growth.get('weight_kg', '')),
                    str(growth.get('height_cm', '')),
                    f"{growth.get('temp_c', '')}, {growth.get('resp_rate', '')}, {growth.get('pulse_rate', '')}",
                    (growth.get('notes') or '')[:30]
                ]
                growth_header.append(growth_data_row)
        
        # Add empty rows to fill table (at least 5 rows total)
        while len(growth_header) < 6:
            growth_header.append(['', '', '', '', '', ''])
        
        growth_table = Table(growth_header, colWidths=[1.0*inch, 0.6*inch, 0.9*inch, 0.9*inch, 1.6*inch, 2.0*inch])
        growth_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(growth_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # === MEDICAL & SURGICAL HISTORY SECTION ===
        header_table = Table([[Paragraph("MEDICAL & SURGICAL HISTORY", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Create combined table for medical and surgical history
        history_header = [['Type', 'Condition/Procedure', 'Date']]
        
        # Add medical conditions
        if medical_conditions:
            for condition in medical_conditions[:8]:  # Limit to 8 entries
                history_header.append([
                    'Medical',
                    condition.get('medical_history_name', ''),
                    str(condition.get('created_at', ''))[:10] if condition.get('created_at') else ''
                ])
        
        # Add surgical history
        if surgical_history:
            for surgery in surgical_history[:8]:  # Limit to 8 entries
                history_header.append([
                    'Surgical',
                    surgery.get('surgical_history_name', ''),
                    str(surgery.get('date_of_surgery', ''))[:10] if surgery.get('date_of_surgery') else ''
                ])
        
        # Add empty rows to fill table (at least 3 rows total)
        while len(history_header) < 4:
            history_header.append(['', '', ''])
        
        history_table = Table(history_header, colWidths=[1.0*inch, 4.5*inch, 1.5*inch])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(history_table)

        
        elements.append(Spacer(1, 0.2*inch))
        current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
        elements.append(Paragraph(f"<b>Generated:</b> {current_date}", metadata_style))
        
        # Page footer function
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
                  canvasmaker=ChildHealthDetailCanvas)
        
        buffer.seek(0)
        return buffer
    
    def _generate_not_found_pdf(self, buffer):
        """Generate a PDF when child record is not found."""
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title='Child Health Record - Not Found',
            author='LAMBO System'
        )
        
        elements = []
        styles = get_standard_styles()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=19,
            textColor=colors.HexColor('#991B1B'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        error_style = ParagraphStyle(
            'Error',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#DC2626'),
            alignment=TA_CENTER,
            fontName='Times-Roman'
        )
        
        elements.append(Paragraph("CHILD HEALTH RECORD", title_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Child health record with ID {self.child_health_id} not found.", error_style))
        
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=ChildHealthDetailCanvas)
        
        buffer.seek(0)
        return buffer
