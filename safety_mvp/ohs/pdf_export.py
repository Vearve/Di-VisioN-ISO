"""
PDF Export utilities for OHS application.
Retro-tech document layout: dark navy banner, teal accent, consistent table styling.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
import os

# ── Palette ────────────────────────────────────────────────────────────────────
_NAVY     = '#0d2137'
_TEAL     = '#4fb3a3'
_MIDBLUE  = '#1e5f8e'
_SECTBG   = '#1a3a5c'
_ROWALT   = '#f0f7ff'
_TEXTDARK = '#1e293b'
_GRIDLINE = '#cbd5e1'
_LTBLUE   = '#a8d4e6'
_INFOBG   = '#eef6fb'


class PDFGenerator:

    def __init__(self, title="OHS Report", company_name=""):
        self.title = title
        self.company_name = company_name
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    # ── Styles ─────────────────────────────────────────────────────────────────

    def _create_custom_styles(self):
        add = self.styles.add

        add(ParagraphStyle('CustomTitle', parent=self.styles['Heading1'],
            fontSize=18, textColor=colors.white, spaceAfter=2,
            alignment=TA_LEFT, fontName='Helvetica-Bold'))

        add(ParagraphStyle('CustomHeading', parent=self.styles['Heading2'],
            fontSize=12, textColor=colors.HexColor(_MIDBLUE),
            spaceAfter=8, spaceBefore=10, fontName='Helvetica-Bold'))

        add(ParagraphStyle('CustomSubHeading', parent=self.styles['Heading3'],
            fontSize=10, textColor=colors.HexColor(_SECTBG),
            spaceAfter=6, fontName='Helvetica-Bold'))

        add(ParagraphStyle('CustomNormal', parent=self.styles['Normal'],
            fontSize=9, textColor=colors.HexColor(_TEXTDARK), leading=13))

        add(ParagraphStyle('RetroMeta', parent=self.styles['Normal'],
            fontSize=8, textColor=colors.HexColor(_LTBLUE),
            alignment=TA_RIGHT, fontName='Helvetica'))

        add(ParagraphStyle('TalkDetail', parent=self.styles['Normal'],
            fontSize=9, textColor=colors.HexColor(_TEXTDARK),
            leading=13, spaceAfter=3))

    # ── Layout helpers ─────────────────────────────────────────────────────────

    def _base_doc(self):
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        return buf, doc

    def _header(self, story, site_name=""):
        now_str = datetime.now().strftime('%d %b %Y  %H:%M')
        meta_lines = [self.company_name or 'Di-VisioN ISO Toolkit']
        if site_name:
            meta_lines.append(f'Site: {site_name}')
        meta_lines.append(f'Generated: {now_str}')

        banner = Table(
            [[Paragraph(self.title, self.styles['CustomTitle']),
              Paragraph('<br/>'.join(meta_lines), self.styles['RetroMeta'])]],
            colWidths=[4.2*inch, 2.8*inch]
        )
        banner.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor(_NAVY)),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING',   (0, 0), (0, -1),  14),
            ('RIGHTPADDING',  (1, 0), (1, -1),  12),
            ('TOPPADDING',    (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(banner)

        accent = Table([['']], colWidths=[7*inch], rowHeights=[3])
        accent.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor(_TEAL)),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(accent)
        story.append(Spacer(1, 0.18*inch))

    def _footer(self, story):
        story.append(Spacer(1, 0.2*inch))
        foot = Table(
            [[f'Di-VisioN ISO Toolkit  ·  OHS Management  ·  {datetime.now().strftime("%Y-%m-%d %H:%M")}']],
            colWidths=[7*inch]
        )
        foot.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor(_NAVY)),
            ('TEXTCOLOR',     (0, 0), (-1, -1), colors.HexColor(_LTBLUE)),
            ('FONTNAME',      (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE',      (0, 0), (-1, -1), 7),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(foot)

    def _section_header(self, story, label, color=_SECTBG):
        story.append(Spacer(1, 0.07*inch))
        bar = Table([[label]], colWidths=[7*inch])
        bar.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor(color)),
            ('TEXTCOLOR',     (0, 0), (-1, -1), colors.white),
            ('FONTNAME',      (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(bar)
        story.append(Spacer(1, 0.05*inch))

    def _info_grid(self, story, rows):
        """4-column label/value grid: [[label, value, label, value], ...]"""
        t = Table(rows, colWidths=[1.2*inch, 2.3*inch, 1.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME',     (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE',     (0, 0), (-1, -1), 8),
            ('BACKGROUND',   (0, 0), (0, -1), colors.HexColor(_INFOBG)),
            ('BACKGROUND',   (2, 0), (2, -1), colors.HexColor(_INFOBG)),
            ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
            ('TOPPADDING',   (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.06*inch))

    def _content_row(self, story, label, value, warn=False):
        """Full-width label | value row. Only rendered when value is non-empty."""
        if not value or not str(value).strip():
            return
        bg = '#fff3cd' if warn else _INFOBG
        ct = Table([[label, str(value)]], colWidths=[1.5*inch, 5.5*inch])
        ct.setStyle(TableStyle([
            ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE',     (0, 0), (-1, -1), 8),
            ('BACKGROUND',   (0, 0), (0, -1), colors.HexColor(bg)),
            ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
            ('TOPPADDING',   (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(ct)
        story.append(Spacer(1, 0.04*inch))

    def _embed_image(self, story, field):
        """Embed an attached image/file into the PDF story.

        Uses field.open()/field.read() (storage-backend agnostic — works for
        local disk and S3). Falls back to showing the filename for non-image
        files. Skips silently if the field is empty.
        """
        if not field:
            return
        name = str(getattr(field, 'name', '') or '')
        if not name:
            return

        ext = os.path.splitext(name)[1].lower()
        is_image = ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')

        if is_image:
            try:
                field.open('rb')
                data = field.read()
                field.close()
                if data:
                    buf = BytesIO(data)
                    story.append(Spacer(1, 0.08*inch))
                    img = Image(buf, width=5*inch, height=4*inch, kind='proportional')
                    story.append(img)
                    story.append(Spacer(1, 0.06*inch))
                    return
            except Exception:
                pass

        # Non-image file, or image read failed — show filename as a row
        self._content_row(story, 'ATTACHED FILE', os.path.basename(name))

    def _flags_row(self, story, flags):
        """Render a row of True/False flags as a coloured pill list."""
        if not flags:
            return
        text = '  ·  '.join(flags)
        ft = Table([[text]], colWidths=[7*inch])
        ft.setStyle(TableStyle([
            ('FONTNAME',     (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE',     (0, 0), (-1, -1), 8),
            ('BACKGROUND',   (0, 0), (-1, -1), colors.HexColor('#1a3a5c')),
            ('TEXTCOLOR',    (0, 0), (-1, -1), colors.HexColor('#a8d4e6')),
            ('TOPPADDING',   (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
            ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ]))
        story.append(ft)
        story.append(Spacer(1, 0.06*inch))

    def _std_table(self, story, data, col_widths, header_color=_MIDBLUE):
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(header_color)),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0),  9),
            ('FONTSIZE',      (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  8),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor(_ROWALT)]),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)

    # ── Reports ────────────────────────────────────────────────────────────────

    def generate_incidents_report(self, incidents, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Incidents: {incidents.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for inc in incidents[:100]:
            date_str = inc.date_reported.strftime('%d %b %Y') if inc.date_reported else 'N/A'
            event_str = inc.event_datetime.strftime('%d %b %Y  %H:%M') if inc.event_datetime else 'N/A'
            self._section_header(story, f'  {date_str}  ·  {inc.title or "Incident"}')

            self._info_grid(story, [
                ['Date Reported', date_str,
                 'Event Date/Time', event_str],
                ['Site', inc.site.name if inc.site else 'N/A',
                 'Location', inc.location or '-'],
                ['Severity', inc.severity or 'N/A',
                 'Treatment Level', (inc.get_treatment_level_display() if hasattr(inc, 'get_treatment_level_display') else inc.treatment_level) or 'N/A'],
                ['Affected Person', inc.affected_person_name or '-',
                 'Employment Type', (inc.get_employment_type_display() if hasattr(inc, 'get_employment_type_display') else inc.employment_type) or '-'],
                ['Department', inc.department or '-',
                 'Lost Time (days)', str(inc.lost_time_days or 0)],
                ['Reported By', inc.reported_by.get_full_name() or inc.reported_by.username if inc.reported_by else '-',
                 'Reportable', 'YES — Notify Regulator' if inc.reportable_to_regulator else 'No'],
            ])

            self._content_row(story, 'DESCRIPTION', inc.description)
            self._content_row(story, 'CREW / WITNESSES', ', '.join(filter(None, [inc.crew, inc.witnesses])) or None)
            self._content_row(story, 'IMMEDIATE ACTION', inc.immediate_action_taken)
            self._content_row(story, 'INJURY / ILLNESS', ', '.join(filter(None, [inc.injury_type, inc.body_part_affected])) or None)
            self._content_row(story, 'INCIDENT CATEGORY', inc.incident_category)
            self._content_row(story, 'ROOT CAUSE', inc.root_cause)
            self._content_row(story, 'CONTRIBUTING FACTORS', inc.contributing_factors)
            self._content_row(story, 'CORRECTIVE ACTIONS', inc.corrective_actions)
            self._content_row(story, 'LESSONS LEARNED', inc.lessons_learned)
            self._content_row(story, 'CLOSEOUT VERIFICATION', inc.closeout_verification)

            inv_lead = inc.investigation_lead
            inv_lead_str = (inv_lead.get_full_name() or inv_lead.username) if inv_lead else '-'
            action_own = inc.action_owner
            action_own_str = (action_own.get_full_name() or action_own.username) if action_own else '-'
            comp_date = inc.investigation_completion_date.strftime('%d %b %Y') if inc.investigation_completion_date else '-'
            reg_date = inc.regulator_notification_date.strftime('%d %b %Y') if inc.regulator_notification_date else '-'
            self._content_row(story, 'INVESTIGATION', f'Lead: {inv_lead_str}  |  Action Owner: {action_own_str}  |  Completion: {comp_date}  |  Regulator notified: {reg_date}')

            self._embed_image(story, inc.image)
            self._embed_image(story, inc.incident_file)
            story.append(Spacer(1, 0.25*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_attendance_report(self, attendance_records, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        total_hours = sum(r.get_man_hours() for r in attendance_records)
        story.append(Paragraph(f'Attendance Records: {attendance_records.count()}  ·  Total Man-Hours: {round(total_hours, 2)}',
                               self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Date', 'Employee', 'Start', 'End', 'Break (min)', 'Man-Hours']]
        for r in attendance_records[:100]:
            data.append([
                r.date.strftime('%d/%m/%Y'),
                r.employee.name[:22],
                r.start_time.strftime('%H:%M'),
                r.end_time.strftime('%H:%M'),
                str(r.break_duration_minutes),
                f'{r.get_man_hours():.1f}h',
            ])
        self._std_table(story, data, [1*inch, 1.7*inch, 0.8*inch, 0.8*inch, 1.1*inch, 0.85*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_employees_report(self, employees, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Employees: {employees.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Name', 'Position', 'Department', 'Scope', 'Contact', 'Emergency Contact']]
        for emp in employees[:100]:
            data.append([
                emp.name[:22],
                emp.position[:16],
                emp.department[:16],
                (emp.get_scope_display() if hasattr(emp, 'get_scope_display') else emp.scope)[:10],
                emp.contact_number[:16],
                emp.emergency_contact[:22],
            ])
        self._std_table(story, data, [1.2*inch, 1.1*inch, 1.1*inch, 0.9*inch, 1.2*inch, 1.2*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_jsa_report(self, jsas, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total JSAs: {jsas.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for jsa in jsas[:100]:
            date_str = jsa.assessment_date.strftime('%d %b %Y') if jsa.assessment_date else 'N/A'
            self._section_header(story, f'  {jsa.jsa_number or "JSA"}  ·  {jsa.job_task}')

            self._info_grid(story, [
                ['JSA Number', jsa.jsa_number or '-',
                 'Work Order', jsa.work_order_number or '-'],
                ['Date', date_str,
                 'Site', jsa.site.name if jsa.site else 'N/A'],
                ['Location', jsa.location or '-',
                 'Plant / Area', jsa.plant_area or '-'],
                ['Senior Supervisor', jsa.senior_supervisor_name or '-',
                 'Work Group Supervisor', jsa.work_group_supervisor_name or '-'],
                ['Doc Reference', f'{jsa.document_reference}  Rev {jsa.revision_number}',
                 'Performed By', (jsa.performed_by.get_full_name() or jsa.performed_by.username) if jsa.performed_by else '-'],
            ])

            # Permits
            permit_map = [
                ('permit_to_work', 'Permit to Work'), ('excavation_permit', 'Excavation'),
                ('hot_work_permit', 'Hot Work'), ('hv_electrical_isolation_permit', 'HV Electrical Isolation'),
                ('hv_vicinity_permit', 'HV Vicinity'), ('radiation_work_permit', 'Radiation'),
                ('working_at_height_permit', 'Working at Height'), ('chemical_pump_pipe_permit', 'Chemical/Pump/Pipe'),
                ('confined_space_permit', 'Confined Space'), ('other_permit', jsa.other_permit_description or 'Other'),
            ]
            permits = [label for attr, label in permit_map if getattr(jsa, attr, False)]
            if permits:
                self._content_row(story, 'PERMITS REQUIRED', '  ·  '.join(permits))

            # FPCs
            fpc_map = [
                ('fpc_competent_capable_controlled', 'Competent & Capable'),
                ('fpc_identify_control_hazards', 'Identify & Control Hazards'),
                ('fpc_safe_lifting_operations', 'Safe Lifting'),
                ('fpc_drive_safely', 'Drive Safely'),
                ('fpc_energy_isolation', 'Energy Isolation'),
                ('fpc_confined_space_entry', 'Confined Space Entry'),
                ('fpc_work_at_heights', 'Work at Heights'),
                ('fpc_surface_underground', 'Surface/Underground'),
                ('fpc_equipment_safeguards', 'Equipment Safeguards'),
                ('fpc_chemicals_hazardous_substances', 'Chemicals/Hazardous Substances'),
            ]
            fpcs = [label for attr, label in fpc_map if getattr(jsa, attr, False)]
            if fpcs:
                self._content_row(story, 'FPC COMMITMENTS', '  ·  '.join(fpcs))

            # Potential hazards
            haz_map = [
                ('hazard_electrical', 'Electrical'), ('hazard_mechanical', 'Mechanical'),
                ('hazard_chemical', 'Chemical'), ('hazard_dust_fume', 'Dust/Fume'),
                ('hazard_stored_energy', 'Stored Energy'), ('hazard_live_equipment', 'Live Equipment'),
                ('hazard_manual_handling', 'Manual Handling'), ('hazard_radiation', 'Radiation'),
                ('hazard_noise', 'Noise'), ('hazard_fire_explosives', 'Fire/Explosives'),
                ('hazard_working_at_height', 'Working at Height'), ('hazard_rock_falls', 'Rock Falls'),
                ('hazard_flora_fauna', 'Flora/Fauna'), ('hazard_falling_equipment', 'Falling Equipment'),
            ]
            haz = [label for attr, label in haz_map if getattr(jsa, attr, False)]
            if haz:
                self._content_row(story, 'POTENTIAL HAZARDS', '  ·  '.join(haz))

            self._content_row(story, 'ADDITIONAL PPE', jsa.additional_ppe_requirements)
            self._content_row(story, 'SPECIAL TOOLS / EQUIPMENT', jsa.special_tools_equipment)
            self._content_row(story, 'HAZARDOUS MATERIALS', jsa.hazardous_materials)
            self._content_row(story, 'FIRE / EMERGENCY EQUIPMENT', jsa.fire_emergency_equipment)
            self._content_row(story, 'REQUIRED COMPETENCY', jsa.required_competency)
            self._content_row(story, 'ADDITIONAL CONTROLS', jsa.additional_controls_required)
            self._content_row(story, 'HAZARDS (GENERAL)', jsa.hazards)
            self._content_row(story, 'CONTROLS (GENERAL)', jsa.controls)

            # JSA Steps table
            steps = list(jsa.steps.order_by('step_number'))
            if steps:
                self._section_header(story, '  JOB SAFETY ANALYSIS STEPS', color=_MIDBLUE)
                step_data = [['#', 'Job Step', 'Hazard', 'Current Controls', 'Risk\nBefore', 'Additional Actions', 'Risk\nAfter']]
                for s in steps:
                    step_data.append([
                        str(s.step_number),
                        s.job_step or '-',
                        s.job_step_hazard or '-',
                        s.current_controls or '-',
                        s.residual_risk_before or '-',
                        s.required_additional_actions or '-',
                        s.residual_risk_after or '-',
                    ])
                self._std_table(story, step_data, [0.3*inch, 1.2*inch, 1.1*inch, 1.2*inch, 0.55*inch, 1.3*inch, 0.55*inch])
                story.append(Spacer(1, 0.06*inch))

            # Team acknowledgements
            acks = jsa.team_member_acknowledgements or []
            if acks:
                self._section_header(story, '  TEAM ACKNOWLEDGEMENTS', color=_MIDBLUE)
                ack_data = [['Name', 'ID No.', 'Date']]
                for a in acks:
                    ack_data.append([a.get('name', '-'), a.get('id_no', '-'), a.get('date', '-')])
                self._std_table(story, ack_data, [2.5*inch, 2*inch, 2.5*inch])

            self._embed_image(story, jsa.jsa_file)
            story.append(Spacer(1, 0.3*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_fra_report(self, fras, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total FRAs: {fras.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for fra in fras[:100]:
            date_str = fra.date_assessed.strftime('%d %b %Y') if fra.date_assessed else 'N/A'
            self._section_header(story, f'  {date_str}  ·  {fra.activity}')

            self._info_grid(story, [
                ['Activity', fra.activity,
                 'Location', fra.location or '-'],
                ['Hazard Category', fra.hazard_category or '-',
                 'Risk Level', fra.risk_level or '-'],
                ['Initial Risk Score', f'L{fra.likelihood or "-"} × S{fra.severity_score or "-"} = {fra.initial_risk_score or "-"}',
                 'Residual Risk Score', f'L{fra.residual_likelihood or "-"} × S{fra.residual_severity or "-"} = {fra.residual_risk_score or "-"}'],
                ['Acceptable', 'Yes' if fra.acceptable else 'No',
                 'Review Frequency', fra.review_frequency or '-'],
                ['Assessed By', (fra.assessed_by.get_full_name() or fra.assessed_by.username) if fra.assessed_by else '-',
                 'Approver', (fra.approver.get_full_name() or fra.approver.username) if fra.approver else '-'],
            ])

            self._content_row(story, 'RISK IDENTIFIED', fra.risk_identified)
            self._content_row(story, 'PERSONS AT RISK', fra.persons_at_risk)
            self._content_row(story, 'EXISTING CONTROLS', fra.existing_controls)
            self._content_row(story, 'CONTROL MEASURES', fra.control_measures)
            self._content_row(story, 'ADDITIONAL CONTROLS', fra.additional_controls)
            self._embed_image(story, fra.fra_file)
            story.append(Spacer(1, 0.25*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_flra_report(self, flras, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total FLRAs: {flras.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for flra in flras[:100]:
            date_str = flra.date.strftime('%d %b %Y') if flra.date else 'N/A'
            self._section_header(story, f'  {date_str}  ·  {flra.task_description[:80] if flra.task_description else "FLRA"}')

            assessed_by_str = '-'
            if flra.assessed_by:
                assessed_by_str = flra.assessed_by.get_full_name() or flra.assessed_by.username

            self._info_grid(story, [
                ['Date', date_str,
                 'Site', flra.site.name if flra.site else 'N/A'],
                ['Location', flra.location or '-',
                 'Shift', flra.shift or 'N/A'],
                ['Weather Conditions', flra.weather_conditions or '-',
                 'Assessed By', assessed_by_str],
                ['Supervisor', flra.supervisor_signature or '-',
                 'Escalation Required', 'YES' if flra.escalation_required else 'No'],
            ])

            flags = []
            if flra.simultaneous_operations:    flags.append('Simultaneous Operations')
            if flra.energy_isolation_confirmed: flags.append('Energy Isolation Confirmed')
            if flra.stop_work_authority_used:   flags.append('Stop Work Authority Used')
            if flra.escalation_required:        flags.append('⚠ ESCALATION REQUIRED')
            self._flags_row(story, flags)

            self._content_row(story, 'TASK DESCRIPTION', flra.task_description)
            self._content_row(story, 'IDENTIFIED HAZARDS', flra.identified_hazards)
            self._content_row(story, 'CONTROL MEASURES', flra.control_measures)
            self._content_row(story, 'ADDITIONAL CONTROLS', flra.additional_controls_added)
            self._content_row(story, 'DYNAMIC CHANGES', flra.dynamic_changes_noticed)
            self._content_row(story, 'WORKER SIGNATURES', flra.worker_signatures)

            # Employees on task
            emp_names = list(flra.selected_employees.values_list('name', flat=True))
            all_people = emp_names[:]
            if flra.crew:
                all_people.append(f'Crew/External: {flra.crew}')
            self._content_row(story, 'EMPLOYEES ON TASK', ', '.join(all_people) if all_people else '-')

            self._embed_image(story, flra.flra_file)
            story.append(Spacer(1, 0.25*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_observations_report(self, observations, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Observations: {observations.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for obs in observations[:100]:
            date_str = obs.date.strftime('%d %b %Y') if obs.date else 'N/A'
            obs_type = 'Planned Task Observation' if obs.observation_type == 'PTO' else 'Critical Control Verification'
            self._section_header(story, f'  {date_str}  ·  {obs_type}  ·  {obs.task}')

            observed_by_str = (obs.observed_by.get_full_name() or obs.observed_by.username) if obs.observed_by else '-'
            self._info_grid(story, [
                ['Date', date_str,
                 'Type', obs_type],
                ['Site', obs.site.name if obs.site else 'N/A',
                 'Observed By', observed_by_str],
                ['Follow-up Required', 'YES' if obs.follow_up_required else 'No',
                 'Task', obs.task],
            ])

            self._content_row(story, 'CONTROLS VERIFIED', obs.controls_verified)
            self._content_row(story, 'FINDINGS', obs.findings)
            self._embed_image(story, obs.file)
            story.append(Spacer(1, 0.25*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_toolbox_talks_report(self, toolbox_talks, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)

        total = toolbox_talks.count()
        story.append(Paragraph(f'Total Toolbox Talks: {total}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for talk in toolbox_talks[:100]:
            date_str = talk.talk_date.strftime('%d %b %Y') if talk.talk_date else 'N/A'
            title_text = talk.title or 'Untitled Talk'

            # ── Talk banner ──────────────────────────────────────────────────
            self._section_header(story, f'  {date_str}  ·  {title_text}')

            # ── Info grid ────────────────────────────────────────────────────
            info_data = [
                ['Date', date_str,
                 'Site', talk.site.name if talk.site else 'N/A'],
                ['Facilitator', talk.facilitator_name or '-',
                 'Recorded Attendance', str(talk.attendance_count or 0)],
            ]
            info_t = Table(info_data, colWidths=[1.2*inch, 2.3*inch, 1.5*inch, 2*inch])
            info_t.setStyle(TableStyle([
                ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME',     (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, -1), 8),
                ('BACKGROUND',   (0, 0), (0, -1), colors.HexColor(_INFOBG)),
                ('BACKGROUND',   (2, 0), (2, -1), colors.HexColor(_INFOBG)),
                ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
                ('TOPPADDING',   (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
                ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(info_t)
            story.append(Spacer(1, 0.07*inch))

            # ── Content fields ───────────────────────────────────────────────
            content_fields = [
                ('TOPIC DETAILS',     getattr(talk, 'topic_details', None)),
                ('HAZARDS DISCUSSED', getattr(talk, 'hazards_discussed', None)),
                ('CONTROLS AGREED',   getattr(talk, 'controls_agreed', None)),
                ('ACTION ITEMS',      getattr(talk, 'action_items', None)),
            ]
            for label, value in content_fields:
                if value and str(value).strip():
                    ct = Table([[label, str(value)]], colWidths=[1.5*inch, 5.5*inch])
                    ct.setStyle(TableStyle([
                        ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE',     (0, 0), (-1, -1), 8),
                        ('BACKGROUND',   (0, 0), (0, -1), colors.HexColor(_INFOBG)),
                        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
                        ('TOPPADDING',   (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
                        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(ct)
                    story.append(Spacer(1, 0.04*inch))

            # ── Follow-up ────────────────────────────────────────────────────
            if getattr(talk, 'follow_up_required', False):
                due = getattr(talk, 'follow_up_due_date', None) or '-'
                owner = getattr(talk, 'follow_up_owner', None) or '-'
                ft = Table(
                    [['FOLLOW-UP REQUIRED', f'Owner: {owner}  |  Due: {due}']],
                    colWidths=[1.5*inch, 5.5*inch]
                )
                ft.setStyle(TableStyle([
                    ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE',     (0, 0), (-1, -1), 8),
                    ('BACKGROUND',   (0, 0), (0, -1), colors.HexColor('#fff3cd')),
                    ('BACKGROUND',   (1, 0), (1, -1), colors.HexColor('#fffbf0')),
                    ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
                    ('TOPPADDING',   (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
                ]))
                story.append(ft)
                story.append(Spacer(1, 0.04*inch))

            # ── Attendees ────────────────────────────────────────────────────
            self._section_header(story, '  ATTENDEES', color='#2c5f8e')

            attendees = []
            for emp in talk.attendee_employees.all():
                role = (getattr(emp, 'position', '') or
                        getattr(emp, 'job_title', '') or 'Employee')
                attendees.append((emp.name, role))

            extras_raw = getattr(talk, 'attendees', '') or ''
            for name in [n.strip() for n in extras_raw.replace('\n', ',').split(',') if n.strip()]:
                attendees.append((name, 'Additional Attendee'))

            if attendees:
                att_data = [['#', 'Name', 'Role / Category']]
                for idx, (name, role) in enumerate(attendees, 1):
                    att_data.append([str(idx), name, role])
                self._std_table(story, att_data, [0.4*inch, 3.6*inch, 3*inch])
            else:
                story.append(Paragraph('No attendees recorded for this talk.',
                                       self.styles['CustomNormal']))

            story.append(Spacer(1, 0.3*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_certifications_report(self, certifications, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Certifications: {certifications.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Employee', 'Certification', 'Issuer', 'Issue Date', 'Expiry Date']]
        for cert in certifications[:100]:
            data.append([
                (cert.employee.username if getattr(cert, 'employee', None) else 'N/A')[:22],
                cert.name[:26],
                cert.issuing_body[:20],
                cert.issue_date.strftime('%d/%m/%Y') if cert.issue_date else 'N/A',
                cert.expiry_date.strftime('%d/%m/%Y') if cert.expiry_date else 'N/A',
            ])
        self._std_table(story, data, [1.4*inch, 1.8*inch, 1.4*inch, 1*inch, 1*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_documents_report(self, documents, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Documents: {documents.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Name', 'Type', 'Site', 'Uploaded', 'Uploader']]
        for d in documents[:100]:
            data.append([
                d.name[:26],
                d.doc_type,
                d.site.name if d.site else 'N/A',
                d.upload_date.strftime('%d/%m/%Y') if d.upload_date else 'N/A',
                (d.uploaded_by.username if getattr(d, 'uploaded_by', None) else 'N/A')[:18],
            ])
        self._std_table(story, data, [1.9*inch, 1*inch, 1.4*inch, 1*inch, 1.2*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_training_report(self, trainings, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Training Items: {trainings.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Title', 'Site', 'Training Date', 'Due Date', 'Status']]
        for item in trainings[:100]:
            data.append([
                item.title[:28],
                item.site.name if item.site else 'N/A',
                item.training_date.strftime('%d/%m/%Y') if item.training_date else 'N/A',
                item.due_date.strftime('%d/%m/%Y') if item.due_date else 'N/A',
                item.status,
            ])
        self._std_table(story, data, [2*inch, 1.3*inch, 1.1*inch, 1*inch, 0.9*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_objectives_report(self, objectives, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Objectives: {objectives.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Objective', 'Site', 'Status', 'Progress', 'Due Date']]
        for obj in objectives[:100]:
            data.append([
                obj.name[:28],
                obj.site.name if obj.site else 'N/A',
                obj.status,
                f'{obj.progress_percent()}%',
                obj.due_date.strftime('%d/%m/%Y') if obj.due_date else 'N/A',
            ])
        self._std_table(story, data, [2*inch, 1.3*inch, 1*inch, 0.9*inch, 1*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_materials_report(self, materials, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Total Materials: {materials.count()}', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Name', 'Site', 'Quantity', 'Date Received', 'SDS Available']]
        for m in materials[:100]:
            data.append([
                m.name[:26],
                m.site.name if m.site else 'N/A',
                f'{m.quantity} {m.unit}',
                m.date_received.strftime('%d/%m/%Y') if m.date_received else 'N/A',
                'Yes' if m.sds_available else 'No',
            ])
        self._std_table(story, data, [1.9*inch, 1.3*inch, 1.3*inch, 1.1*inch, 1*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_site_health_report(self, reports, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Monthly Site Health & Safety Summary', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        data = [['Month', 'Year', 'Site / Project', 'Incidents', 'Near Misses',
                 'Observations', 'Inspections', 'Training Hrs', 'Man-Hours']]
        for report in reports[:100]:
            month_name = dict(report._meta.get_field('report_month').choices).get(
                report.report_month, str(report.report_month))
            data.append([
                month_name,
                str(report.report_year),
                report.site_project.name if report.site_project else 'Unknown',
                str(report.incident_count),
                str(report.near_miss_count),
                str(report.observation_count),
                str(report.inspection_count),
                f'{float(report.training_hours):.1f}',
                f'{float(report.man_hours):.1f}',
            ])
        self._std_table(story, data,
                        [0.8*inch, 0.55*inch, 1.3*inch, 0.75*inch, 0.85*inch,
                         0.85*inch, 0.85*inch, 0.8*inch, 0.8*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    # ── New-style detailed reports ─────────────────────────────────────────────

    def generate_checklists_report(self, checklists, site_name="", step_map=None):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        story.append(Paragraph(f'Total records: {checklists.count()}', self.styles['CustomNormal']))
        story.append(Spacer(1, 0.15*inch))

        for cl in checklists[:50]:
            story.append(Paragraph(
                f'{cl.get_checklist_type_display()} — {cl.date_completed}'
                f' | Site: {cl.site or "N/A"} | Equipment: {cl.equipment_id or "N/A"}',
                self.styles['CustomSubHeading']
            ))
            info_data = [
                ['Operator', cl.operator_name or '-', 'Supervisor', cl.supervisor_name or '-'],
                ['Inspection Area', cl.inspection_area or '-', 'Operational Status',
                 (cl.get_operational_status_display()
                  if hasattr(cl, 'get_operational_status_display')
                  else (cl.operational_status or '-'))],
            ]
            info_t = Table(info_data, colWidths=[1.3*inch, 2*inch, 1.3*inch, 2*inch])
            info_t.setStyle(TableStyle([
                ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME',     (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTSIZE',     (0, 0), (-1, -1), 8),
                ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor(_GRIDLINE)),
                ('BACKGROUND',   (0, 0), (0, -1), colors.HexColor(_INFOBG)),
                ('BACKGROUND',   (2, 0), (2, -1), colors.HexColor(_INFOBG)),
                ('TOPPADDING',   (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
            ]))
            story.append(info_t)
            story.append(Spacer(1, 0.07*inch))

            basic = [
                ('PPE Inspection',          cl.ppe_inspection),
                ('Fire Safety Check',        cl.fire_safety_check),
                ('Equipment Condition',      cl.equipment_condition),
                ('Emergency Exits Clear',    cl.emergency_exits_clear),
                ('Safety Signage Visible',   cl.safety_signage_visible),
                ('First Aid Kit Stocked',    cl.first_aid_kit_stocked),
                ('Housekeeping Checked',     cl.housekeeping_checked),
            ]
            basic_data = [['Inspection Item', 'Result']]
            for label, val in basic:
                basic_data.append([label, 'Pass' if val else 'Fail'])
            self._std_table(story, basic_data, [4.5*inch, 1*inch])
            story.append(Spacer(1, 0.07*inch))

            step_labels = (step_map or {}).get(cl.checklist_type, [])
            step_rows = [['#', 'Inspection Item / Question', 'Result', 'Comments']]
            fail_row_indices = []
            for i in range(1, 48):
                sk = f'{i:02d}'
                compliant = getattr(cl, f'step_{sk}_compliant', None)
                if compliant is None:
                    continue
                label = step_labels[i - 1] if i - 1 < len(step_labels) else f'Step {i}'
                comment = getattr(cl, f'step_{sk}_comments', '') or ''
                result_text = 'Pass' if compliant else 'FAIL'
                if not compliant:
                    fail_row_indices.append(len(step_rows))
                step_rows.append([
                    str(i), label, result_text,
                    comment[:80] + ('…' if len(comment) > 80 else ''),
                ])

            if len(step_rows) > 1:
                tbl = Table(step_rows, colWidths=[0.35*inch, 3.9*inch, 0.65*inch, 1.8*inch])
                style_cmds = [
                    ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(_MIDBLUE)),
                    ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
                    ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                    ('FONTSIZE',      (0, 0), (-1, -1), 8),
                    ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor(_GRIDLINE)),
                    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor(_ROWALT)]),
                    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING',    (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 5),
                    ('FONTNAME',      (2, 1), (2, -1),  'Helvetica-Bold'),
                    ('ALIGN',         (0, 0), (0, -1),  'CENTER'),
                    ('ALIGN',         (2, 0), (2, -1),  'CENTER'),
                ]
                for fi in fail_row_indices:
                    style_cmds += [
                        ('BACKGROUND', (2, fi), (2, fi), colors.HexColor('#fee2e2')),
                        ('TEXTCOLOR',  (2, fi), (2, fi), colors.HexColor('#b91c1c')),
                    ]
                tbl.setStyle(TableStyle(style_cmds))
                story.append(tbl)
                story.append(Spacer(1, 0.07*inch))

            if cl.findings or cl.actions_required:
                story.append(Paragraph(f'Findings: {cl.findings or "-"}', self.styles['CustomNormal']))
                story.append(Paragraph(f'Actions Required: {cl.actions_required or "-"}', self.styles['CustomNormal']))
            story.append(Spacer(1, 0.2*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_capa_report(self, actions, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        data = [['Title', 'Priority', 'Status', 'Due Date', 'Site', 'Root Cause']]
        for a in actions[:100]:
            data.append([a.title[:35], a.get_priority_display(), a.get_status_display(),
                         str(a.due_date or '-'), str(a.site or '-'), (a.root_cause or '-')[:40]])
        self._std_table(story, data, [1.8*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1*inch, 1.3*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_contractors_report(self, contractors, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        data = [['Name', 'Company', 'Site', 'Onboarded', 'Onboarding Date']]
        for c in contractors[:100]:
            data.append([c.name, c.company, str(c.site or '-'),
                         'Yes' if c.onboarded else 'No', str(c.onboarding_date or '-')])
        self._std_table(story, data, [1.5*inch, 1.5*inch, 1.2*inch, 0.9*inch, 1.2*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_ccv_report(self, ccvs, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        data = [['Type', 'Assessor', 'Date/Time', 'Location', 'Dept', 'Steps OK']]
        for c in ccvs[:100]:
            answered = [getattr(c, f'step_{i:02d}_compliant') for i in range(1, 30)
                        if getattr(c, f'step_{i:02d}_compliant', None) is not None]
            ok = sum(1 for v in answered if v)
            total = len(answered)
            data.append([
                c.get_ccv_type_display(), c.assessor_name or '-',
                str(c.assessment_datetime)[:16] if c.assessment_datetime else '-',
                c.location or '-', c.department or '-',
                f'{ok}/{total}' if total else '-',
            ])
        self._std_table(story, data, [1.5*inch, 1.2*inch, 1.1*inch, 1.1*inch, 1*inch, 0.7*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_pto_chemicals_report(self, ptos, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        data = [['PTO Type', 'Site', 'Date', 'Shift', 'Location']]
        for p in ptos[:100]:
            data.append([
                (p.get_pto_type_display() if hasattr(p, 'get_pto_type_display')
                 else getattr(p, 'pto_type', '')),
                str(p.site or '-'),
                str(getattr(p, 'date', None) or str(getattr(p, 'created_at', ''))[:10]),
                str(getattr(p, 'shift_mining', None) or getattr(p, 'shift_other', None) or '-'),
                str(getattr(p, 'location', None) or '-'),
            ])
        self._std_table(story, data, [2.2*inch, 1.2*inch, 1*inch, 1*inch, 1.3*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_medical_profiles_report(self, profiles, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        data = [['Employee', 'Fitness Status', 'Surveillance', 'Next Medical Due', 'Restrictions']]
        for p in profiles[:100]:
            data.append([p.employee.name, p.get_fitness_status_display(),
                         'Yes' if p.surveillance_required else 'No',
                         str(p.next_medical_due or '-'), (p.restrictions or '-')[:40]])
        self._std_table(story, data, [1.5*inch, 1.3*inch, 0.9*inch, 1.1*inch, 1.9*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_medical_assessments_report(self, assessments, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name=site_name)
        data = [['Employee', 'Exam Type', 'Assessment Date', 'Valid Until', 'Outcome', 'Provider']]
        for a in assessments[:100]:
            data.append([
                a.profile.employee.name, a.exam_type[:25],
                str(a.assessment_date), str(a.valid_until or '-'),
                a.get_outcome_display(), str(getattr(a, 'provider', None) or '-')[:20],
            ])
        self._std_table(story, data, [1.3*inch, 1.4*inch, 1.1*inch, 1*inch, 1.1*inch, 0.8*inch])
        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    # ── EMS Reports ────────────────────────────────────────────────────────────

    def generate_ems_aspects_report(self, aspects, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Environmental Aspects Register — {aspects.count()} entries', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for a in aspects[:200]:
            created = a.created_at.strftime('%d %b %Y') if a.created_at else 'N/A'
            review = a.review_date.strftime('%d %b %Y') if a.review_date else '-'
            self._section_header(story, f'  {a.activity}  ·  {a.aspect}')
            self._info_grid(story, [
                ['Activity', a.activity, 'Aspect', a.aspect],
                ['Potential Impact', a.potential_impact,
                 'Impact Type', a.get_impact_type_display() if hasattr(a, 'get_impact_type_display') else a.impact_type],
                ['Operating Condition', a.get_operating_condition_display() if hasattr(a, 'get_operating_condition_display') else a.operating_condition,
                 'Significance', a.get_significance_display() if hasattr(a, 'get_significance_display') else a.significance],
                ['Monitoring Required', 'Yes' if a.monitoring_required else 'No',
                 'Review Date', review],
                ['Site', a.site.name if a.site else 'All Sites',
                 'Recorded', created],
            ])
            self._content_row(story, 'CONTROL MEASURE', a.control_measure)
            self._content_row(story, 'LEGAL REQUIREMENT', a.legal_requirement)
            self._content_row(story, 'NOTES', a.notes)
            story.append(Spacer(1, 0.2*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_ems_waste_report(self, logs, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        total_kg = sum(float(l.quantity_kg or 0) for l in logs)
        story.append(Paragraph(
            f'Waste Management Log — {logs.count()} records  ·  Total: {total_kg:,.1f} kg',
            self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        data = [['Date', 'Site', 'Waste Type', 'Description', 'Qty (kg)', 'Disposal Method', 'Contractor', 'Manifest']]
        for l in logs[:200]:
            data.append([
                l.log_date.strftime('%d/%m/%Y') if l.log_date else '-',
                l.site.name if l.site else 'N/A',
                l.get_waste_type_display() if hasattr(l, 'get_waste_type_display') else l.waste_type,
                l.description[:28],
                f'{float(l.quantity_kg):,.1f}',
                l.get_disposal_method_display() if hasattr(l, 'get_disposal_method_display') else l.disposal_method,
                (l.disposal_contractor or '-')[:20],
                (l.manifest_number or '-')[:14],
            ])
        self._std_table(story, data,
                        [0.75*inch, 0.8*inch, 1*inch, 1.1*inch, 0.65*inch, 1.05*inch, 0.85*inch, 0.75*inch])

        # Notes section — only records that have notes
        notes_records = [l for l in logs[:200] if l.notes and l.notes.strip()]
        if notes_records:
            self._section_header(story, '  NOTES', color=_MIDBLUE)
            for l in notes_records:
                self._content_row(story, l.log_date.strftime('%d/%m/%Y') if l.log_date else '-', l.notes)

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_ems_spills_report(self, spills, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Spill & Release Incidents — {spills.count()} records', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for s in spills[:100]:
            date_str = s.incident_date.strftime('%d %b %Y  %H:%M') if s.incident_date else 'N/A'
            severity_disp = s.get_severity_display() if hasattr(s, 'get_severity_display') else s.severity
            self._section_header(story, f'  {date_str}  ·  {severity_disp}')

            reported_by_str = (s.reported_by.get_full_name() or s.reported_by.username) if s.reported_by else '-'
            qty_str = f'{float(s.quantity_litres):,.1f} L' if s.quantity_litres else '-'
            cleanup_date = s.cleanup_date.strftime('%d %b %Y') if s.cleanup_date else '-'

            self._info_grid(story, [
                ['Date & Time', date_str,
                 'Substance', s.get_substance_display() if hasattr(s, 'get_substance_display') else s.substance],
                ['Severity', severity_disp,
                 'Quantity', qty_str],
                ['Site', s.site.name if s.site else 'N/A',
                 'Reported By', reported_by_str],
                ['Cleanup Completed', 'Yes' if s.cleanup_completed else 'No',
                 'Cleanup Date', cleanup_date],
                ['Regulatory Notification Required', 'YES' if s.regulatory_notification_required else 'No',
                 'Notification Sent', 'Yes' if s.regulatory_notification_sent else 'No'],
            ])

            flags = []
            if s.regulatory_notification_required and not s.regulatory_notification_sent:
                flags.append('⚠ REGULATORY NOTIFICATION PENDING')
            if not s.cleanup_completed:
                flags.append('⚠ CLEANUP INCOMPLETE')
            self._flags_row(story, flags)

            self._content_row(story, 'LOCATION', s.location_description)
            self._content_row(story, 'CAUSE', s.cause)
            self._content_row(story, 'IMMEDIATE ACTION', s.immediate_action)
            self._content_row(story, 'NOTES', s.notes)
            story.append(Spacer(1, 0.25*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_ems_objectives_report(self, objectives, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Environmental Objectives — {objectives.count()} records', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        for obj in objectives[:100]:
            due = obj.due_date.strftime('%d %b %Y') if obj.due_date else 'No due date'
            status_disp = obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status
            self._section_header(story, f'  {obj.title}  ·  {status_disp}')

            responsible = '-'
            if obj.responsible_person:
                responsible = obj.responsible_person.get_full_name() or obj.responsible_person.username

            self._info_grid(story, [
                ['Title', obj.title, 'Status', status_disp],
                ['Due Date', due, 'Responsible', responsible],
                ['Site', obj.site.name if obj.site else 'All Sites',
                 'Indicator', obj.indicator or '-'],
            ])
            self._content_row(story, 'TARGET / DESCRIPTION', obj.target_description)
            self._content_row(story, 'NOTES', obj.notes)
            story.append(Spacer(1, 0.2*inch))

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_ems_energy_report(self, readings, site_name=""):
        buf, doc = self._base_doc()
        story = []
        self._header(story, site_name)
        story.append(Paragraph(f'Energy & Water Consumption — {readings.count()} readings', self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))

        data = [['Date', 'Site', 'Resource', 'Quantity', 'Unit Cost', 'Total Cost', 'Meter Ref', 'Recorded By']]
        for r in readings[:200]:
            qty = float(r.quantity or 0)
            cost = float(r.unit_cost or 0)
            total = qty * cost if r.unit_cost else '-'
            total_str = f'${total:,.2f}' if isinstance(total, float) else '-'
            recorded_by = '-'
            if r.recorded_by:
                recorded_by = (r.recorded_by.get_full_name() or r.recorded_by.username)[:16]
            data.append([
                r.reading_date.strftime('%d/%m/%Y') if r.reading_date else '-',
                r.site.name[:14] if r.site else 'N/A',
                r.get_resource_type_display() if hasattr(r, 'get_resource_type_display') else r.resource_type,
                f'{qty:,.3f}',
                f'${cost:,.2f}' if r.unit_cost else '-',
                total_str,
                (r.meter_reference or '-')[:14],
                recorded_by,
            ])
        self._std_table(story, data,
                        [0.75*inch, 0.85*inch, 1.1*inch, 0.8*inch, 0.7*inch, 0.7*inch, 0.85*inch, 0.7*inch])

        notes_records = [r for r in readings[:200] if r.notes and r.notes.strip()]
        if notes_records:
            self._section_header(story, '  NOTES', color=_MIDBLUE)
            for r in notes_records:
                self._content_row(story, r.reading_date.strftime('%d/%m/%Y') if r.reading_date else '-', r.notes)

        self._footer(story)
        doc.build(story)
        buf.seek(0)
        return buf
