"""
PDF Export utilities for OHS application.
Generates professional PDF reports for various modules.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
import os


class PDFGenerator:
    """Generate professional PDF reports."""

    def __init__(self, title="OHS Report", company_name=""):
        self.title = title
        self.company_name = company_name
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0f8f6f'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0a6f54'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#374151'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            lineHeight=1.4
        ))

    def generate_incidents_report(self, incidents, site_name=""):
        """Generate PDF report for incidents."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Header
        story.append(Paragraph(self.title, self.styles['CustomTitle']))
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Summary
        story.append(Paragraph(f"Total Incidents: {incidents.count()}", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.15*inch))

        # Table Data
        table_data = [['Date', 'Site / Project', 'Type', 'Severity', 'Description', 'Status']]
        for incident in incidents[:100]:  # Limit to 100 per page
            table_data.append([
                incident.date_of_incident.strftime('%m/%d/%Y') if incident.date_of_incident else 'N/A',
                incident.site.name if getattr(incident, 'site', None) else 'Unknown',
                incident.get_incident_type_display() if hasattr(incident, 'get_incident_type_display') else getattr(incident, 'incident_type', '')[:15],
                incident.get_severity_display() if hasattr(incident, 'get_severity_display') else getattr(incident, 'severity', '')[:10],
                incident.description[:40] + '...' if len(incident.description or '') > 40 else incident.description or '',
                incident.status if hasattr(incident, 'status') else 'Open'
            ])

        # Create table
        table = Table(table_data, colWidths=[1*inch, 1.5*inch, 1.1*inch, 1*inch, 1.4*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))

        story.append(table)

        # Footer
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit",
            self.styles['CustomNormal']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_attendance_report(self, attendance_records, site_name=""):
        """Generate PDF report for attendance with man-hours summary."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Header
        story.append(Paragraph("Attendance & Man-Hours Report", self.styles['CustomTitle']))
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Summary
        total_hours = sum(record.get_man_hours() for record in attendance_records)
        total_days = attendance_records.count()
        story.append(Paragraph(f"Total Attendance Records: {total_days}", self.styles['CustomHeading']))
        story.append(Paragraph(f"Total Man-Hours: {round(total_hours, 2)}", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.15*inch))

        # Table Data
        table_data = [['Date', 'Employee', 'Start Time', 'End Time', 'Break (min)', 'Man-Hours']]
        for record in attendance_records[:100]:
            table_data.append([
                record.date.strftime('%m/%d/%Y'),
                record.employee.name[:20],
                record.start_time.strftime('%H:%M'),
                record.end_time.strftime('%H:%M'),
                str(record.break_duration_minutes),
                f"{record.get_man_hours():.1f}h"
            ])

        # Create table
        table = Table(table_data, colWidths=[1*inch, 1.5*inch, 1*inch, 1*inch, 1.2*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))

        story.append(table)

        # Footer
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit",
            self.styles['CustomNormal']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_employees_report(self, employees, site_name=""):
        """Generate PDF report for employees."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Header
        story.append(Paragraph("Employee Directory", self.styles['CustomTitle']))
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Summary
        story.append(Paragraph(f"Total Employees: {employees.count()}", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.15*inch))

        # Table Data
        table_data = [['Name', 'Position', 'Department', 'Scope', 'Contact', 'Emergency Contact']]
        for emp in employees[:100]:
            table_data.append([
                emp.name[:20],
                emp.position[:15],
                emp.department[:15],
                emp.get_scope_display() if hasattr(emp, 'get_scope_display') else emp.scope[:10],
                emp.contact_number[:15],
                emp.emergency_contact[:20]
            ])

        # Create table
        table = Table(table_data, colWidths=[1.2*inch, 1.1*inch, 1.1*inch, 1*inch, 1.2*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))

        story.append(table)

        # Footer
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit",
            self.styles['CustomNormal']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_jsa_report(self, jsas, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Job Safety Analysis Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total JSAs: {jsas.count()}", self.styles['CustomHeading']))
        table_data = [['JSA #', 'Job Task', 'Site', 'Assessment Date', 'Performed By']]
        for jsa in jsas[:100]:
            table_data.append([
                jsa.jsa_number or 'N/A',
                jsa.job_task[:24],
                jsa.site.name if jsa.site else 'N/A',
                jsa.assessment_date.strftime('%m/%d/%Y') if jsa.assessment_date else 'N/A',
                jsa.senior_supervisor_name or jsa.work_group_supervisor_name or 'N/A',
            ])
        table = Table(table_data, colWidths=[1.2*inch, 2.2*inch, 1.4*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_fra_report(self, fras, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Formal Risk Assessment Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total FRAs: {fras.count()}", self.styles['CustomHeading']))
        table_data = [['Activity', 'Location', 'Hazard Category', 'Risk Level', 'Assessed By']]
        for fra in fras[:100]:
            table_data.append([
                fra.activity[:24],
                fra.location[:18],
                fra.hazard_category[:16],
                fra.risk_level or 'N/A',
                fra.assessed_by.username if getattr(fra, 'assessed_by', None) else 'N/A',
            ])
        table = Table(table_data, colWidths=[1.6*inch, 1.4*inch, 1.4*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_flra_report(self, flras, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Field Level Risk Assessment Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total FLRAs: {flras.count()}", self.styles['CustomHeading']))
        table_data = [['Date', 'Site', 'Shift', 'Task', 'Employees']]
        for flra in flras[:100]:
            table_data.append([
                flra.date.strftime('%m/%d/%Y') if flra.date else 'N/A',
                flra.site.name if flra.site else 'N/A',
                flra.shift or 'N/A',
                flra.task_description[:22],
                getattr(flra, 'selected_employee_names', '-')[:30],
            ])
        table = Table(table_data, colWidths=[1*inch, 1.2*inch, 1*inch, 2.2*inch, 1.4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_observations_report(self, observations, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Observation & CCV Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Observations: {observations.count()}", self.styles['CustomHeading']))
        table_data = [['Date', 'Site', 'Task', 'Type', 'Follow-up']]
        for observation in observations[:100]:
            table_data.append([
                observation.date.strftime('%m/%d/%Y') if observation.date else 'N/A',
                observation.site.name if observation.site else 'N/A',
                observation.task[:24],
                observation.observation_type,
                'Yes' if observation.follow_up_required else 'No',
            ])
        table = Table(table_data, colWidths=[1*inch, 1.3*inch, 2.2*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_toolbox_talks_report(self, toolbox_talks, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Toolbox Talks Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Talks: {toolbox_talks.count()}", self.styles['CustomHeading']))
        table_data = [['Date', 'Title', 'Site', 'Facilitator', 'Attendance']]
        for talk in toolbox_talks[:100]:
            table_data.append([
                talk.talk_date.strftime('%m/%d/%Y') if talk.talk_date else 'N/A',
                talk.title[:24],
                talk.site.name if talk.site else 'N/A',
                talk.facilitator_name or 'N/A',
                str(talk.attendance_count),
            ])
        table = Table(table_data, colWidths=[1*inch, 2*inch, 1.3*inch, 1.5*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_certifications_report(self, certifications, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Certifications Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Certifications: {certifications.count()}", self.styles['CustomHeading']))
        table_data = [['Employee', 'Certification', 'Issuer', 'Issue', 'Expiry']]
        for cert in certifications[:100]:
            table_data.append([
                cert.employee.username if getattr(cert, 'employee', None) else 'N/A',
                cert.name[:24],
                cert.issuing_body[:20],
                cert.issue_date.strftime('%m/%d/%Y') if cert.issue_date else 'N/A',
                cert.expiry_date.strftime('%m/%d/%Y') if cert.expiry_date else 'N/A',
            ])
        table = Table(table_data, colWidths=[1.4*inch, 1.7*inch, 1.4*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_documents_report(self, documents, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Document Library Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Documents: {documents.count()}", self.styles['CustomHeading']))
        table_data = [['Name', 'Type', 'Site', 'Uploaded', 'Uploader']]
        for doc_item in documents[:100]:
            table_data.append([
                doc_item.name[:24],
                doc_item.doc_type,
                doc_item.site.name if doc_item.site else 'N/A',
                doc_item.upload_date.strftime('%m/%d/%Y') if doc_item.upload_date else 'N/A',
                doc_item.uploaded_by.username if getattr(doc_item, 'uploaded_by', None) else 'N/A',
            ])
        table = Table(table_data, colWidths=[1.8*inch, 0.9*inch, 1.4*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_training_report(self, trainings, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Training Matrix Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Training Items: {trainings.count()}", self.styles['CustomHeading']))
        table_data = [['Title', 'Site', 'Date', 'Due', 'Status']]
        for item in trainings[:100]:
            table_data.append([
                item.title[:26],
                item.site.name if item.site else 'N/A',
                item.training_date.strftime('%m/%d/%Y') if item.training_date else 'N/A',
                item.due_date.strftime('%m/%d/%Y') if item.due_date else 'N/A',
                item.status,
            ])
        table = Table(table_data, colWidths=[1.8*inch, 1.3*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_objectives_report(self, objectives, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Objectives Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Objectives: {objectives.count()}", self.styles['CustomHeading']))
        table_data = [['Objective', 'Site', 'Status', 'Progress', 'Due']]
        for objective_item in objectives[:100]:
            table_data.append([
                objective_item.name[:26],
                objective_item.site.name if objective_item.site else 'N/A',
                objective_item.status,
                f"{objective_item.progress_percent()}%",
                objective_item.due_date.strftime('%m/%d/%Y') if objective_item.due_date else 'N/A',
            ])
        table = Table(table_data, colWidths=[1.8*inch, 1.3*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_materials_report(self, materials, site_name=""):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = [Paragraph("Materials Inventory Report", self.styles['CustomTitle'])]
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Total Materials: {materials.count()}", self.styles['CustomHeading']))
        table_data = [['Name', 'Site', 'Quantity', 'Received', 'SDS Available']]
        for material_item in materials[:100]:
            table_data.append([
                material_item.name[:24],
                material_item.site.name if material_item.site else 'N/A',
                f"{material_item.quantity} {material_item.unit}",
                material_item.date_received.strftime('%m/%d/%Y') if material_item.date_received else 'N/A',
                'Yes' if material_item.sds_available else 'No',
            ])
        table = Table(table_data, colWidths=[1.8*inch, 1.3*inch, 1.4*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit", self.styles['CustomNormal']))
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_site_health_report(self, reports, site_name=""):
        """Generate PDF report for monthly site health and safety summaries."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []
        story.append(Paragraph("Monthly Site Health & Safety Report", self.styles['CustomTitle']))
        if self.company_name:
            story.append(Paragraph(self.company_name, self.styles['Normal']))
        if site_name:
            story.append(Paragraph(f"Site: {site_name}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        table_data = [['Month', 'Year', 'Site / Project', 'Incidents', 'Near Misses', 'Observations', 'Inspections', 'Training Hrs', 'Man-Hours']]
        for report in reports[:100]:
            month_name = dict(report._meta.get_field('report_month').choices).get(report.report_month, str(report.report_month))
            table_data.append([
                month_name,
                str(report.report_year),
                report.site_project.name if report.site_project else 'Unknown',
                str(report.incident_count),
                str(report.near_miss_count),
                str(report.observation_count),
                str(report.inspection_count),
                f"{float(report.training_hours):.1f}",
                f"{float(report.man_hours):.1f}",
            ])

        table = Table(table_data, colWidths=[0.8*inch, 0.6*inch, 1.3*inch, 0.8*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.85*inch, 0.85*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f8f6f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))

        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            f"<b>Page generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | OHS ISO 45001 Toolkit",
            self.styles['CustomNormal']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer
