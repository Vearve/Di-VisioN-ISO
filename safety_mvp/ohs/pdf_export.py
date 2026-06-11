"""
PDF Export utilities for OHS application.
Retro-tech document layout: dark navy banner, teal accent, consistent table styling.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime

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
        data = [['Date', 'Site / Project', 'Type', 'Severity', 'Description', 'Status']]
        for inc in incidents[:100]:
            data.append([
                inc.date_of_incident.strftime('%d/%m/%Y') if inc.date_of_incident else 'N/A',
                inc.site.name if getattr(inc, 'site', None) else 'Unknown',
                (inc.get_incident_type_display() if hasattr(inc, 'get_incident_type_display')
                 else getattr(inc, 'incident_type', ''))[:15],
                (inc.get_severity_display() if hasattr(inc, 'get_severity_display')
                 else getattr(inc, 'severity', ''))[:10],
                (inc.description or '')[:40] + ('…' if len(inc.description or '') > 40 else ''),
                getattr(inc, 'status', 'Open'),
            ])
        self._std_table(story, data, [0.9*inch, 1.4*inch, 1.1*inch, 0.9*inch, 1.5*inch, 0.7*inch])
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
        data = [['JSA #', 'Job Task', 'Site', 'Assessment Date', 'Performed By']]
        for jsa in jsas[:100]:
            data.append([
                jsa.jsa_number or 'N/A',
                jsa.job_task[:26],
                jsa.site.name if jsa.site else 'N/A',
                jsa.assessment_date.strftime('%d/%m/%Y') if jsa.assessment_date else 'N/A',
                (jsa.senior_supervisor_name or jsa.work_group_supervisor_name or 'N/A')[:20],
            ])
        self._std_table(story, data, [1.1*inch, 2.1*inch, 1.3*inch, 1.2*inch, 1.3*inch])
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
        data = [['Activity', 'Location', 'Hazard Category', 'Risk Level', 'Assessed By']]
        for fra in fras[:100]:
            data.append([
                fra.activity[:26],
                fra.location[:18],
                fra.hazard_category[:18],
                fra.risk_level or 'N/A',
                (fra.assessed_by.username if getattr(fra, 'assessed_by', None) else 'N/A')[:16],
            ])
        self._std_table(story, data, [1.6*inch, 1.4*inch, 1.5*inch, 0.9*inch, 1.3*inch])
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
        data = [['Date', 'Site', 'Shift', 'Task', 'Employees']]
        for flra in flras[:100]:
            data.append([
                flra.date.strftime('%d/%m/%Y') if flra.date else 'N/A',
                flra.site.name if flra.site else 'N/A',
                flra.shift or 'N/A',
                flra.task_description[:24],
                getattr(flra, 'selected_employee_names', '-')[:32],
            ])
        self._std_table(story, data, [1*inch, 1.2*inch, 0.9*inch, 2.2*inch, 1.4*inch])
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
        data = [['Date', 'Site', 'Task', 'Type', 'Follow-up']]
        for obs in observations[:100]:
            data.append([
                obs.date.strftime('%d/%m/%Y') if obs.date else 'N/A',
                obs.site.name if obs.site else 'N/A',
                obs.task[:26],
                obs.observation_type,
                'Yes' if obs.follow_up_required else 'No',
            ])
        self._std_table(story, data, [0.95*inch, 1.3*inch, 2.3*inch, 1.05*inch, 0.85*inch])
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
