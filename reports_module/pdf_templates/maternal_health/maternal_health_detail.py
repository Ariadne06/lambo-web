"""
Maternal Health Detail PDF Report Generator
Generates detailed health record for a specific maternal health record
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
from bhw_module.models import Maternal


class MaternalHealthDetailCanvas(canvas.Canvas):
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


class MaternalHealthDetailPDF:
    """Generates a detailed maternal health record PDF report."""
    
    def __init__(self, maternal_health_id):
        """Initialize with maternal health ID."""
        self.maternal_health_id = int(maternal_health_id)
        
    def _get_maternal_record(self):
        """Fetch maternal health record from database."""
        return Maternal.sp_view_specific_maternal_health_record(self.maternal_health_id)
    
    def _get_obstetrical_history(self):
        """Fetch obstetrical history."""
        return Maternal.sp_view_obstetrical_history(self.maternal_health_id)
    
    def _get_medical_conditions(self):
        """Fetch medical conditions."""
        return Maternal.sp_view_specific_maternal_all_medical_condition(self.maternal_health_id)
    
    def _get_surgical_history(self):
        """Fetch surgical history."""
        return Maternal.sp_view_specific_maternal_all_surgical_history(self.maternal_health_id)
    
    def _get_immunizations(self):
        """Fetch immunization status."""
        return Maternal.sp_view_specific_maternal_immunization_status_track(self.maternal_health_id)
    
    def _get_disease_surveillance(self):
        """Fetch disease surveillance records."""
        return Maternal.sp_view_specific_maternal_all_disease_surveillance(self.maternal_health_id)
    
    def _get_laboratory_screening(self):
        """Fetch laboratory screening records."""
        return Maternal.sp_view_specific_maternal_all_laboratory_screening(self.maternal_health_id)
    
    def _get_checkup_records(self):
        """Fetch checkup records."""
        return Maternal.sp_view_specific_maternal_all_checkup_records(self.maternal_health_id)
    
    def _get_supplements(self):
        """Fetch supplement records."""
        return Maternal.sp_view_specific_maternal_all_supplements_record(self.maternal_health_id)
    
    def _get_deworming(self):
        """Fetch deworming records."""
        return Maternal.sp_view_specific_maternal_all_deworming_record(self.maternal_health_id)
    
    def _get_delivery_outcome(self):
        """Fetch delivery outcome."""
        return Maternal.sp_view_specific_maternal_delivery_outcome(self.maternal_health_id)
    
    def _get_postpartum_visits(self):
        """Fetch postpartum visit records."""
        return Maternal.sp_view_specific_maternal_all_postpartum_visit(self.maternal_health_id)
    
    def generate(self):
        """Generate the PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        
        # Fetch data
        maternal_record = self._get_maternal_record()
        
        if not maternal_record:
            self._generate_not_found_pdf(buffer)
            return buffer
        
        obstetrical_history = self._get_obstetrical_history()
        medical_conditions = self._get_medical_conditions() or []
        surgical_history = self._get_surgical_history() or []
        immunizations = self._get_immunizations()
        disease_surveillance = self._get_disease_surveillance() or []
        laboratory_screening = self._get_laboratory_screening() or []
        checkup_records = self._get_checkup_records() or []
        supplements = self._get_supplements() or []
        deworming = self._get_deworming() or []
        delivery_outcome = self._get_delivery_outcome()
        postpartum_visits = self._get_postpartum_visits() or []
        
        # Create document - Portrait orientation
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch,
            title=f'Maternal Health Record - {maternal_record.get("full_name", "Unknown")}',
            author='LAMBO System',
            subject='Maternal Health Record Detail'
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
            fontSize=9,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Bold'
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#374151'),
            fontName='Times-Roman'
        )
        
        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.white,
            fontName='Times-Bold',
            alignment=TA_CENTER
        )
        
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=8,
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
        elements.append(Paragraph("MATERNAL HEALTH RECORD", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Maternal Information section header
        header_table = Table([[Paragraph("MATERNAL INFORMATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        # Compact header info similar to child health form
        nhts_status = "NHTS" if maternal_record.get('nhts_status') else "Non-NHTS"
        
        header_info = [
            [
                f"Name: {maternal_record.get('full_name') or '_______________'}",
                f"Date of Birth: {str(maternal_record.get('dob', ''))[:10] if maternal_record.get('dob') else '_______________'}",
                f"Age: {str(maternal_record.get('age_years', '___')) if maternal_record.get('age_years') is not None else '___'}"
            ],
            [
                f"Registration Date: {str(maternal_record.get('registration_date', ''))[:10] if maternal_record.get('registration_date') else '_______________'}",
                f"Family Code: {maternal_record.get('family_code') or '_______________'}",
                f"NHTS Status: {nhts_status}"
            ],
            [
                f"Contact Number: {maternal_record.get('phone_number') or '_______________'}",
                f"Record Status: {maternal_record.get('record_status') or maternal_record.get('record_status_name') or '_______________'}",
                ''
            ],
        ]
        
        header_table_data = Table(header_info, colWidths=[2.8*inch, 2.2*inch, 2.0*inch])
        header_table_data.setStyle(TableStyle([
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
        elements.append(header_table_data)
        
        # Complete address in separate full-width row
        address_text = f"{maternal_record.get('full_address') or ''} {maternal_record.get('address_landmark') or ''}".strip()
        address_info = [[f"Complete Address: {address_text or '_______________'}"]]
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
        
        # === OBSTETRICAL HISTORY SECTION ===
        header_table = Table([[Paragraph("OBSTETRICAL HISTORY", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        if obstetrical_history:
            gravida = obstetrical_history.get('gravida', '___')
            para = obstetrical_history.get('para', '___')
            abortion = obstetrical_history.get('abortion', '___')
            lmp = str(obstetrical_history.get('last_menstrual_period', ''))[:10] if obstetrical_history.get('last_menstrual_period') else '_______________'
            edd = str(obstetrical_history.get('expected_date_of_delivery', ''))[:10] if obstetrical_history.get('expected_date_of_delivery') else '_______________'
            
            obs_info = [
                [
                    f"Gravida: {gravida}",
                    f"Para: {para}",
                    f"Abortion: {abortion}"
                ],
                [
                    f"Last Menstrual Period: {lmp}",
                    f"Expected Date of Delivery: {edd}",
                    ''
                ],
            ]
            
            obs_table = Table(obs_info, colWidths=[2.8*inch, 2.2*inch, 2.0*inch])
            obs_table.setStyle(TableStyle([
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
            elements.append(obs_table)
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
        
        med_surg_data = [['Type', 'Condition/Procedure', 'Date']]
        
        # Add medical conditions
        if medical_conditions:
            for mc in medical_conditions:
                med_surg_data.append([
                    'Medical',
                    mc.get('m_medical_history_name', '___'),
                    str(mc.get('date_added', '___'))[:10] if mc.get('date_added') else '___'
                ])
        
        # Add surgical history
        if surgical_history:
            for sh in surgical_history:
                med_surg_data.append([
                    'Surgical',
                    sh.get('m_surgical_history_name', '___'),
                    str(sh.get('date_of_surgery', '___'))[:10] if sh.get('date_of_surgery') else '___'
                ])
        
        # Add one empty row only if no data at all
        if len(med_surg_data) == 1:
            med_surg_data.append(['___', '___', '___'])
        
        med_surg_table = Table(med_surg_data, colWidths=[1.2*inch, 4.0*inch, 1.8*inch])
        med_surg_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(med_surg_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # === IMMUNIZATION STATUS (TT VACCINATION) ===
        header_table = Table([[Paragraph("IMMUNIZATION STATUS (Td, TT, or Tetap vaccination)", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        if immunizations:
            imm_header = ['1st dose', '2nd dose', '3rd dose', '4th dose', '5th dose', 'FIM Status']
            imm_dates = [
                str(immunizations.get('first_dose_date', ''))[:10] if immunizations.get('first_dose') else '___',
                str(immunizations.get('second_dose_date', ''))[:10] if immunizations.get('second_dose') else '___',
                str(immunizations.get('third_dose_date', ''))[:10] if immunizations.get('third_dose') else '___',
                str(immunizations.get('fourth_dose_date', ''))[:10] if immunizations.get('fourth_dose') else '___',
                str(immunizations.get('fifth_dose_date', ''))[:10] if immunizations.get('fifth_dose') else '___',
                immunizations.get('fim_status', '___') or '___'
            ]
            
            imm_data = [imm_header, imm_dates]
            imm_table = Table(imm_data, colWidths=[1.17*inch]*6)
            imm_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(imm_table)
        else:
            empty_imm = [
                ['1st dose', '2nd dose', '3rd dose', '4th dose', '5th dose', 'FIM Status'],
                ['___', '___', '___', '___', '___', '___']
            ]
            imm_table = Table(empty_imm, colWidths=[1.17*inch]*6)
            imm_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(imm_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # === INFECTIOUS DISEASE SURVEILLANCE ===
        header_table = Table([[Paragraph("INFECTIOUS DISEASE SURVEILLANCE", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        disease_data = [['Disease Type', 'Date Screened', 'Result']]
        
        if disease_surveillance:
            for disease in disease_surveillance:
                disease_data.append([
                    disease.get('disease_name', '___'),
                    str(disease.get('screening_date', ''))[:10] if disease.get('screening_date') else '___',
                    disease.get('result', '___') or '___'
                ])
        else:
            # Add one empty row if no data
            disease_data.append(['___', '___', '___'])
        
        disease_table = Table(disease_data, colWidths=[2.5*inch, 2.0*inch, 2.5*inch])
        disease_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(disease_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # === LABORATORY SCREENING ===
        header_table = Table([[Paragraph("LABORATORY SCREENING", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        lab_data = [['Test Type', 'Test Date', 'Result', 'Iron Given', 'Iron Qty']]
        
        if laboratory_screening:
            for lab in laboratory_screening:
                # Map technical names to display names
                test_name = lab.get('test_name', '___')
                if test_name == 'CBC_Test':
                    test_name = 'CBC/Hgb&Hct Count'
                elif test_name == 'GDM_Screen':
                    test_name = 'Gestational Diabetes Screening'
                
                lab_data.append([
                    test_name,
                    str(lab.get('test_date', ''))[:10] if lab.get('test_date') else '___',
                    lab.get('result', '___') or '___',
                    str(lab.get('iron_tablet_given_date', ''))[:10] if lab.get('iron_tablet_given_date') else '___',
                    str(lab.get('iron_tablet_quantity', '___') or '___')
                ])
        else:
            # Add one empty row if no data
            lab_data.append(['___', '___', '___', '___', '___'])
        
        lab_table = Table(lab_data, colWidths=[2.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        lab_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(lab_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Separate checkups by trimester
        first_trimester = []
        second_trimester = []
        third_trimester = []
        
        if checkup_records:
            for checkup in checkup_records:
                trimester = checkup.get('trimester_name', '')
                # Combine weight, height, and BMI
                wt = str(checkup.get('weight_kg', '___') or '___')
                ht = str(checkup.get('height_cm', '___') or '___')
                bmi = str(checkup.get('bmi', '___') or '___')
                wt_ht_bmi = f"{wt}/{ht}/{bmi}"
                
                checkup_row = [
                    str(checkup.get('date_of_checkup', ''))[:10] if checkup.get('date_of_checkup') else '___',
                    str(checkup.get('aog_weeks', '___') or '___'),
                    wt_ht_bmi,
                    checkup.get('blood_pressure', '___') or '___',
                    str(checkup.get('fetal_heart_rate', '___') or '___'),
                    checkup.get('laboratory_results', '___') or '___',
                    checkup.get('notes', '___') or '___'
                ]
                
                if 'First' in str(trimester):
                    first_trimester.append(checkup_row)
                elif 'Second' in str(trimester):
                    second_trimester.append(checkup_row)
                elif 'Third' in str(trimester):
                    third_trimester.append(checkup_row)
        
        # First Trimester Table (only show if data exists)
        if first_trimester:
            first_trim_header = Table([[Paragraph("FIRST TRIMESTER", section_header_style)]], colWidths=[7.0*inch])
            first_trim_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0)
            ]))
            elements.append(first_trim_header)
            elements.append(Spacer(1, 4))
            
            first_data = [['Date', 'AOG', 'Wt/Ht/BMI', 'BP', 'FHR', 'Lab Results', 'Notes']]
            first_data.extend(first_trimester)
            
            first_table = Table(first_data, colWidths=[0.8*inch, 0.5*inch, 1.0*inch, 0.7*inch, 0.5*inch, 1.5*inch, 2.0*inch])
            first_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(first_table)
            elements.append(Spacer(1, 0.15*inch))
        
        # Second Trimester Table (only show if data exists)
        if second_trimester:
            second_trim_header = Table([[Paragraph("SECOND TRIMESTER", section_header_style)]], colWidths=[7.0*inch])
            second_trim_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0)
            ]))
            elements.append(second_trim_header)
            elements.append(Spacer(1, 4))
            
            second_data = [['Date', 'AOG', 'Wt/Ht/BMI', 'BP', 'FHR', 'Lab Results', 'Notes']]
            second_data.extend(second_trimester)
            
            second_table = Table(second_data, colWidths=[0.8*inch, 0.5*inch, 1.0*inch, 0.7*inch, 0.5*inch, 1.5*inch, 2.0*inch])
            second_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(second_table)
            elements.append(Spacer(1, 0.15*inch))
        
        # Third Trimester Table (only show if data exists)
        if third_trimester:
            third_trim_header = Table([[Paragraph("THIRD TRIMESTER", section_header_style)]], colWidths=[7.0*inch])
            third_trim_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0)
            ]))
            elements.append(third_trim_header)
            elements.append(Spacer(1, 4))
            
            third_data = [['Date', 'AOG', 'Wt/Ht/BMI', 'BP', 'FHR', 'Lab Results', 'Notes']]
            third_data.extend(third_trimester)
            
            third_table = Table(third_data, colWidths=[0.8*inch, 0.5*inch, 1.0*inch, 0.7*inch, 0.5*inch, 1.5*inch, 2.0*inch])
            third_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(third_table)
            elements.append(Spacer(1, 0.15*inch))
        
        # === MICRONUTRIENT SUPPLEMENTATION ===
        header_table = Table([[Paragraph("MICRONUTRIENT SUPPLEMENTATION", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        supp_data = [['Supplement', 'Date Given', 'Tablets', 'Trimester']]
        
        if supplements:
            for supp in supplements:
                supp_data.append([
                    supp.get('supplement_name', '___'),
                    str(supp.get('date_given', ''))[:10] if supp.get('date_given') else '___',
                    str(supp.get('number_of_tablets', '___') or '___'),
                    supp.get('trimester_name', '___') or '___'
                ])
        else:
            # Add one empty row if no data
            supp_data.append(['___', '___', '___', '___'])
        
        supp_table = Table(supp_data, colWidths=[2.0*inch, 1.8*inch, 1.5*inch, 1.7*inch])
        supp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(supp_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # === DEWORMING ===
        header_table = Table([[Paragraph("DEWORMING TABLET", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        deworm_data = [['Deworming Medicine', 'Date Given', 'Tablets', 'Trimester']]
        
        if deworming:
            for deworm in deworming:
                deworm_data.append([
                    deworm.get('deworming_name', '___'),
                    str(deworm.get('date_given', ''))[:10] if deworm.get('date_given') else '___',
                    str(deworm.get('number_of_tablets', '___') or '___'),
                    deworm.get('trimester_name', '___') or '___'
                ])
        else:
            # Add one empty row if no data
            deworm_data.append(['___', '___', '___', '___'])
        
        deworm_table = Table(deworm_data, colWidths=[2.0*inch, 1.8*inch, 1.5*inch, 1.7*inch])
        deworm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(deworm_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # === PREGNANCY OUTCOME ===
        header_table = Table([[Paragraph("PREGNANCY OUTCOME", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        if delivery_outcome:
            delivery_info_data = [
                [
                    f"Date Terminated: {str(delivery_outcome.get('date_terminated', ''))[:10] if delivery_outcome.get('date_terminated') else '_______________'}",
                    f"Outcome: {delivery_outcome.get('outcome_type') or '_______________'}",
                    f"Type of Delivery: {delivery_outcome.get('delivery_type') or '_______________'}"
                ],
                [
                    f"Place of Delivery: {delivery_outcome.get('place_delivery_type') or '_______________'}",
                    f"Ownership: {delivery_outcome.get('ownership_type') or '_______________'}",
                    f"Birth Attendant: {delivery_outcome.get('birth_attendant') or '_______________'}"
                ],
                [
                    f"Baby Sex: {delivery_outcome.get('baby_sex') or '___'}",
                    f"Birthweight (grams): {delivery_outcome.get('baby_birthweight_in_grams') or '___'}",
                    f"Time of Delivery: {delivery_outcome.get('time_of_delivery') or '_______________'}"
                ],
            ]
            
            delivery_table = Table(delivery_info_data, colWidths=[2.8*inch, 2.2*inch, 2.0*inch])
            delivery_table.setStyle(TableStyle([
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
            elements.append(delivery_table)
        else:
            empty_delivery = [["No delivery outcome recorded yet"]]
            delivery_table = Table(empty_delivery, colWidths=[7.0*inch])
            delivery_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#6B7280')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ]))
            elements.append(delivery_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # === POSTPARTUM VISITS WITH NEWBORN ===
        header_table = Table([[Paragraph("POSTPARTUM VISITS WITH NEWBORN", section_header_style)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#991B1B')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4))
        
        ppv_data = [['Date of Visit', 'Weight (kg)', 'Height (cm)', 'Blood Pressure', 'Notes']]
        
        if postpartum_visits:
            for ppv in postpartum_visits:
                ppv_data.append([
                    str(ppv.get('date_of_visit', ''))[:10] if ppv.get('date_of_visit') else '___',
                    str(ppv.get('weight_kg', '___') or '___'),
                    str(ppv.get('height_cm', '___') or '___'),
                    ppv.get('blood_pressure', '___') or '___',
                    ppv.get('notes', '___') or '___'
                ])
        else:
            # Add one empty row if no data
            ppv_data.append(['___', '___', '___', '___', '___'])
        
        ppv_table = Table(ppv_data, colWidths=[1.2*inch, 1.0*inch, 1.0*inch, 1.3*inch, 2.5*inch])
        ppv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(ppv_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Add metadata at the bottom
        elements.append(Spacer(1, 0.1*inch))
        current_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
        elements.append(Paragraph(f"<b>Generated:</b> {current_date}", metadata_style))
        
        # Page footer function
        def add_page_footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont('Times-Roman', 8)
            canvas_obj.setFillColor(colors.HexColor('#6B7280'))
            page_num = canvas_obj.getPageNumber()
            text = f"Page {page_num}"
            canvas_obj.drawRightString(7.5*inch, 0.5*inch, text)
            canvas_obj.drawString(0.5*inch, 0.5*inch, "LAMBO System - Confidential Document")
            canvas_obj.restoreState()
        
        # Build PDF with custom canvas
        doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer,
                  canvasmaker=MaternalHealthDetailCanvas)
        
        buffer.seek(0)
        return buffer
    
    def _get_data_table_style(self):
        """Returns consistent table style for data sections"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ])
    
    def _generate_not_found_pdf(self, buffer):
        """Generate error PDF when maternal record is not found."""
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        styles = get_standard_styles()
        
        error_style = ParagraphStyle(
            'Error',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#DC2626'),
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("MATERNAL HEALTH RECORD NOT FOUND", error_style))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"Maternal Health ID: {self.maternal_health_id}", 
                                ParagraphStyle('ErrorDetail', parent=styles['Normal'], 
                                             fontSize=11, alignment=TA_CENTER, fontName='Times-Roman')))
        
        doc.build(elements, canvasmaker=MaternalHealthDetailCanvas)
        buffer.seek(0)
