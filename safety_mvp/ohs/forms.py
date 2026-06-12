from django import forms
from django.contrib.auth.models import User

from .models import (
    AttendanceRecord,
    CAPAAction,
    CCVCriticalControlVerification,
    Certification,
    Contractor,
    Document,
    Employee,
    EnergyWaterConsumption,
    EnvironmentalAspect,
    EnvironmentalObjective,
    FLRA,
    FRA,
    Incident,
    JSA,
    Material,
    MedicalAssessment,
    MedicalProfile,
    Objective,
    Observation,
    ProjectPreset,
    PTOChemicalHazardousSubstance,
    SafetyChecklist,
    ScheduleItem,
    SiteProject,
    SpillReleaseIncident,
    TenantPreset,
    TenantMembership,
    ToolboxTalk,
    MonthlySiteHealthReport,
    TrainingMatrix,
    WasteManagementLog,
)


class TenantScopedModelForm(forms.ModelForm):
    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field, forms.ModelMultipleChoiceField):
                existing_class = field.widget.attrs.get('class', '').strip()
                widget_class = f'{existing_class} searchable-multiselect-source'.strip()
                field.widget.attrs['class'] = widget_class
                field.widget.attrs.setdefault('data-placeholder', 'Search...')

        if tenant is None:
            return

        if 'site' in self.fields:
            self.fields['site'].queryset = SiteProject.objects.filter(tenant=tenant).order_by('name')
        if 'site_project' in self.fields:
            self.fields['site_project'].queryset = SiteProject.objects.filter(tenant=tenant).order_by('name')

        member_user_ids = TenantMembership.objects.filter(
            tenant=tenant,
            is_active=True,
        ).values_list('user_id', flat=True)

        user_fields = [
            'assigned_to',
            'owner',
            'verified_by',
            'investigation_lead',
            'action_owner',
            'supervisor_approval',
            'approver',
            'employee',
            'assessor',
            'manager',
            'responsible_person',
        ]
        for field in user_fields:
            if field in self.fields:
                self.fields[field].queryset = User.objects.filter(id__in=member_user_ids).order_by('username')

        if 'employee' in self.fields and isinstance(self.fields['employee'], forms.ModelChoiceField):
            if self.fields['employee'].queryset.model is Employee:
                self.fields['employee'].queryset = Employee.objects.filter(tenant=tenant).order_by('name')

        if 'assigned_employees' in self.fields:
            self.fields['assigned_employees'].queryset = Employee.objects.filter(tenant=tenant).order_by('name')
            self.fields['assigned_employees'].widget = forms.SelectMultiple(attrs={'class': 'emp-select', 'size': '5'})

        if 'attendee_employees' in self.fields:
            self.fields['attendee_employees'].queryset = Employee.objects.filter(tenant=tenant).order_by('name')
            self.fields['attendee_employees'].widget = forms.SelectMultiple(attrs={'class': 'emp-select', 'size': '5'})

        if 'profile' in self.fields:
            self.fields['profile'].queryset = MedicalProfile.objects.filter(tenant=tenant).order_by('employee__name')

        if 'related_material' in self.fields:
            self.fields['related_material'].queryset = Material.objects.filter(tenant=tenant).order_by('name')

        if 'certifications' in self.fields:
            self.fields['certifications'].queryset = Certification.objects.filter(tenant=tenant).order_by('name')
            self.fields['certifications'].widget.attrs.setdefault('data-placeholder', 'Search certifications...')

        if 'attachments' in self.fields:
            self.fields['attachments'].queryset = Document.objects.filter(tenant=tenant).order_by('name')
            self.fields['attachments'].widget.attrs.setdefault('data-placeholder', 'Search documents...')

        if 'selected_employees' in self.fields:
            self.fields['selected_employees'].queryset = Employee.objects.filter(tenant=tenant).order_by('name')
            self.fields['selected_employees'].widget = forms.SelectMultiple(attrs={'class': 'emp-select', 'size': '5'})


class IncidentForm(TenantScopedModelForm):
    class Meta:
        model = Incident
        exclude = ('tenant', 'date_reported', 'reported_by')


class JSAForm(TenantScopedModelForm):
    class Meta:
        model = JSA
        exclude = ('tenant', 'date', 'performed_by', 'created_at', 'updated_at')


class FRAForm(TenantScopedModelForm):
    class Meta:
        model = FRA
        exclude = ('tenant', 'date_assessed', 'assessed_by')


class FLRAForm(TenantScopedModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'selected_employees' in self.fields:
            self.fields['selected_employees'].queryset = Employee.objects.filter(tenant=self.tenant).order_by('name') if self.tenant else Employee.objects.none()
            self.fields['selected_employees'].widget = forms.SelectMultiple(attrs={
                'size': 6,
                'class': 'searchable-multiselect-source',
                'data-placeholder': 'Search employees...',
            })
            self.fields['selected_employees'].label = 'Employees on task'
            self.fields['selected_employees'].help_text = 'Hold Ctrl or Cmd to select one or more employees for the same task.'

        if 'crew' in self.fields:
            self.fields['crew'].label = 'Crew / external workers'
            self.fields['crew'].help_text = 'Optional free text for contractors, visitors, or people not listed as employees.'

    class Meta:
        model = FLRA
        exclude = ('tenant', 'date', 'assessed_by')


class ObservationForm(TenantScopedModelForm):
    class Meta:
        model = Observation
        exclude = ('tenant', 'date', 'observed_by')


class PTOChemicalHazardousSubstanceForm(TenantScopedModelForm):
    class Meta:
        model = PTOChemicalHazardousSubstance
        exclude = ('tenant', 'created_at')


class CCVCriticalControlVerificationForm(TenantScopedModelForm):
    class Meta:
        model = CCVCriticalControlVerification
        exclude = ('tenant', 'created_at')


class SafetyChecklistForm(TenantScopedModelForm):
    class Meta:
        model = SafetyChecklist
        exclude = ('tenant', 'completed_by')


class TenantPresetForm(forms.ModelForm):
    class Meta:
        model = TenantPreset
        fields = (
            'ccv_target',
            'pto_target',
            'flra_target',
            'employee_target',
            'objective_target',
            'company_logo',
        )


class ProjectPresetForm(TenantScopedModelForm):
    class Meta:
        model = ProjectPreset
        exclude = ('tenant',)
        fields = ('man_hours_target', 'incident_target', 'jsa_target', 'fra_target', 'flra_target', 'ccv_target', 'safety_incidents_severity_target')


class ToolboxTalkForm(TenantScopedModelForm):
    class Meta:
        model = ToolboxTalk
        exclude = ('tenant', 'created_at', 'conducted_by', 'attendance_count')
        labels = {
            'attendee_employees': 'Attendees (select from employee register)',
            'attendees': 'Additional attendees (not in register)',
        }


class EmployeeForm(TenantScopedModelForm):
    class Meta:
        model = Employee
        exclude = ('tenant',)
        fields = ('name', 'position', 'department', 'contact_number', 'emergency_contact', 'scope', 'expert_traits', 'user', 'site', 'certifications', 'employee_file')


class MonthlySiteHealthReportForm(TenantScopedModelForm):
    class Meta:
        model = MonthlySiteHealthReport
        exclude = ('tenant',)

    def clean(self):
        cleaned = super().clean()
        site = cleaned.get('site_project')
        month = cleaned.get('report_month')
        year = cleaned.get('report_year')
        if site and month and year:
            qs = MonthlySiteHealthReport.objects.filter(
                site_project=site, report_month=month, report_year=year
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'A report for {site} — {dict(MonthlySiteHealthReport._meta.get_field("report_month").choices).get(month, month)} {year} already exists.'
                )
        return cleaned


class ContractorForm(TenantScopedModelForm):
    class Meta:
        model = Contractor
        exclude = ('tenant',)


class CertificationForm(TenantScopedModelForm):
    class Meta:
        model = Certification
        exclude = ('tenant',)


class TrainingMatrixForm(TenantScopedModelForm):
    class Meta:
        model = TrainingMatrix
        exclude = ('tenant',)


class ObjectiveForm(TenantScopedModelForm):
    class Meta:
        model = Objective
        exclude = ('tenant',)


class DocumentForm(TenantScopedModelForm):
    class Meta:
        model = Document
        exclude = ('tenant', 'upload_date', 'uploaded_by')


class MaterialForm(TenantScopedModelForm):
    class Meta:
        model = Material
        exclude = ('tenant',)


class ScheduleItemForm(TenantScopedModelForm):
    class Meta:
        model = ScheduleItem
        exclude = ('tenant', 'created_by', 'created_at', 'updated_at')


class CAPAActionForm(TenantScopedModelForm):
    class Meta:
        model = CAPAAction
        exclude = ('tenant', 'created_by', 'created_at', 'updated_at')


class MedicalProfileForm(TenantScopedModelForm):
    class Meta:
        model = MedicalProfile
        exclude = ('tenant', 'created_at', 'updated_at')


class MedicalAssessmentForm(TenantScopedModelForm):
    class Meta:
        model = MedicalAssessment
        exclude = ('tenant', 'created_at')


class SiteProjectForm(TenantScopedModelForm):
    class Meta:
        model = SiteProject
        exclude = ('tenant',)


class AttendanceRecordForm(TenantScopedModelForm):
    class Meta:
        model = AttendanceRecord
        exclude = ('tenant',)
        fields = ('site_project', 'employee', 'date', 'start_time', 'end_time', 'break_duration_minutes', 'notes')


class EnvironmentalAspectForm(TenantScopedModelForm):
    class Meta:
        model = EnvironmentalAspect
        exclude = ('tenant', 'created_at', 'updated_at')


class WasteManagementLogForm(TenantScopedModelForm):
    class Meta:
        model = WasteManagementLog
        exclude = ('tenant', 'recorded_by')


class SpillReleaseIncidentForm(TenantScopedModelForm):
    class Meta:
        model = SpillReleaseIncident
        exclude = ('tenant', 'reported_by')


class EnvironmentalObjectiveForm(TenantScopedModelForm):
    class Meta:
        model = EnvironmentalObjective
        exclude = ('tenant', 'created_at', 'updated_at')


class EnergyWaterConsumptionForm(TenantScopedModelForm):
    class Meta:
        model = EnergyWaterConsumption
        exclude = ('tenant', 'recorded_by')
