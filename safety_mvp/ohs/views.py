from django.contrib import messages
from django.shortcuts import redirect, render
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from datetime import timedelta, datetime
from django.utils.timezone import localdate
import operator
import logging
import traceback
from functools import reduce
from django.db.models import Q, Sum

logger = logging.getLogger(__name__)
from .pdf_export import PDFGenerator
from .models import Incident, JSA, JSAStep, FRA, FLRA, Document, Material, Observation, PTOChemicalHazardousSubstance, CCVCriticalControlVerification, SafetyChecklist, ToolboxTalk, Certification, Contractor, Employee, Objective, TrainingMatrix, ScheduleItem, Reminder, CAPAAction, MedicalProfile, MedicalAssessment, AuditLog, KPIDailySnapshot, AnalyticsWarehouseDaily, SiteProject, SiteProjectAttachment, TenantPreset, AttendanceRecord, ProjectPreset, MonthlySiteHealthReport, EnvironmentalAspect, WasteManagementLog, SpillReleaseIncident, EnvironmentalObjective, EnergyWaterConsumption
from .tenant_context import has_minimum_role, user_role_for_tenant, user_tenants
from .forms import (
    AttendanceRecordForm,
    CAPAActionForm,
    CCVCriticalControlVerificationForm,
    CertificationForm,
    ContractorForm,
    DocumentForm,
    EmployeeForm,
    EnergyWaterConsumptionForm,
    EnvironmentalAspectForm,
    EnvironmentalObjectiveForm,
    FLRAForm,
    FRAForm,
    IncidentForm,
    JSAForm,
    MaterialForm,
    MedicalAssessmentForm,
    MedicalProfileForm,
    ObjectiveForm,
    ObservationForm,
    ProjectPresetForm,
    PTOChemicalHazardousSubstanceForm,
    SafetyChecklistForm,
    ScheduleItemForm,
    SiteProjectForm,
    SpillReleaseIncidentForm,
    TenantPresetForm,
    ToolboxTalkForm,
    TrainingMatrixForm,
    MonthlySiteHealthReportForm,
    WasteManagementLogForm,
)

TARGETS = {
    'observation': 20,   # CCV including PTO
    'flra': 500,
    'jsa': 15,
    'fra': 1,
    # SDS and SOP have no count/target
    # The rest don't need a target
}


def safe_root(request):
    return HttpResponse('App is running', content_type='text/plain')


def _calculate_kpi_metrics(site, tenant, date_from=None, date_to=None):
    """Calculate KPI metrics for a project/site."""
    from django.utils.timezone import localdate
    from datetime import timedelta
    
    if date_to is None:
        date_to = localdate()
    if date_from is None:
        # Default to last 30 days
        date_from = date_to - timedelta(days=30)
    
    # Get or create project preset
    preset, _ = ProjectPreset.objects.get_or_create(
        site_project=site,
        tenant=tenant,
        defaults={
            'man_hours_target': 1000,
            'incident_target': 0,
            'jsa_target': 10,
            'fra_target': 5,
            'flra_target': 100,
            'ccv_target': 20,
        }
    )
    
    # Calculate attendance/man-hours
    attendance_records = AttendanceRecord.objects.filter(
        site_project=site,
        tenant=tenant,
        date__gte=date_from,
        date__lte=date_to
    )
    total_man_hours = sum(record.get_man_hours() for record in attendance_records)
    
    # Count incidents by severity
    incidents = Incident.objects.filter(
        site=site,
        tenant=tenant,
        event_datetime__date__gte=date_from,
        event_datetime__date__lte=date_to
    )
    incident_count = incidents.count()
    high_severity_incidents = incidents.filter(severity='Fatality').count()
    
    # Count safety assessments/JSAs
    jsa_count = JSA.objects.filter(
        site=site,
        tenant=tenant,
        date__gte=date_from,
        date__lte=date_to
    ).count()

    fra_count = FRA.objects.filter(
        site=site,
        tenant=tenant,
        date_assessed__gte=date_from,
        date_assessed__lte=date_to
    ).count()

    flra_count = FLRA.objects.filter(
        site=site,
        tenant=tenant,
        date__gte=date_from,
        date__lte=date_to
    ).count()

    ccv_count = CCVCriticalControlVerification.objects.filter(
        site=site,
        tenant=tenant,
        assessment_datetime__date__gte=date_from,
        assessment_datetime__date__lte=date_to
    ).count()
    
    # Calculate compliance metrics
    kpis = {
        'date_range': f"{date_from.strftime('%b %d')} - {date_to.strftime('%b %d, %Y')}",
        'man_hours': {
            'actual': round(total_man_hours, 2),
            'target': preset.man_hours_target,
            'percent': round((total_man_hours / preset.man_hours_target * 100) if preset.man_hours_target > 0 else 0, 1),
            'status': 'On Track' if total_man_hours >= preset.man_hours_target else 'Behind',
        },
        'incidents': {
            'actual': incident_count,
            'target': preset.incident_target,
            'percent': round((incident_count / preset.incident_target * 100) if preset.incident_target > 0 else (0 if incident_count == 0 else 100), 1),
            'status': 'Good' if incident_count <= preset.incident_target else 'Needs Attention',
            'high_severity': high_severity_incidents,
        },
        'jsa': {
            'actual': jsa_count,
            'target': preset.jsa_target,
            'percent': round((jsa_count / preset.jsa_target * 100) if preset.jsa_target > 0 else 0, 1),
            'status': 'On Track' if jsa_count >= preset.jsa_target else 'Behind',
        },
        'fra': {
            'actual': fra_count,
            'target': preset.fra_target,
            'percent': round((fra_count / preset.fra_target * 100) if preset.fra_target > 0 else 0, 1),
            'status': 'On Track' if fra_count >= preset.fra_target else 'Behind',
        },
        'flra': {
            'actual': flra_count,
            'target': preset.flra_target,
            'percent': round((flra_count / preset.flra_target * 100) if preset.flra_target > 0 else 0, 1),
            'status': 'On Track' if flra_count >= preset.flra_target else 'Behind',
        },
        'ccv': {
            'actual': ccv_count,
            'target': preset.ccv_target,
            'percent': round((ccv_count / preset.ccv_target * 100) if preset.ccv_target > 0 else 0, 1),
            'status': 'On Track' if ccv_count >= preset.ccv_target else 'Behind',
        },
        'preset': preset,
    }
    
    return kpis


def _scope_queryset(qs, current_tenant=None, current_site=None):
    if current_tenant is None:
        return qs.none()

    scoped = qs.filter(tenant=current_tenant)
    if current_site:
        if any(field.name == 'site' for field in qs.model._meta.fields):
            scoped = scoped.filter(site=current_site)
        if any(field.name == 'site_project' for field in qs.model._meta.fields):
            scoped = scoped.filter(site_project=current_site)
    return scoped


def _sidebar_site_metrics(current_tenant=None, current_site=None):
    if current_tenant is None:
        return {
            'sidebar_employee_count': 0,
            'sidebar_training_count': 0,
            'sidebar_objective_count': 0,
            'sidebar_material_count': 0,
            'sidebar_document_count': 0,
        }

    return {
        'sidebar_employee_count': _scope_queryset(Employee.objects.all(), current_tenant, current_site).count(),
        'sidebar_training_count': _scope_queryset(TrainingMatrix.objects.all(), current_tenant, current_site).count(),
        'sidebar_objective_count': _scope_queryset(Objective.objects.all(), current_tenant, current_site).count(),
        'sidebar_material_count': _scope_queryset(Material.objects.all(), current_tenant, current_site).count(),
        'sidebar_document_count': _scope_queryset(Document.objects.all(), current_tenant, current_site).count(),
    }


def _tenant_targets(current_tenant):
    if current_tenant is None:
        return {
            'ccv_target': TARGETS['observation'],
            'pto_target': TARGETS['observation'],
            'flra_target': TARGETS['flra'],
            'employee_target': 0,
            'objective_target': 0,
        }

    presets, _ = TenantPreset.objects.get_or_create(tenant=current_tenant)
    return {
        'ccv_target': presets.ccv_target,
        'pto_target': presets.pto_target,
        'flra_target': presets.flra_target,
        'employee_target': presets.employee_target,
        'objective_target': presets.objective_target,
    }


def _get_company_logo_url(tenant):
    if not tenant:
        return None
    try:
        preset = TenantPreset.objects.get(tenant=tenant)
        if preset.company_logo:
            return preset.company_logo.url
    except Exception:
        pass
    return None


@login_required
def home(request):
    try:
        return _home_inner(request)
    except Exception:
        logger.exception("Home view crashed — tenant=%s site=%s user=%s",
                         getattr(request, 'current_tenant', None),
                         getattr(request, 'current_site', None),
                         getattr(request.user, 'username', '?'))
        raise


def _home_inner(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    today = localdate()
    target_values = _tenant_targets(current_tenant)

    def scoped(model):
        return _scope_queryset(model.objects.all(), current_tenant, current_site)

    data = {
        'incident_count': scoped(Incident).count(),
        'jsa_count': scoped(JSA).count(),
        'fra_count': scoped(FRA).count(),
        'flra_count': scoped(FLRA).count(),
        'document_count': scoped(Document).count(),
        'material_count': scoped(Material).count(),
        'observation_count': scoped(Observation).count(),
        'safetychecklist_count': scoped(SafetyChecklist).count(),
        'certification_count': scoped(Certification).count(),
        'contractor_count': scoped(Contractor).count(),
        'employee_count': scoped(Employee).count(),
        'attendance_count': scoped(AttendanceRecord).count(),
        'schedule_count': scoped(ScheduleItem).count(),
        'pending_reminder_count': scoped(Reminder).filter(status='pending').count(),
        'capa_open_count': scoped(CAPAAction).exclude(status='closed').count(),
        'capa_overdue_count': scoped(CAPAAction).exclude(status='closed').filter(due_date__lt=today).count(),
        'medical_due_count': scoped(MedicalProfile).filter(next_medical_due__isnull=False, next_medical_due__lte=today + timedelta(days=30)).count(),
        'audit_event_count': scoped(AuditLog).count(),

        # Targets for bar chart
        'observation_target': target_values['ccv_target'] + target_values['pto_target'],
        'flra_target': target_values['flra_target'],
        'jsa_target': TARGETS['jsa'],
        'fra_target': TARGETS['fra'],
    }

    today_checklists = scoped(SafetyChecklist).filter(checklist_type='Daily', date_completed=today)
    today_checklist_count = today_checklists.count()

    objectives = scoped(Objective)
    training_matrix = scoped(TrainingMatrix)
    reminders = scoped(Reminder).filter(status='pending').order_by('remind_on', 'due_date')[:8]
    schedule_items = scoped(ScheduleItem).filter(is_active=True).order_by('next_due_date')[:8]
    capa_actions = scoped(CAPAAction).exclude(status='closed').order_by('due_date', 'priority')[:8]
    medical_due = scoped(MedicalProfile).filter(next_medical_due__isnull=False).order_by('next_medical_due')[:8]
    recent_audit_events = scoped(AuditLog).order_by('-created_at')[:10]
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    available_sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name') if current_tenant else SiteProject.objects.none()
    current_role = user_role_for_tenant(request.user, current_tenant)

    permissions = {
        'can_manage_tenant': has_minimum_role(current_role, 'admin'),
        'can_manage_schedules': has_minimum_role(current_role, 'supervisor'),
        'can_view_docs': has_minimum_role(current_role, 'worker'),
        'can_manage_capa': has_minimum_role(current_role, 'supervisor'),
        'can_manage_medical': has_minimum_role(current_role, 'site_manager'),
    }

    sidebar_metrics = _sidebar_site_metrics(current_tenant, current_site) if current_tenant else {
        'sidebar_employee_count': 0,
        'sidebar_training_count': 0,
        'sidebar_objective_count': 0,
        'sidebar_material_count': 0,
        'sidebar_document_count': 0,
    }

    return render(request, 'home.html', {
        **data,
        'objectives': objectives,
        'training_matrix': training_matrix,
        'upcoming_reminders': reminders,
        'upcoming_schedule_items': schedule_items,
        'open_capa_actions': capa_actions,
        'upcoming_medicals': medical_due,
        'recent_audit_events': recent_audit_events,
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'available_sites': available_sites,
        'current_role': current_role,
        'today_checklist_done': today_checklist_count > 0,
        'today_checklist_count': today_checklist_count,
        'company_logo_url': _get_company_logo_url(current_tenant),
        **sidebar_metrics,
        **permissions,
    })


def schedule_center(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    current_role = user_role_for_tenant(request.user, current_tenant)

    if current_tenant is None:
        schedule_items = ScheduleItem.objects.none()
        reminders = Reminder.objects.none()
    else:
        schedule_items = ScheduleItem.objects.filter(tenant=current_tenant).order_by('next_due_date', 'title')
        reminders = Reminder.objects.filter(tenant=current_tenant).order_by('remind_on', 'due_date')

    return render(request, 'schedule_center.html', {
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'current_role': current_role,
        'can_manage_tenant': has_minimum_role(current_role, 'admin'),
        'can_manage_schedules': has_minimum_role(current_role, 'supervisor'),
        'schedule_items': schedule_items,
        'reminders': reminders,
        'company_logo_url': _get_company_logo_url(current_tenant),
    })


def capa_center(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    current_role = user_role_for_tenant(request.user, current_tenant)

    if current_tenant is None:
        actions = CAPAAction.objects.none()
    else:
        actions = CAPAAction.objects.filter(tenant=current_tenant).order_by('status', 'due_date', '-created_at')

    return render(request, 'capa_center.html', {
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'current_role': current_role,
        'can_manage_tenant': has_minimum_role(current_role, 'admin'),
        'can_manage_capa': has_minimum_role(current_role, 'supervisor'),
        'actions': actions,
        'company_logo_url': _get_company_logo_url(current_tenant),
    })


def medical_center(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    current_role = user_role_for_tenant(request.user, current_tenant)

    if current_tenant is None:
        profiles = MedicalProfile.objects.none()
        assessments = MedicalAssessment.objects.none()
    else:
        profiles = MedicalProfile.objects.filter(tenant=current_tenant).order_by('next_medical_due', 'employee__name')
        assessments = MedicalAssessment.objects.filter(tenant=current_tenant).order_by('-assessment_date')[:30]

    return render(request, 'medical_center.html', {
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'current_role': current_role,
        'can_manage_tenant': has_minimum_role(current_role, 'admin'),
        'can_manage_medical': has_minimum_role(current_role, 'site_manager'),
        'profiles': profiles,
        'assessments': assessments,
        'company_logo_url': _get_company_logo_url(current_tenant),
    })


def analytics_dashboard(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    current_role = user_role_for_tenant(request.user, current_tenant)

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    site_id = request.GET.get('site')

    if current_tenant is None:
        snapshots = AnalyticsWarehouseDaily.objects.none()
        sites = SiteProject.objects.none()
    else:
        snapshots = AnalyticsWarehouseDaily.objects.filter(tenant=current_tenant)
        sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name')

        if site_id:
            snapshots = snapshots.filter(site_id=site_id)
        if start_date:
            snapshots = snapshots.filter(snapshot_date__gte=start_date)
        if end_date:
            snapshots = snapshots.filter(snapshot_date__lte=end_date)

    snapshots = snapshots.order_by('snapshot_date')
    chart_points = list(snapshots.values(
        'snapshot_date',
        'incident_count',
        'open_capa_count',
        'overdue_capa_count',
        'observation_count',
        'checklist_count',
        'medical_due_count',
    ))

    return render(request, 'analytics_dashboard.html', {
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'current_role': current_role,
        'can_manage_tenant': has_minimum_role(current_role, 'admin'),
        'sites': sites,
        'snapshots': snapshots,
        'chart_points': chart_points,
        'selected_site': site_id or '',
        'start_date': start_date or '',
        'end_date': end_date or '',
        'company_logo_url': _get_company_logo_url(current_tenant),
    })


@login_required
def presets_page(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    available_sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name') if current_tenant else SiteProject.objects.none()
    current_role = user_role_for_tenant(request.user, current_tenant)

    if not has_minimum_role(current_role, 'supervisor'):
        messages.error(request, 'You do not have access to presets for the selected tenant.')
        return redirect('home')

    if current_tenant is None:
        messages.error(request, 'No tenant selected. Select a tenant first.')
        return redirect('home')

    preset, _ = TenantPreset.objects.get_or_create(tenant=current_tenant)

    if request.method == 'POST':
        form = TenantPresetForm(request.POST, request.FILES, instance=preset)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.tenant = current_tenant
            instance.save()
            messages.success(request, 'Preset targets updated successfully.')
            return redirect('presets_page')
    else:
        form = TenantPresetForm(instance=preset)

    return render(request, 'presets_page.html', {
        'title': 'Presets',
        'description': 'Set target values for CCV, PTO, FLRA, Employees and Objectives.',
        'form': form,
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'available_sites': available_sites,
        'current_role': current_role,
        'active_route': 'presets_page',
        **_sidebar_site_metrics(current_tenant, current_site),
    })


def site_projects_page(request):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    available_sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name') if current_tenant else SiteProject.objects.none()
    current_role = user_role_for_tenant(request.user, current_tenant)

    if not has_minimum_role(current_role, 'supervisor'):
        messages.error(request, 'You do not have access to site and project management for the selected tenant.')
        return redirect('home')

    site_qs = SiteProject.objects.none()
    if current_tenant:
        site_qs = SiteProject.objects.filter(tenant=current_tenant).order_by('-id')

    edit_instance = None
    edit_id = request.GET.get('edit')
    if edit_id and current_tenant:
        edit_instance = site_qs.filter(id=edit_id).first()

    if request.method == 'POST':
        delete_attachment_id = request.POST.get('delete_attachment_id')
        if delete_attachment_id and current_tenant:
            attachment = SiteProjectAttachment.objects.filter(
                tenant=current_tenant,
                id=delete_attachment_id,
            ).first()
            if attachment:
                site_id_for_redirect = attachment.site_project_id
                attachment.delete()
                messages.success(request, 'Attachment deleted.')
                return redirect(f'/app/sites/?edit={site_id_for_redirect}')
            messages.error(request, 'Attachment not found or not allowed.')
            return redirect('site_projects_page')

        delete_id = request.POST.get('delete_id')
        if delete_id and current_tenant:
            deleting_site = site_qs.filter(id=delete_id).first()
            deleted, _ = site_qs.filter(id=delete_id).delete()
            if deleted:
                if current_site and deleting_site and current_site.id == deleting_site.id:
                    request.session.pop('current_site_id', None)
                messages.success(request, 'Site/Project deleted.')
            else:
                messages.error(request, 'Site/Project not found or not allowed.')
            return redirect('site_projects_page')

        edit_post_id = request.POST.get('edit_id')
        if edit_post_id and current_tenant:
            edit_instance = site_qs.filter(id=edit_post_id).first()

        form = SiteProjectForm(request.POST, request.FILES, tenant=current_tenant, instance=edit_instance)
        if form.is_valid() and current_tenant:
            instance = form.save(commit=False)
            instance.tenant = current_tenant
            instance.save()

            uploaded_files = request.FILES.getlist('site_attachments')
            for uploaded_file in uploaded_files:
                SiteProjectAttachment.objects.create(
                    tenant=current_tenant,
                    site_project=instance,
                    file=uploaded_file,
                    uploaded_by=request.user if request.user.is_authenticated else None,
                )

            if edit_instance:
                messages.success(request, 'Site/Project updated successfully.')
            else:
                messages.success(request, 'Site/Project created successfully.')
            return redirect('site_projects_page')
    else:
        form = SiteProjectForm(tenant=current_tenant, instance=edit_instance)

    site_cards = []
    for site in site_qs:
        attachments = list(site.attachments.all()[:4])
        site_cards.append({
            'site': site,
            'incidents_count': Incident.objects.filter(tenant=current_tenant, site=site).count(),
            'jsa_count': JSA.objects.filter(tenant=current_tenant, site=site).count(),
            'fra_count': FRA.objects.filter(tenant=current_tenant, site=site).count(),
            'employees_count': Employee.objects.filter(tenant=current_tenant, site=site).count(),
            'training_count': TrainingMatrix.objects.filter(tenant=current_tenant, site=site).count(),
            'objectives_count': Objective.objects.filter(tenant=current_tenant, site=site).count(),
            'attachments': attachments,
            'attachments_count': site.attachments.count(),
        })

    return render(request, 'site_projects.html', {
        'title': 'Sites and Projects',
        'description': 'Create and manage operational sites/projects, then open their module workspace.',
        'form': form,
        'is_edit_mode': edit_instance is not None,
        'edit_record_id': edit_instance.id if edit_instance else '',
        'site_cards': site_cards,
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'available_sites': available_sites,
        'current_role': current_role,
        'active_route': 'site_projects_page',
        'editing_attachments': edit_instance.attachments.all() if edit_instance else SiteProjectAttachment.objects.none(),
        'company_logo_url': _get_company_logo_url(current_tenant),
        **_sidebar_site_metrics(current_tenant, current_site),
    })


def site_manage_page(request, site_id):
    current_tenant = getattr(request, 'current_tenant', None)
    current_role = user_role_for_tenant(request.user, current_tenant)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []

    if not has_minimum_role(current_role, 'worker'):
        messages.error(request, 'You do not have access to this site workspace.')
        return redirect('home')

    site = SiteProject.objects.filter(tenant=current_tenant, id=site_id).first() if current_tenant else None
    if not site:
        messages.error(request, 'Site/Project not found for selected tenant.')
        return redirect('site_projects_page')

    request.session['current_site_id'] = site.id
    available_sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name')

    module_links = [
        ('JSA', '/app/jsa/', JSA.objects.filter(tenant=current_tenant, site=site).count()),
        ('FRA', '/app/fra/', FRA.objects.filter(tenant=current_tenant, site=site).count()),
        ('FLRA', '/app/flra/', FLRA.objects.filter(tenant=current_tenant, site=site).count()),
        ('PTO', '/app/pto-chemicals/', PTOChemicalHazardousSubstance.objects.filter(tenant=current_tenant, site=site).count()),
        ('CCV', '/app/ccv/', CCVCriticalControlVerification.objects.filter(tenant=current_tenant, site=site).count()),
        ('Checklists', '/app/checklists/', SafetyChecklist.objects.filter(tenant=current_tenant, site=site).count()),
        ('Toolbox Talks', '/app/toolbox-talks/', ToolboxTalk.objects.filter(tenant=current_tenant, site=site).count()),
        ('Incidents', '/app/incidents/', Incident.objects.filter(tenant=current_tenant, site=site).count()),
        ('Employees', '/app/employees/', Employee.objects.filter(tenant=current_tenant, site=site).count()),
        ('Monthly Health Reports', '/app/monthly-health-reports/', MonthlySiteHealthReport.objects.filter(tenant=current_tenant, site_project=site).count()),
        ('Training', '/app/training/', TrainingMatrix.objects.filter(tenant=current_tenant, site=site).count()),
        ('Objectives', '/app/objectives/', Objective.objects.filter(tenant=current_tenant, site=site).count()),
        ('Materials', '/app/materials/', Material.objects.filter(tenant=current_tenant, site=site).count()),
        ('Documents', '/app/documents/', Document.objects.filter(tenant=current_tenant, site=site).count()),
    ]

    ems_links = [
        ('Env. Aspects Register', '/app/ems/aspects/', EnvironmentalAspect.objects.filter(tenant=current_tenant, site=site).count()),
        ('Waste Management Log', '/app/ems/waste/', WasteManagementLog.objects.filter(tenant=current_tenant, site=site).count()),
        ('Spill & Release Incidents', '/app/ems/spills/', SpillReleaseIncident.objects.filter(tenant=current_tenant, site=site).count()),
        ('Environmental Objectives', '/app/ems/objectives/', EnvironmentalObjective.objects.filter(tenant=current_tenant, site=site).count()),
        ('Energy & Water Consumption', '/app/ems/energy/', EnergyWaterConsumption.objects.filter(tenant=current_tenant, site=site).count()),
    ]

    recent_activity = AuditLog.objects.filter(tenant=current_tenant, site=site).order_by('-created_at')[:12]
    
    # Calculate KPI metrics for the last 30 days
    kpi_metrics = _calculate_kpi_metrics(site, current_tenant)

    return render(request, 'site_manage.html', {
        'site': site,
        'module_links': module_links,
        'ems_links': ems_links,
        'kpi_metrics': kpi_metrics,
        'current_tenant': current_tenant,
        'current_site': site,
        'available_tenants': available_tenants,
        'available_sites': available_sites,
        'current_role': current_role,
        'active_route': 'site_projects_page',
        'recent_activity': recent_activity,
        'company_logo_url': _get_company_logo_url(current_tenant),
        **_sidebar_site_metrics(current_tenant, site),
    })


def site_presets_page(request, site_id):
    """Manage KPI presets for a specific project/site."""
    current_tenant = getattr(request, 'current_tenant', None)
    current_role = user_role_for_tenant(request.user, current_tenant)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []

    if not has_minimum_role(current_role, 'supervisor'):
        messages.error(request, 'You do not have permission to manage project presets.')
        return redirect('home')

    site = SiteProject.objects.filter(tenant=current_tenant, id=site_id).first() if current_tenant else None
    if not site:
        messages.error(request, 'Site/Project not found for selected tenant.')
        return redirect('site_projects_page')

    request.session['current_site_id'] = site.id
    available_sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name')

    preset, _ = ProjectPreset.objects.get_or_create(
        site_project=site,
        tenant=current_tenant,
        defaults={
            'man_hours_target': 1000,
            'incident_target': 0,
            'jsa_target': 10,
            'fra_target': 5,
            'flra_target': 100,
            'ccv_target': 20,
        }
    )

    if request.method == 'POST':
        form = ProjectPresetForm(request.POST, instance=preset, tenant=current_tenant)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.tenant = current_tenant
            instance.site_project = site
            instance.save()
            messages.success(request, 'Project KPI targets updated successfully.')
            return redirect('site_presets_page', site_id=site.id)
    else:
        form = ProjectPresetForm(instance=preset, tenant=current_tenant)

    kpi_metrics = _calculate_kpi_metrics(site, current_tenant)

    return render(request, 'site_presets.html', {
        'site': site,
        'form': form,
        'kpi_metrics': kpi_metrics,
        'current_tenant': current_tenant,
        'current_site': site,
        'available_tenants': available_tenants,
        'available_sites': available_sites,
        'current_role': current_role,
        'active_route': 'site_projects_page',
    })


def _module_page(
    request,
    *,
    model,
    form_class,
    title,
    description,
    route_name,
    user_role_min='worker',
    auto_user_fields=None,
    list_fields=None,
    form_sections=None,
    list_header_info=None,
    extra_context=None,
    post_save_callback=None,
):
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    available_tenants = user_tenants(request.user) if request.user.is_authenticated else []
    available_sites = SiteProject.objects.filter(tenant=current_tenant).order_by('name') if current_tenant else SiteProject.objects.none()
    current_role = user_role_for_tenant(request.user, current_tenant)

    if not has_minimum_role(current_role, user_role_min):
        messages.error(request, 'You do not have access to this page for the selected tenant.')
        return redirect('home')

    search_query = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    PAGE_SIZE = 25

    records = model.objects.none()
    total_count = 0
    if current_tenant:
        qs = _scope_queryset(model.objects.all(), current_tenant, current_site).order_by('-id')
        if search_query:
            # Search across all CharField and TextField fields
            string_fields = [
                f.name for f in model._meta.get_fields()
                if hasattr(f, 'get_internal_type') and f.get_internal_type() in ('CharField', 'TextField')
            ]
            if string_fields:
                q_filter = reduce(operator.or_, [Q(**{f'{f}__icontains': search_query}) for f in string_fields])
                qs = qs.filter(q_filter)
        total_count = qs.count()
        paginator = Paginator(qs, PAGE_SIZE)
        page_obj = paginator.get_page(page_number)
        records = page_obj
    else:
        page_obj = None
        paginator = None

    edit_instance = None
    edit_id = request.GET.get('edit')
    if edit_id and current_tenant:
        edit_qs = _scope_queryset(model.objects.all(), current_tenant, current_site)
        edit_instance = edit_qs.filter(id=edit_id).first()

    if request.method == 'POST':
        delete_id = request.POST.get('delete_id')
        if delete_id and current_tenant:
            delete_qs = _scope_queryset(model.objects.all(), current_tenant, current_site)
            deleted, _ = delete_qs.filter(id=delete_id).delete()
            if deleted:
                messages.success(request, f'{title} record deleted.')
            else:
                messages.error(request, 'Record not found or not allowed.')
            return redirect(route_name)

        edit_post_id = request.POST.get('edit_id')
        if edit_post_id and current_tenant:
            edit_qs = _scope_queryset(model.objects.all(), current_tenant, current_site)
            edit_instance = edit_qs.filter(id=edit_post_id).first()

        form = form_class(request.POST, request.FILES, tenant=current_tenant, instance=edit_instance)
        if form.is_valid() and current_tenant:
            instance = form.save(commit=False)
            instance.tenant = current_tenant
            if current_site and hasattr(instance, 'site_id'):
                instance.site = current_site

            if request.user.is_authenticated:
                for field in (auto_user_fields or []):
                    setattr(instance, f'{field}_id', request.user.pk)

            instance.save()
            form.save_m2m()
            if post_save_callback:
                post_save_callback(request, instance)
            if edit_instance:
                messages.success(request, f'{title} updated successfully.')
            else:
                messages.success(request, f'{title} saved successfully.')
            return redirect(route_name)
    else:
        form = form_class(tenant=current_tenant, instance=edit_instance)

    section_blocks = []
    used_fields = set()
    if form_sections:
        for section_title, section_field_names in form_sections:
            section_fields = []
            for field_name in section_field_names:
                if field_name in form.fields:
                    section_fields.append(form[field_name])
                    used_fields.add(field_name)
            if section_fields:
                section_blocks.append((section_title, section_fields))

    remaining_fields = [form[field] for field in form.fields if field not in used_fields]
    if remaining_fields:
        section_blocks.append(('Other Details', remaining_fields))

    summary_cards = extra_context.get('summary_cards', []) if extra_context else []
    resolved_fields = list_fields or [('id', 'ID'), ('__str__', 'Record')]
    list_columns = [label for _, label in resolved_fields]
    list_rows = []
    for row in records:
        values = []
        for field_name, _ in resolved_fields:
            if field_name == '__str__':
                value = str(row)
            else:
                display_method = f'get_{field_name}_display'
                if hasattr(row, display_method):
                    value = getattr(row, display_method)()
                else:
                    value = getattr(row, field_name, '')
                if isinstance(value, bool):
                    value = 'Yes' if value else 'No'
                if value in (None, ''):
                    value = '-'
            values.append(value)
        list_rows.append({'id': row.id, 'values': values})

    if current_site:
        back_url = f'/app/sites/manage/{current_site.id}/'
        back_label = 'Back to Site Workspace'
    else:
        back_url = '/app/sites/'
        back_label = 'Back to Sites & Projects'

    return render(request, 'module_page.html', {
        'current_tenant': current_tenant,
        'current_site': current_site,
        'available_tenants': available_tenants,
        'available_sites': available_sites,
        'current_role': current_role,
        'can_manage_tenant': has_minimum_role(current_role, 'admin'),
        'can_manage_schedules': has_minimum_role(current_role, 'supervisor'),
        'can_manage_capa': has_minimum_role(current_role, 'supervisor'),
        'can_manage_medical': has_minimum_role(current_role, 'site_manager'),
        'title': title,
        'description': description,
        'form': form,
        'is_edit_mode': edit_instance is not None,
        'edit_record_id': edit_instance.id if edit_instance else '',
        'section_blocks': section_blocks,
        'list_columns': list_columns,
        'list_rows': list_rows,
        'active_route': route_name,
        'current_path': request.path,
        'search_query': search_query,
        'page_obj': page_obj,
        'total_count': total_count,
        'summary_cards': summary_cards,
        'back_url': back_url,
        'back_label': back_label,
        'export_name': route_name.replace('_page', ''),
        'company_logo_url': _get_company_logo_url(current_tenant),
        **_sidebar_site_metrics(current_tenant, current_site),
        **(extra_context or {}),
    })


def export_to_pdf(request, module_name):
    """Export module data to PDF format."""
    current_tenant = getattr(request, 'current_tenant', None)
    current_site = getattr(request, 'current_site', None)
    current_role = user_role_for_tenant(request.user, current_tenant)

    if not has_minimum_role(current_role, 'worker'):
        messages.error(request, 'You do not have permission to export data.')
        return redirect('home')

    if not current_tenant:
        messages.error(request, 'Please select a workspace first.')
        return redirect('home')

    record_id = request.GET.get('record_id')

    def scope_qs(qs):
        qs = _scope_queryset(qs, current_tenant, current_site)
        if record_id:
            qs = qs.filter(id=record_id)
        return qs

    pdf_gen = PDFGenerator(
        title=f"{module_name.replace('_', ' ').title()} Report",
        company_name=current_tenant.name
    )
    site_name = current_site.name if current_site else "All Sites"

    try:
        if module_name == 'incidents':
            data = scope_qs(Incident.objects.all()).order_by('-event_datetime')
            buffer = pdf_gen.generate_incidents_report(data, site_name)
            filename = f"incidents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'attendance':
            data = scope_qs(AttendanceRecord.objects.all()).order_by('-date')
            buffer = pdf_gen.generate_attendance_report(data, site_name)
            filename = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'employees':
            data = scope_qs(Employee.objects.all()).order_by('name')
            buffer = pdf_gen.generate_employees_report(data, site_name)
            filename = f"employees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'jsa':
            data = scope_qs(JSA.objects.all()).order_by('-date')
            buffer = pdf_gen.generate_jsa_report(data, site_name)
            filename = f"jsa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'fra':
            data = scope_qs(FRA.objects.all()).order_by('-date_assessed')
            buffer = pdf_gen.generate_fra_report(data, site_name)
            filename = f"fra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'flra':
            data = scope_qs(FLRA.objects.all()).order_by('-date')
            buffer = pdf_gen.generate_flra_report(data, site_name)
            filename = f"flra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'observations':
            data = scope_qs(Observation.objects.all()).order_by('-date')
            buffer = pdf_gen.generate_observations_report(data, site_name)
            filename = f"observations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'toolbox_talks':
            data = scope_qs(ToolboxTalk.objects.all()).order_by('-talk_date')
            buffer = pdf_gen.generate_toolbox_talks_report(data, site_name)
            filename = f"toolbox_talks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'certifications':
            data = scope_qs(Certification.objects.all()).order_by('-issue_date')
            buffer = pdf_gen.generate_certifications_report(data, site_name)
            filename = f"certifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'documents':
            data = scope_qs(Document.objects.all()).order_by('-upload_date')
            buffer = pdf_gen.generate_documents_report(data, site_name)
            filename = f"documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'training':
            data = scope_qs(TrainingMatrix.objects.all()).order_by('-training_date')
            buffer = pdf_gen.generate_training_report(data, site_name)
            filename = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'objectives':
            data = scope_qs(Objective.objects.all()).order_by('-due_date')
            buffer = pdf_gen.generate_objectives_report(data, site_name)
            filename = f"objectives_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'materials':
            data = scope_qs(Material.objects.all()).order_by('-date_received')
            buffer = pdf_gen.generate_materials_report(data, site_name)
            filename = f"materials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'monthly_site_health_reports':
            data = scope_qs(MonthlySiteHealthReport.objects.all()).order_by('-report_year', '-report_month')
            buffer = pdf_gen.generate_site_health_report(data, site_name)
            filename = f"monthly_site_health_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'checklists':
            data = scope_qs(SafetyChecklist.objects.all()).order_by('-date_completed')
            buffer = pdf_gen.generate_checklists_report(data, site_name)
            filename = f"checklists_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'capa':
            data = scope_qs(CAPAAction.objects.all()).order_by('-due_date')
            buffer = pdf_gen.generate_capa_report(data, site_name)
            filename = f"capa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'contractors':
            data = scope_qs(Contractor.objects.all()).order_by('name')
            buffer = pdf_gen.generate_contractors_report(data, site_name)
            filename = f"contractors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'ccv':
            data = scope_qs(CCVCriticalControlVerification.objects.all()).order_by('-assessment_datetime')
            buffer = pdf_gen.generate_ccv_report(data, site_name)
            filename = f"ccv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'pto_chemicals':
            data = scope_qs(PTOChemicalHazardousSubstance.objects.all()).order_by('-id')
            buffer = pdf_gen.generate_pto_chemicals_report(data, site_name)
            filename = f"pto_chemicals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'medical_profiles':
            data = scope_qs(MedicalProfile.objects.all()).order_by('employee__name')
            buffer = pdf_gen.generate_medical_profiles_report(data, site_name)
            filename = f"medical_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        elif module_name == 'medical_assessments':
            data = scope_qs(MedicalAssessment.objects.all()).order_by('-assessment_date')
            buffer = pdf_gen.generate_medical_assessments_report(data, site_name)
            filename = f"medical_assessments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        else:
            messages.error(request, f'Export not available for {module_name}')
            return redirect('home')

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('home')


def incidents_page(request):
    return _module_page(
        request,
        model=Incident,
        form_class=IncidentForm,
        title='Incident Reporting',
        description='Capture incident details without using admin pages.',
        route_name='incidents_page',
        auto_user_fields=['reported_by'],
        list_fields=[
            ('site_project', 'Site'),
            ('title', 'Title'),
            ('incident_category', 'Category'),
            ('severity', 'Severity'),
            ('location', 'Location'),
            ('reportable_to_regulator', 'Regulator Reportable'),
        ],
        form_sections=[
            ('Incident Overview', ['site', 'title', 'incident_category', 'severity', 'location', 'event_datetime']),
            ('People and Impact', ['affected_person_name', 'employment_type', 'department', 'crew', 'injury_type', 'body_part_affected', 'lost_time_days', 'treatment_level']),
            ('Investigation', ['description', 'witnesses', 'immediate_action_taken', 'root_cause', 'contributing_factors', 'corrective_actions', 'action_owner', 'investigation_lead', 'investigation_completion_date']),
            ('Compliance and Evidence', ['reportable_to_regulator', 'regulator_notification_date', 'closeout_verification', 'lessons_learned', 'image', 'incident_file']),
        ],
    )


def jsa_page(request):
    edit_id = request.GET.get('edit') or request.POST.get('edit_id')
    step_lookup = {}
    edit_jsa = None
    if getattr(request, 'current_tenant', None) and edit_id:
        edit_jsa = JSA.objects.filter(tenant=request.current_tenant, id=edit_id).first()
        if edit_jsa:
            step_lookup = {step.step_number: step for step in edit_jsa.steps.all()}

    def build_people_rows(entries, total_rows):
        rows = []
        entries = entries or []
        for index in range(total_rows):
            entry = entries[index] if index < len(entries) else {}
            rows.append({
                'row_number': index + 1,
                'date': entry.get('date', ''),
                'name': entry.get('name', ''),
                'id_no': entry.get('id_no', ''),
                'signature': entry.get('signature', ''),
            })
        return rows

    def parse_people_rows(post_request, prefix, total_rows):
        rows = []
        for index in range(1, total_rows + 1):
            row = {
                'date': post_request.POST.get(f'{prefix}_{index}_date', '').strip(),
                'name': post_request.POST.get(f'{prefix}_{index}_name', '').strip(),
                'id_no': post_request.POST.get(f'{prefix}_{index}_id_no', '').strip(),
                'signature': post_request.POST.get(f'{prefix}_{index}_signature', '').strip(),
            }
            if any(row.values()):
                rows.append(row)
        return rows

    def save_jsa_steps(post_request, jsa_instance):
        step_rows = []
        for index in range(1, 9):
            row = {
                'step_number': index,
                'job_step': post_request.POST.get(f'jsa_step_{index}_job_step', '').strip(),
                'job_step_hazard': post_request.POST.get(f'jsa_step_{index}_job_step_hazard', '').strip(),
                'current_controls': post_request.POST.get(f'jsa_step_{index}_current_controls', '').strip(),
                'evaluation_control_type': post_request.POST.get(f'jsa_step_{index}_evaluation_control_type', '').strip(),
                'likelihood_before': post_request.POST.get(f'jsa_step_{index}_likelihood_before', '').strip(),
                'consequence_before': post_request.POST.get(f'jsa_step_{index}_consequence_before', '').strip(),
                'residual_risk_before': post_request.POST.get(f'jsa_step_{index}_residual_risk_before', '').strip(),
                'required_additional_actions': post_request.POST.get(f'jsa_step_{index}_required_additional_actions', '').strip(),
                'likelihood_after': post_request.POST.get(f'jsa_step_{index}_likelihood_after', '').strip(),
                'consequence_after': post_request.POST.get(f'jsa_step_{index}_consequence_after', '').strip(),
                'residual_risk_after': post_request.POST.get(f'jsa_step_{index}_residual_risk_after', '').strip(),
            }
            if any(value for key, value in row.items() if key != 'step_number'):
                step_rows.append(row)

        jsa_instance.steps.all().delete()
        if step_rows:
            jsa_steps_to_create = []
            for row in step_rows:
                step = JSAStep(jsa=jsa_instance, **row)
                if hasattr(step, 'tenant'):
                    step.tenant = jsa_instance.tenant
                jsa_steps_to_create.append(step)
            JSAStep.objects.bulk_create(jsa_steps_to_create)

        jsa_instance.team_member_acknowledgements = parse_people_rows(post_request, 'jsa_team_member', 10)
        jsa_instance.daily_review_log = parse_people_rows(post_request, 'jsa_daily_review', 10)
        jsa_instance.save(update_fields=['team_member_acknowledgements', 'daily_review_log'])

    step_choice_map = {
        'hierarchy': JSAStep.HIERARCHY_CHOICES,
        'risk_levels': JSAStep.RISK_LEVEL_CHOICES,
    }

    return _module_page(
        request,
        model=JSA,
        form_class=JSAForm,
        title='Job Safety Analysis (FM0464)',
        description='Create comprehensive job safety analyses with hazard controls and risk assessment.',
        route_name='jsa_page',
        auto_user_fields=['performed_by'],
        list_fields=[
            ('jsa_number', 'JSA #'),
            ('job_task', 'Job Task'),
            ('plant_area', 'Plant/Area'),
            ('assessment_date', 'Date'),
            ('signed', 'Signed'),
        ],
        form_sections=[
            ('Document Metadata', ['document_reference', 'revision_number', 'total_pages', 'date_of_issue', 'date_of_next_review']),
            ('JSA Summary', ['site', 'jsa_number', 'work_order_number', 'job_task', 'plant_area', 'location', 'assessment_date']),
            ('Supervisors', ['senior_supervisor_name', 'senior_supervisor_signature', 'work_group_supervisor_name', 'work_group_supervisor_signature']),
            ('Permits Required', ['permit_to_work', 'excavation_permit', 'hot_work_permit', 'hv_electrical_isolation_permit', 'hv_vicinity_permit', 'radiation_work_permit', 'working_at_height_permit', 'chemical_pump_pipe_permit', 'confined_space_permit', 'other_permit', 'other_permit_description']),
            ('PPE & Equipment', ['additional_ppe_requirements', 'special_tools_equipment']),
            ('Fatality Prevention Commitments', ['fpc_competent_capable_controlled', 'fpc_identify_control_hazards', 'fpc_safe_lifting_operations', 'fpc_drive_safely', 'fpc_energy_isolation', 'fpc_confined_space_entry', 'fpc_work_at_heights', 'fpc_surface_underground', 'fpc_equipment_safeguards', 'fpc_chemicals_hazardous_substances']),
            ('Hazardous Materials & Emergency Equipment', ['hazardous_materials', 'fire_emergency_equipment']),
            ('Supporting Documents', ['supports_lift_plan', 'supports_sds', 'supports_emergency_action_plan', 'safe_work_procedure_possible']),
            ('Potential Hazards', ['hazard_flora_fauna', 'hazard_electrical', 'hazard_mechanical', 'hazard_chemical', 'hazard_dust_fume', 'hazard_soil_erosion', 'hazard_stored_energy', 'hazard_live_equipment', 'hazard_manual_handling', 'hazard_radiation', 'hazard_spills_water', 'hazard_falling_equipment', 'hazard_noise', 'hazard_ignition_sources', 'hazard_spills_ground', 'hazard_fire_explosives', 'hazard_light_dark', 'hazard_rock_falls', 'hazard_concealed_services']),
            ('Weather Conditions', ['weather_rain', 'weather_thunder', 'weather_lightning', 'weather_extreme_temperatures', 'weather_other', 'weather_other_description']),
            ('Acknowledgements', ['senior_supervisor_acknowledgement']),
            ('Approval and Review', ['pre_job_briefing_completed', 'supervisor_approval', 'signed', 'valid_from', 'valid_to', 'jsa_file']),
        ],
        post_save_callback=save_jsa_steps,
        extra_context={
            'jsa_step_choice_map': step_choice_map,
            'jsa_step_rows': [
                {
                    'step_number': index,
                    'job_step': getattr(step_lookup.get(index), 'job_step', ''),
                    'job_step_hazard': getattr(step_lookup.get(index), 'job_step_hazard', ''),
                    'current_controls': getattr(step_lookup.get(index), 'current_controls', ''),
                    'evaluation_control_type': getattr(step_lookup.get(index), 'evaluation_control_type', ''),
                    'likelihood_before': getattr(step_lookup.get(index), 'likelihood_before', ''),
                    'consequence_before': getattr(step_lookup.get(index), 'consequence_before', ''),
                    'residual_risk_before': getattr(step_lookup.get(index), 'residual_risk_before', ''),
                    'required_additional_actions': getattr(step_lookup.get(index), 'required_additional_actions', ''),
                    'likelihood_after': getattr(step_lookup.get(index), 'likelihood_after', ''),
                    'consequence_after': getattr(step_lookup.get(index), 'consequence_after', ''),
                    'residual_risk_after': getattr(step_lookup.get(index), 'residual_risk_after', ''),
                }
                for index in range(1, 9)
            ],
            'jsa_team_rows': build_people_rows(getattr(edit_jsa, 'team_member_acknowledgements', []), 10),
            'jsa_review_rows': build_people_rows(getattr(edit_jsa, 'daily_review_log', []), 10),
        },
    )


def fra_page(request):
    return _module_page(
        request,
        model=FRA,
        form_class=FRAForm,
        title='FRA Entries',
        description='Create formal risk assessments from the front-end.',
        route_name='fra_page',
        auto_user_fields=['assessed_by'],
        list_fields=[
            ('activity', 'Activity'),
            ('hazard_category', 'Hazard Category'),
            ('risk_level', 'Risk Level'),
            ('initial_risk_score', 'Initial Score'),
            ('residual_risk_score', 'Residual Score'),
        ],
        form_sections=[
            ('FRA Details', ['site', 'activity', 'location', 'hazard_category', 'persons_at_risk', 'risk_identified']),
            ('Risk Scoring', ['likelihood', 'severity_score', 'initial_risk_score', 'residual_likelihood', 'residual_severity', 'residual_risk_score', 'acceptable']),
            ('Control Measures', ['existing_controls', 'additional_controls', 'control_measures', 'review_frequency', 'approver', 'fra_file']),
        ],
    )


def flra_page(request):
    return _module_page(
        request,
        model=FLRA,
        form_class=FLRAForm,
        title='FLRA Entries',
        description='Capture field level risk assessments by site and shift.',
        route_name='flra_page',
        auto_user_fields=['assessed_by'],
        list_fields=[
            ('task_description', 'Task'),
            ('location', 'Location'),
            ('selected_employee_names', 'Employees'),
            ('shift', 'Shift'),
            ('energy_isolation_confirmed', 'Isolation Confirmed'),
            ('escalation_required', 'Escalation'),
        ],
        form_sections=[
            ('Task Context', ['site', 'task_description', 'location', 'shift', 'selected_employees', 'crew', 'weather_conditions']),
            ('Operational Conditions', ['simultaneous_operations', 'energy_isolation_confirmed', 'stop_work_authority_used', 'dynamic_changes_noticed']),
            ('Controls and Sign-off', ['identified_hazards', 'control_measures', 'additional_controls_added', 'worker_signatures', 'supervisor_signature', 'escalation_required', 'flra_file']),
        ],
    )


def observations_page(request):
    return _module_page(
        request,
        model=Observation,
        form_class=ObservationForm,
        title='Observations',
        description='Log PTO and CCV observations in one user page.',
        route_name='observations_page',
        auto_user_fields=['observed_by'],
        list_fields=[
            ('task', 'Task'),
            ('observation_type', 'Type'),
            ('follow_up_required', 'Follow-up'),
            ('date', 'Date'),
        ],
        form_sections=[
            ('Observation Details', ['site', 'task', 'observation_type', 'controls_verified', 'findings', 'follow_up_required', 'attachments', 'file']),
        ],
    )


def pto_chemicals_page(request):
    pto_field_map = {
        'chemicals_hazardous_substances': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_08_compliant'],
        'work_at_heights': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_07_compliant'],
        'energy_isolation': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_08_compliant'],
        'equipment_safeguards_protective_devices': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_06_compliant'],
        'identify_control_hazards': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_05_compliant'],
        'mobile_equipment_light_vehicles': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_08_compliant'],
        'competent_capable_controlled': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_08_compliant'],
        'safe_operation_forklifts': ['observer_name', 'employee_name', 'shift_mining', 'reason_for_observation', 'step_01_compliant', 'step_23_compliant'],
    }

    pto_step_map = {
        'chemicals_hazardous_substances': [
            'Handle or work around hazardous substances if authorized to do so, and in accordance with prescribed controls.',
            'Always obtain, read, understand and follow the instructions on the Safety Data Sheet (SDS) for the hazardous substance that you will be handling.',
            'Never handle or use chemicals or hazardous substances if you have not been trained and authorized in their use, handling, storage and disposal.',
            'Ensure a hot work permit is issued and use continuous LEL gas monitoring when introducing an ignition source to work areas where flammable materials may be present.',
            'Wear appropriate personal gas detection monitors when required and leave the work area immediately if the alarm begins to sound.',
            'Only access explosives storage areas and/or handle explosives if authorized to do so.',
            'Always evacuate the blast danger zone before blasting and check blasted material for possible misfires before loading/excavating.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
        'work_at_heights': [
            'Protect self and others against a fall when working at heights (1.8m or more) by always maintaining 100 percent tie-off.',
            'Ensure a fall protection plan and a rescue plan is in place and communicated to all affected personnel.',
            'Use a certified fall protection system with full body harness, lanyard and proper anchor points when working at heights.',
            'Conduct pre-use inspections of fall protection system components and immediately remove and destroy damaged items.',
            'Ensure all tools and loose objects are stored and used in a secure manner to prevent dropped objects.',
            'Ensure areas below elevated work in progress are controlled (for example barricades and/or sentries) to prevent pedestrian access.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
        'energy_isolation': [
            'Verify effective equipment energy isolations and remain out of the line of fire.',
            'Identify all energy sources including electrical, mechanical, hydraulic, pneumatic, chemical, nuclear, kinetic and gravitational.',
            'Ensure all energized sources are properly isolated and any stored energy is discharged prior to starting work.',
            'Secure using your personal lock and tags any isolation point that could inadvertently be returned to an energized state during work.',
            'Verify the isolation effectiveness (bump test for zero energy state) prior to starting work.',
            'Ensure only authorized personnel are permitted to access hazardous energy areas.',
            'Ensure that all guards and safety systems are restored when the work is completed.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
        'equipment_safeguards_protective_devices': [
            'Authorized and qualified personnel alter, bypass, inhibit or remove equipment safeguards and protective devices.',
            'Operate equipment according to manufacturer specifications, with safeguards and protective devices in place.',
            'Disconnect tools when not in use, before servicing, and before changing components or accessories.',
            'Ensure all emergency shutoffs are clearly identified, visible and accessible.',
            'Follow lockout/tagout procedures when required to alter, bypass or inhibit equipment safeguards and protective devices.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
        'identify_control_hazards': [
            'Identify and control hazards to maintain a safe workplace and use the STOP UNSAFE WORK AUTHORITY to keep self and others safe.',
            'Conduct a hazard assessment and implement any required controls prior to the commencement of work.',
            'Communicate, and resume work with any newly identified controls in place to minimize risks As Low As Reasonably Practicable (ALARP).',
            'Recognize when a formal Management of Change (MOC) is needed and notify your supervisor to initiate proper risk assessment, planning and change communication efforts.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
        'mobile_equipment_light_vehicles': [
            'Obey traffic rules, drive to road conditions and avoid distractions while driving.',
            'Ensure vehicle safety devices are in good working order and properly used (for example seat belts, back up alarms, headlights, flags and strobe lights, kill switches).',
            'Do not use your cell phone or other electronic devices (except approved communication radios) when operating a vehicle or equipment.',
            'Secure loads and loose items that could become a projectile with a sudden turn or stop.',
            'Obey posted signage and drive according to road and weather conditions.',
            'Prevent vehicle movement when parking through an appropriate combination of wheel chocks, parking ditches, wheels turned into berms or walls, and equipment GETs lowered into the ground.',
            'Ensure pedestrians stand clear of mobile equipment travel path and operating radius.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
        'safe_operation_forklifts': [
            'Does the operator have appropriate competency to operate a forklift? Check for certification or valid operating permit.',
            'Is the operator of the forklift fit for work (for example not fatigued or medically ill)?',
            'Has the operator completed forklift prestart inspection correctly, and any identified defects rectified before operating the forklift?',
            'Has the operator completed a FLRA and ensured the work area is free from items that may constitute a hazard while the forklift is in operation?',
            'Did the operator correctly sound horns (one horn before starting the engine, two horns before moving forward, and three horns before reversing)?',
            'Is the forklift operator always using the seat belt to keep all body parts inside the driver compartment while operating the forklift?',
            'Is the weight of the load within the Safe Working Load (SWL) of the forklift?',
            'Are the forks inserted as far under the load as possible?',
            'Is the lifted load vertical or tilted backwards, as securely as required?',
            'If pallets containing multiple items are being lifted, are all items securely strapped or contained on the pallet?',
            'Is there any person supporting, working, or walking under suspended load of the forklift?',
            'If the load is high and blocking vision, is the operator driving in reverse?',
            'When approaching a corner, is the operator slowing down and sounding a horn?',
            'Is the operator always giving right of way to pedestrians?',
            'Is the operator driving to road conditions (follow posted speed limits, slow down at cross aisles, sharp curves, ramps, dips, and wet or slippery surfaces)?',
            'Is the forklift turned off with forks lowered to the floor, park brakes set, and key removed from ignition when not in use or left unattended?',
            'Are forks raised and clear off the ground, with mast tilted back slightly as the forklift travels?',
            'Has the area where the forklift is operating been barricaded to restrict access?',
            'Is the operator maintaining three-point contact when mounting or dismounting from the forklift?',
            'If fork extensions are being used, are they approved by a Mechanical Engineer?',
            'If fork extensions are being used, are they secured with a retainer (heel hook, pins, etc.)?',
            'If fork extensions were in use, have they been removed from the forklift immediately after the task?',
            'If not in use, is the forklift parked in a designated area with forks lowered and tilted slightly forward without posing a hazard in walkways or aisles?',
        ],
        'competent_capable_controlled': [
            'Carry out work for which authorized, trained, qualified and fit to perform.',
            'Take personal responsibility for maintaining safe working conditions and for ensuring hazard controls are effective. STOP any job that you believe is unsafe.',
            'Work according to established job instructions, practices and procedures and know what to do in case of emergency.',
            'Obey all signs and barriers, use the right tools and equipment and wear the correct PPE for the task.',
            'Be fit for duty and unaffected by medications, drugs or alcohol and manage fatigue while on the job.',
            'Notify your supervisor if you feel you are not competent or capable of performing work safely.',
            'Notify a supervisor/manager if you are aware of, or reasonably suspect, another worker is not fit for duty.',
            'STOP any work that does not comply with the safety rules, regulations and/or procedures and notify your Supervisor immediately.',
        ],
    }

    pto_meta_map = {
        'chemicals_hazardous_substances': {
            'title': 'CHEMICALS & HAZARDOUS SUBSTANCES FPC PTO',
            'ref': '0623',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
        'work_at_heights': {
            'title': 'WORK AT HEIGHTS FPC PTO',
            'ref': '0632',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
        'energy_isolation': {
            'title': 'ENERGY ISOLATION FPC PTO',
            'ref': '0627',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
        'equipment_safeguards_protective_devices': {
            'title': 'EQUIPMENT SAFEGUARDS & PROTECTIVE DEVICES FPC PTO',
            'ref': '0628',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
        'identify_control_hazards': {
            'title': 'IDENTIFY AND CONTROL HAZARDS FPC PTO',
            'ref': '0629',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
        'mobile_equipment_light_vehicles': {
            'title': 'MOBILE EQUIPMENT AND LIGHT VEHICLES FPC PTO',
            'ref': '0630',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
        'safe_operation_forklifts': {
            'title': 'SAFE OPERATION OF FORKLIFT PTO',
            'ref': '0633',
            'version': '00',
            'authored_by': 'Christopher Mumba',
            'approved_by': 'Jurrius Wessel',
            'date': '23/01/2023',
        },
        'competent_capable_controlled': {
            'title': 'COMPETENT, CAPABLE AND CONTROLLED FPC PTO',
            'ref': '-',
            'version': '00',
            'authored_by': 'E Hinamanjolo',
            'approved_by': 'T Zulu',
            'date': '15/02/2022',
        },
    }

    return _module_page(
        request,
        model=PTOChemicalHazardousSubstance,
        form_class=PTOChemicalHazardousSubstanceForm,
        title='PTO - Chemicals & Hazardous Substances',
        description='Capture all PTO forms from one page by selecting PTO type, then filling required fields.',
        route_name='pto_chemicals_page',
        list_fields=[
            ('pto_type', 'PTO Type'),
            ('employee_name', 'Employee'),
            ('observer_name', 'Observer'),
            ('competency_result', 'Outcome'),
            ('follow_up_pto_recommended', 'Follow-up PTO'),
            ('created_at', 'Created'),
        ],
        form_sections=[
            ('PTO Selection', ['site', 'pto_type']),
            ('Observer Details', ['observer_name', 'observer_employee_id', 'observer_job_title', 'observer_department', 'observer_date', 'observer_signature']),
            ('Employee Details', ['employee_name', 'employee_id', 'employee_job_title', 'employee_department', 'employee_observed_at', 'employee_signature']),
            ('Shift and Observation Context', ['shift_mining', 'shift_other', 'crew_mining', 'crew_other', 'reason_for_observation', 'notification_of_pto']),
            ('Evaluation and Follow-up', ['competency_result', 'forwarded_to_hr', 'follow_up_pto_recommended', 'employee_superintendent_name', 'employee_superintendent_signature']),
            ('Action Plan', ['action_1', 'action_1_responsible', 'action_1_by_when', 'action_2', 'action_2_responsible', 'action_2_by_when', 'action_3', 'action_3_responsible', 'action_3_by_when']),
            ('Standardized Task Steps', ['step_01_compliant', 'step_01_comments', 'step_02_compliant', 'step_02_comments', 'step_03_compliant', 'step_03_comments', 'step_04_compliant', 'step_04_comments', 'step_05_compliant', 'step_05_comments', 'step_06_compliant', 'step_06_comments', 'step_07_compliant', 'step_07_comments', 'step_08_compliant', 'step_08_comments', 'step_09_compliant', 'step_09_comments', 'step_10_compliant', 'step_10_comments', 'step_11_compliant', 'step_11_comments', 'step_12_compliant', 'step_12_comments', 'step_13_compliant', 'step_13_comments', 'step_14_compliant', 'step_14_comments', 'step_15_compliant', 'step_15_comments', 'step_16_compliant', 'step_16_comments', 'step_17_compliant', 'step_17_comments', 'step_18_compliant', 'step_18_comments', 'step_19_compliant', 'step_19_comments', 'step_20_compliant', 'step_20_comments', 'step_21_compliant', 'step_21_comments', 'step_22_compliant', 'step_22_comments', 'step_23_compliant', 'step_23_comments']),
        ],
        extra_context={
            'template_field_map': pto_field_map,
            'template_step_map': pto_step_map,
            'template_meta_map': pto_meta_map,
        },
    )


def ccv_page(request):
    ccv_field_map = {
        'mobile_equipment': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_18_compliant'],
        'rotating_equipment': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_13_compliant'],
        'fall_from_heights': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_22_compliant'],
        'confined_space': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_13_compliant'],
        'fall_of_ground': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_16_compliant'],
        'hazardous_substances_chemicals': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_11_compliant'],
        'stored_energy': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_14_compliant'],
        'lifting': ['assessor_name', 'location', 'department', 'step_01_compliant', 'step_16_compliant'],
    }

    ccv_step_map = {
        'mobile_equipment': [
            'Is the team member alert, rested, and free of distractions?',
            'Is team member aware of and complying with posted speed limits and changing road conditions?',
            'Are electronic devices secured and put away?',
            'Are visibility accessories (for example strobe lights, reflective tape, buggy whip) installed, functional, and maintained?',
            'Are all safety critical items installed and functioning properly prior to operating equipment (for example tires, brakes, steering, horn, cameras, maintenance up-to-date, fatigue monitoring)?',
            'Have all seatbelts been inspected for damage and determined to be in good operable condition and worn correctly?',
            'Has interaction between vehicles and pedestrians been minimized by physical barriers, designated walkways/travel ways, and work area exclusion zones?',
            'In parking and other congested traffic areas, are berms installed and maintained to minimize vehicle interactions?',
            'Are vehicles operating at the required separation distance per Traffic Management Plan?',
            'Do employees avoid entering equipment blind spots unless positive communication is established and equipment is shut down and secured from movement?',
            'Are berms built with competent material to the mid-axle height of the largest vehicle travelling the area to prevent vehicles from falling over the edge or overturning?',
            'Is the vehicle or equipment parked in a designated or segregated parking area?',
            'Are loads and loose items that could become a hazard or risk secured?',
            'Is the park/service brake set, other suitable brakes applied, and the vehicle blocked against movement?',
            'Are radios installed, present, and operational in vehicles/equipment in required areas?',
            'Is positive two-way communication made when passing equipment or entering exclusion zones?',
            'Is the equipment fitted with the appropriate fire suppression system and/or fire extinguisher?',
            'Has the employee inspected the fire suppression system and/or fire extinguisher(s) prior to operation?',
        ],
        'rotating_equipment': [
            'Has the worker been trained and authorized, and does the worker understand the components of working around rotating equipment?',
            'Is guarding and/or a barrier present and does it meet the standard?',
            'If an authorized bypass needs to occur, has communication been made to all affected personnel?',
            'Is the exclusion zone demarcated with the hazard and precautionary actions identified?',
            'Is there an authorized process in place for removal of guards, when necessary, in order to perform live testing?',
            'Is worker clear of potential line of fire situations?',
            'Are there designated covered walkways under conveyor belts?',
            'Are barricades in place where there is the potential for falling objects?',
            'Is the emergency shut-off device visible, accessible, and properly maintained?',
            'If removed, have all guards and safety systems been restored when the work is completed?',
            'Have individuals performed effective mechanical blocking, and are the mechanical blocks approved and safe for use?',
            'Are jacks and blocks designed, adequate, and positioned correctly for the task?',
            'During maintenance, are the articulation and bed locks in place to block against movement?',
        ],
        'fall_from_heights': [
            'Have you completed a risk assessment prior to starting the working at heights job?',
            'Has the Fall from Heights permit been completed, signed off, and implemented correctly for non-routine tasks, and are safety helmets secured using a chinstrap?',
            'Are all objects, tools and equipment secured with an approved tether device to prevent them from falling?',
            'If required, are exclusion zones established on lower levels (for example barricades, barriers, guards) to prevent individuals from being struck by a falling object?',
            'Is there a physical barrier or barricade with signage in place that will mitigate the risk?',
            'Is anyone working alone?',
            'Has the worker been trained and authorized, and does the worker understand the components of fall protection?',
            'Have the key components been maintained and inspected by the worker prior to use?',
            'Was the clearance fall distance calculated prior to starting work?',
            'While using a Fall Restraint System, is the anchor point capable of withstanding the expected force?',
            'Is the proper fall protection system being used for the task (for example prevention, restraint, arrest, full body harness, proper length shock-absorbing lanyard, and trauma straps)?',
            'Are Fall Arrest Systems attached to the harness D-ring in the middle of the back and is the tie off able to withstand 22.5kN or 5,000 pounds of force?',
            'Where the work method requires persons to detach and re-attach at height, is a dual fall arrest or dual fall restraint system being used so at least one connection point is always maintained?',
            'Are work platforms tagged correctly, inspected, certified, maintained, and in proper working condition suitable for the task?',
            'Is the aerial lift, scissor lift, or other elevated work platform equipped with secured floors, guardrails, and toe-boards to prevent items from falling to lower surfaces?',
            'Has the ladder been inspected prior to use and is it the correct height and material for the job?',
            'Do work platforms appear free from signs of overloading and in good working order?',
            'Are workers on the mobile work platform properly protected with a fall prevention or fall arrest system?',
            'Are weather and terrain conditions acceptable to keep the working platform stable?',
            'Do employees have means to summon help or self-rescue while using fall protection?',
            'Is more than one employee working on the task while using fall protection, and are any employees working alone?',
            'Is a fall protection plan and a rescue plan in place and communicated to all affected personnel?',
        ],
        'confined_space': [
            'Has the Confined Space Permit been completed and implemented correctly?',
            'Is the attendant/spotter present while confined space is occupied?',
            'Is the confined space attendant/spotter maintaining a register of people entering and exiting?',
            'Are all confined space entry and exit locations guarded or barricaded and labeled to prevent unauthorized entry?',
            'Is there effective communication between the confined space spotter/attendant and entrants?',
            'Has a risk assessment been conducted and have proper controls been established for each risk identified?',
            'Has the appropriate gas monitor been selected, pre-use bump tested, and validly calibrated for use based on the identified hazards?',
            'Is the atmosphere being tested, results documented per confined space permit, and appropriate controls implemented as per plan?',
            'Have all sources of energy been identified, isolated by each occupant\'s personal lock, tagged, tried out, and in a zero-energy state?',
            'Do attendant and entrants have means to summon help and ability to self-rescue?',
            'Are there at least two employees (no one working alone) while in the confined space?',
            'Is the rescue plan and all required gear in place?',
            'Do the attendants and entrants understand events that could trigger an evacuation or rescue and know how to initiate emergency response?',
        ],
        'fall_of_ground': [
            'Has the worker been trained and authorized, and does the worker understand the components of Fall of Ground activity?',
            'Is the worker familiar with the FRA and critical controls?',
            'Have identified ground control hazards and mitigations been communicated from geotechnical to supervisors and frontline operations between shifts?',
            'Are the highwalls scaled and free of debris, and are the catch benches adequate?',
            'Are team members maintaining loading faces at a safe working height/angle and avoiding positions between mining equipment and the face?',
            'Is the highwall/stockpile built and maintained to plan design?',
            'Are team members entering restricted areas without permission (for example base and crest of highwalls/stockpiles, benches, mining faces, dumps and blasting areas)?',
            'Is the surface water control installed and maintained according to design and clear of obstructions (for example storm water drains)?',
            'Is there a barrier (for example berm or jersey barriers) to stop people and mobile equipment from entering areas where material can fall from a high wall/excavation?',
            'Are restricted areas demarcated and signed, and is employee entry prohibited without authorization?',
            'Are employees kept out of equipment swing radius or blind spots unless positive communication is established, equipment is shut down, and implements are lowered to the ground?',
            'Do installed trenching controls meet or exceed Excavation and Trenching Standard requirements (for example shoring, sloping, benching designs, or hydro excavating)?',
            'Is a ground disturbance/dig permit at the work site and filled out correctly?',
            'Do installed trenching controls meet or exceed Excavation and Trenching Standard requirements for geotechnical inspection and monitoring systems?',
            'Is a ground disturbance/dig permit at the work site and filled out correctly for geotechnical inspection and monitoring systems?',
            'Do employees understand the emergency procedures (for example seismic, primary/secondary escape)?',
        ],
        'hazardous_substances_chemicals': [
            'Has the worker been trained and authorized, and does the worker understand the components of working with hazardous materials?',
            'Do employees understand the hazards associated with the chemical(s) they will be handling or potentially exposed to (for example health hazards, chemical reactivity, flammability)?',
            'Do employees know where to locate the Safety Data Sheets (SDS)?',
            'Are employees wearing the correct type of PPE for the task being performed?',
            'Do team members know and understand the procedure to follow when unknown substance is found?',
            'Is the chemical compatible with the containers in which it is transferred/stored (for example leaks or containment)?',
            'Are containers/pipes appropriately labeled and clearly legible, and where applicable is the direction of flow identified?',
            'Is the transfer/handling area easily accessible with proper containment measures in place?',
            'Have the contents of the delivery truck been verified, and is the delivery driver following safe loading/unloading practices?',
            'Are hazardous substances adequately stored and segregated based on SDS storage and segregation requirements?',
            'Are pipes or other distribution systems used for hazardous substances clearly identified?',
        ],
        'stored_energy': [
            'Has the worker been trained and authorized, and does the worker understand the components of energy isolation?',
            'Have all energy sources been identified, isolated, and de-energized?',
            'Have all isolation points been accounted for?',
            'Are workers using the appropriate locks/tags for the task performed?',
            'Have locks, tags, and other isolation devices been installed so they cannot be bypassed or defeated?',
            'Has the tryout step been completed and has zero energy been verified?',
            'Has the tryout step been completed and has zero energy been verified?',
            'Have all required employees locked out?',
            'Have locks, tags, and other isolation devices been installed so they cannot be bypassed or defeated?',
            'Have all required employees locked out?',
            'Are workers using the appropriate locks/tags for the task performed?',
            'Are guards, barriers, and barricades properly installed to protect personnel from uncontrolled energy release?',
            'Are deadman switches, emergency stops, and pull cords confirmed as functional prior to work commencing?',
            'Does the work plan address reinstallation of guards, barriers, and barricades prior to return to service?',
        ],
        'lifting': [
            'Has the worker been trained and authorized, and does the worker understand the lifting operations?',
            'Does the rigger have knowledge, training and competence in rigging and understand their classification according to the type of load and criticality of the manoeuvres, safe rigging practices, signalling and equipment inspection?',
            'Is there an approved and signed-off Lift Plan available for the operation?',
            'Has a load analysis been completed and documented?',
            'Are all safety critical items installed and functioning properly prior to operating equipment (for example two-way radio, seatbelt, cameras, maintenance up to date)?',
            'Have exclusion zones been clearly barricaded and demarcated?',
            'Are there procedures in place to ensure no unauthorized personnel enter the exclusion zone?',
            'Is all lifting equipment certified, inspected, and in good working condition?',
            'Are lifting accessories (for example slings, shackles, ropes) inspected/certified and undamaged?',
            'Has the employee inspected the fire suppression system and/or fire extinguisher(s) prior to operation?',
            'Is there a clear communication protocol in place for the lifting operation?',
            'Is positive communication made when passing equipment or when entering exclusion zones?',
            'Is there a designated person-in-charge (PIC) overseeing the operation?',
            'Have all people involved in or affected by the lift been briefed?',
            'Has the area been checked for overhead electrical lines, and have measures been taken to prevent electrocution?',
            'Have pre-lift checks been performed to identify and mitigate potential hazards?',
        ],
    }

    ccv_meta_map = {
        'mobile_equipment': {
            'title': 'MOBILE EQUIPMENT CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0635',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'rotating_equipment': {
            'title': 'ROTATING EQUIPMENT CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0638',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'fall_from_heights': {
            'title': 'FALL FROM HEIGHTS CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0632',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'confined_space': {
            'title': 'CONFINED SPACE CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0633',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'fall_of_ground': {
            'title': 'FALL OF GROUND CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0634',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'hazardous_substances_chemicals': {
            'title': 'HAZARDOUS SUBSTANCES AND CHEMICALS CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0636',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'stored_energy': {
            'title': 'STORED ENERGY CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0637',
            'version': '01',
            'date_of_issue': '05/15/2024',
            'date_of_next_review': '05/14/2026',
        },
        'lifting': {
            'title': 'LIFTING CRITICAL CONTROL VERIFICATION FORM',
            'ref': 'FM0737',
            'version': '01',
            'date_of_issue': '12/12/2024',
            'date_of_next_review': '12/12/2026',
        },
    }

    return _module_page(
        request,
        model=CCVCriticalControlVerification,
        form_class=CCVCriticalControlVerificationForm,
        title='CCV - Critical Control Verification',
        description='Capture CCV forms from one page by selecting CCV type, then completing the relevant controls.',
        route_name='ccv_page',
        list_fields=[
            ('ccv_type', 'CCV Type'),
            ('assessor_name', 'Assessor'),
            ('location', 'Location'),
            ('department', 'Department'),
            ('created_at', 'Created'),
        ],
        form_sections=[
            ('CCV Selection', ['site', 'ccv_type']),
            ('Assessment Header', ['assessor_name', 'assessment_datetime', 'location', 'department', 'section']),
            ('Critical Control Performance Requirements', ['step_01_compliant', 'step_01_comments', 'step_02_compliant', 'step_02_comments', 'step_03_compliant', 'step_03_comments', 'step_04_compliant', 'step_04_comments', 'step_05_compliant', 'step_05_comments', 'step_06_compliant', 'step_06_comments', 'step_07_compliant', 'step_07_comments', 'step_08_compliant', 'step_08_comments', 'step_09_compliant', 'step_09_comments', 'step_10_compliant', 'step_10_comments', 'step_11_compliant', 'step_11_comments', 'step_12_compliant', 'step_12_comments', 'step_13_compliant', 'step_13_comments', 'step_14_compliant', 'step_14_comments', 'step_15_compliant', 'step_15_comments', 'step_16_compliant', 'step_16_comments', 'step_17_compliant', 'step_17_comments', 'step_18_compliant', 'step_18_comments', 'step_19_compliant', 'step_19_comments', 'step_20_compliant', 'step_20_comments', 'step_21_compliant', 'step_21_comments', 'step_22_compliant', 'step_22_comments', 'step_23_compliant', 'step_23_comments']),
            ('Recommendations', ['action_1', 'action_1_responsible', 'action_1_due_date', 'action_2', 'action_2_responsible', 'action_2_due_date', 'action_3', 'action_3_responsible', 'action_3_due_date']),
        ],
        extra_context={
            'template_field_map': ccv_field_map,
            'template_step_map': ccv_step_map,
            'template_meta_map': ccv_meta_map,
        },
    )


def checklists_page(request):
    checklist_field_map = {
        'Daily': [
            'site', 'checklist_title', 'inspection_area', 'date_completed',
            'ppe_inspection', 'fire_safety_check', 'housekeeping_checked', 'emergency_exits_clear', 'safety_signage_visible',
            'step_01_compliant', 'step_01_comments', 'step_02_compliant', 'step_02_comments',
            'step_03_compliant', 'step_03_comments', 'step_04_compliant', 'step_04_comments',
            'step_05_compliant', 'step_05_comments', 'step_06_compliant', 'step_06_comments',
            'step_07_compliant', 'step_07_comments', 'step_08_compliant', 'step_08_comments',
            'step_09_compliant', 'step_09_comments', 'step_10_compliant', 'step_10_comments',
            'step_11_compliant', 'step_11_comments', 'step_12_compliant', 'step_12_comments',
            'step_13_compliant', 'step_13_comments', 'step_14_compliant', 'step_14_comments',
            'step_15_compliant', 'step_15_comments',
            'findings', 'actions_required', 'operational_status', 'comments',
        ],
        'Weekly': [
            'site', 'checklist_title', 'inspection_area', 'date_completed',
            'ppe_inspection', 'fire_safety_check', 'first_aid_kit_stocked', 'emergency_exits_clear', 'safety_signage_visible', 'housekeeping_checked', 'equipment_condition',
            'step_01_compliant', 'step_01_comments', 'step_02_compliant', 'step_02_comments',
            'step_03_compliant', 'step_03_comments', 'step_04_compliant', 'step_04_comments',
            'step_05_compliant', 'step_05_comments', 'step_06_compliant', 'step_06_comments',
            'step_07_compliant', 'step_07_comments', 'step_08_compliant', 'step_08_comments',
            'step_09_compliant', 'step_09_comments', 'step_10_compliant', 'step_10_comments',
            'step_11_compliant', 'step_11_comments', 'step_12_compliant', 'step_12_comments',
            'step_13_compliant', 'step_13_comments', 'step_14_compliant', 'step_14_comments',
            'step_15_compliant', 'step_15_comments',
            'findings', 'actions_required', 'operational_status', 'comments',
        ],
        'Monthly': ['site', 'inspection_area', 'equipment_id', 'equipment_condition', 'first_aid_kit_stocked', 'actions_required', 'next_due_date'],
        'Mobile Equipment': ['site', 'checklist_title', 'equipment_id', 'inspection_area', 'operator_name', 'operator_signature', 'deviation_problem', 'deviation_reported_to', 'deviation_action_taken', 'comments', 'operational_status'],
        'Lighting Tower': ['site', 'drill_rig_number', 'lighting_tower_number', 'serial_number', 'step_01_compliant', 'step_29_compliant', 'operational_status'],
        'Drilling Machine Surface': ['site', 'company_name', 'area_name', 'operator_name', 'supervisor_name', 'drill_rig_number', 'step_01_compliant', 'step_47_compliant', 'operational_status'],
        'Environmental': ['site', 'inspection_area', 'checklist_title', 'housekeeping_checked', 'step_01_compliant', 'step_25_compliant', 'findings', 'actions_required', 'operational_status'],
        'Generator': ['site', 'equipment_id', 'inspection_area', 'equipment_condition', 'fire_safety_check', 'next_due_date', 'operational_status'],
        'Other Operational': ['site', 'checklist_title', 'equipment_id', 'inspection_area', 'findings', 'actions_required', 'comments'],
    }

    checklist_step_map = {
        'Daily': [
            'Permit to Work (PTW) reviewed and signed for all high-risk activities.',
            'Hazard identification (HIRA) completed for the work area.',
            'Any near-miss or incident occurred / reported today?',
            'Toolbox talk conducted at shift start.',
            'Emergency equipment (fire extinguishers, first aid kit) inspected and serviceable.',
            'Visitor / contractor site induction completed where applicable.',
            'Area risk assessment reviewed and communicated to all team members.',
            'Shift handover safety briefing completed.',
            'Communication channels (radio / phone) confirmed operational.',
            'Environmental conditions (weather, visibility, ground) assessed and acceptable.',
            'Traffic management plan in place and communicated.',
            'Isolation / Lockout-Tagout (LOTO) procedures applied where required.',
            'Working-at-height equipment inspected and in service.',
            'Confined space entry permit in place where required.',
            'End-of-day site secured and equipment properly stored.',
        ],
        'Weekly': [
            'Management / supervisor safety walk conducted and documented.',
            'Legal and compliance register reviewed for any updates.',
            'CAPA actions reviewed and progress updated.',
            "Previous week's findings and action items closed out.",
            'Safe man-hours for the week logged and verified.',
            'Weekly toolbox talk topic selected, material prepared, and delivered.',
            'Training and competency records reviewed and updated.',
            'Incident and near-miss register reviewed and trend analysed.',
            'Contractor safety files reviewed and current.',
            'Emergency response drill scheduled or conducted.',
            'Equipment maintenance records checked and current.',
            'Environmental compliance checks completed.',
            'Safety notice board updated with current information.',
            'OHS objectives and KPI data collected and reviewed.',
            'High-risk activities for the following week identified and planned.',
        ],
        'Mobile Equipment': [
            'Body work and general condition.',
            '*Wheels (tyres/rims).',
            '*Windscreen and all windows.',
            '*Wipers.',
            '*License disc.',
            '*Rear view and side mirrors.',
            '*Headlights, tail lights, brake lights and indicators.',
            '*Number plates.',
            '*Amber flashing light (when prescribed).',
            '*Buggy whip holder (when prescribed).',
            'Reflective yellow/red strips.',
            '*Roll over bars (LDVs, when prescribed).',
            '*Radiator water.',
            '*Battery condition, connections and water.',
            '*Oil level.',
            '*Brake fluid level.',
            '*Lubricant leaks.',
            'Seats.',
            '*Instrument panel - all instruments working.',
            '*Steering wheel and test steering.',
            'Hooter.',
            '*Reverse hooter (when prescribed).',
            '*Rear view mirror.',
            '*Seat belts.',
            '*Handbrake.',
            '*Footbrake and test brakes.',
            'Spare wheel.',
            'Jack and wheel spanner.',
            '*Emergency triangles.',
            'First aid kit (if applicable).',
            '*Stop blocks (operational vehicles).',
            '*Fire extinguisher (operational vehicle).',
        ],
        'Lighting Tower': [
            'Yellow door Assy condition.',
            'Mudguard condition.',
            'Lifting Jack top wind condition.',
            'Lifting jack side wind drawbar condition.',
            'Mast Assy condition.',
            'Outlet panel condition.',
            'Wheel/Rim condition.',
            'Emergency stop bottom condition.',
            'Roof Assy condition.',
            'Radiator coolant level.',
            'Battery and terminals condition.',
            'Oil level.',
            'Lubricant leaks.',
            'Diesel level.',
            'Diesel tank condition.',
            'Control panel condition.',
            'Water pump condition.',
            'Oil dipstick condition.',
            'Hour meter condition.',
            'Fuel pump Assy condition.',
            'Start motor condition.',
            'Alternator belt condition.',
            'Fan Assy condition.',
            'LED condition.',
            'Led floodlight condition.',
            'Driver condition.',
            'Coil cord condition.',
            'Winch RBW Assy condition.',
            'Last Service.',
        ],
        'Drilling Machine Surface': [
            'Structure Condition',
            'Guide Rod Condition',
            'Main Which Pulley Condition',
            'Main Hosting Pulley Condition',
            'Wire Line Pulley Condition',
            'Support Leg Condition',
            'Main Cylinder Condition',
            'Slides Condition',
            'Light Condition',
            'Gauges Condition',
            'Levers Condition',
            'Emergency Stop Bottom Condition',
            'RCS (Rig Control System) Condition',
            'Bottom Light Condition',
            'Ignition Switch Condition',
            'Coolant Level',
            'Engine Oil Level',
            'Hydraulic Oil Level',
            'Fuel Level',
            'Leakages',
            'Batteries Condition',
            'Service Record',
            'Rod Clamp Condition',
            'Chuck Jaw Condition',
            'Platform Condition',
            'Fire Suppression Condition',
            'Fire Extinguisher Condition',
            'Beacon Condition',
            'Mud Mixer Condition',
            'Crawlers Condition',
            'Critical Grease Points',
            'Hydraulic Jacks Condition',
            'Main Hoist System Condition',
            'Wire-Line System Condition',
            'Rotation Unit Condition',
            'Gear Oil Level',
            'Hydraulic Oil Cooler Condition',
            'Relief Pressure Condition',
            'Water Pump R35 Condition',
            'Pipe Wrenches Condition',
            'Inner Tube Spanner Condition',
            'Head Assembly Condition',
            'Overshot Assembly Condition',
            'Water Swivel Condition',
            'Hosting Plug Condition',
            'Camera Survey Condition',
            'Orientation Tool Condition',
        ],
        'Environmental': [
            'Environmental permits and license conditions for this work area are current and available.',
            'Applicable environmental legal requirements have been identified for this task/activity.',
            'Environmental aspects and risks were reviewed before starting work.',
            'Sensitive receptors (waterways, drains, nearby community, protected zones) are identified and marked.',
            'Waste segregation is correctly applied at source (general, recyclable, hazardous).',
            'Waste bins/containers are labeled, covered, and not overflowing.',
            'Hazardous waste storage is bunded, secure, and protected from rain/wind.',
            'Chemical containers are clearly labeled and stored by compatibility requirements.',
            'Current SDS is available and accessible for all chemicals in use.',
            'Spill kits are present, stocked, and accessible at risk points.',
            'Fuel, oil, and chemical transfer points are checked for leaks before and after use.',
            'Secondary containment (bunds/drip trays) is intact and free from defects.',
            'No visible hydrocarbon or chemical stains indicate uncontrolled releases.',
            'Drain protection controls are in place for high-risk activities.',
            'No contaminated runoff is leaving the work area.',
            'Dust suppression measures are active and effective where needed.',
            'Air emissions/smoke from plant and generators are within acceptable limits.',
            'Noise controls are applied where environmental or health impacts are possible.',
            'Idle time for vehicles/equipment is minimized to reduce emissions.',
            'Housekeeping standards prevent litter, debris spread, and contamination.',
            'Topsoil/erosion/sediment controls are in place where ground disturbance occurs.',
            'Environmental signage and exclusion markings are visible and legible.',
            'Personnel can explain spill/release immediate response steps.',
            'Environmental incidents/near misses are reported and escalated per procedure.',
            'Previous environmental actions are closed out and verified with evidence.',
        ],
    }

    checklist_meta_map = {
        'Daily': {
            'title': 'DAILY SAFETY CHECKLIST (ISO 45001)',
            'ref': 'CHK-DAILY-ISO45001',
            'version': '01',
        },
        'Weekly': {
            'title': 'WEEKLY SAFETY MANAGEMENT REVIEW (ISO 45001)',
            'ref': 'CHK-WEEKLY-ISO45001',
            'version': '01',
        },
        'Monthly': {
            'title': 'MONTHLY SAFETY CHECKLIST',
            'ref': 'CHK-MONTHLY',
            'version': '01',
        },
        'Mobile Equipment': {
            'title': 'MOBILE EQUIPMENT CHECKLIST',
            'ref': 'CHK-LV',
            'version': '01',
        },
        'Lighting Tower': {
            'title': 'LIGHTING TOWER INSPECTION CHECK LIST',
            'document_no': 'LEOS-MAI-INS-02',
            'revision_no': '1.0',
            'effective_date': '19/03/2026',
            'status': 'Current',
        },
        'Drilling Machine Surface': {
            'title': 'DRILLING MACHINE SURFACE INSPECTION CHECK LIST',
            'status': 'Current',
        },
        'Environmental': {
            'title': 'ENVIRONMENTAL CHECKLIST',
            'ref': 'CHK-ENV',
            'version': '01',
        },
        'Generator': {
            'title': 'GENERATOR CHECKLIST',
            'ref': 'CHK-GEN',
            'version': '01',
        },
        'Other Operational': {
            'title': 'OTHER OPERATIONAL CHECKLIST',
            'ref': 'CHK-OTHER',
            'version': '01',
        },
    }

    return _module_page(
        request,
        model=SafetyChecklist,
        form_class=SafetyChecklistForm,
        title='Safety Checklists',
        description='Complete operational checklists including mobile equipment, drilling machine surface, environmental and generator checks.',
        route_name='checklists_page',
        auto_user_fields=['completed_by'],
        list_fields=[
            ('checklist_type', 'Type'),
            ('checklist_title', 'Checklist Title'),
            ('equipment_id', 'Equipment/Asset'),
            ('site', 'Site'),
            ('date_completed', 'Date Completed'),
            ('operational_status', 'Operational Status'),
            ('compliance_score', 'Compliance %'),
        ],
        form_sections=[
            ('Checklist Header', ['site', 'checklist_type', 'checklist_title', 'date_completed', 'equipment_id', 'inspection_area', 'document_number', 'revision_number', 'effective_date', 'document_status', 'company_name', 'area_name', 'operator_name', 'supervisor_name', 'drill_rig_number', 'lighting_tower_number', 'serial_number']),
            ('Inspection Items', ['ppe_inspection', 'fire_safety_check', 'equipment_condition', 'emergency_exits_clear', 'safety_signage_visible', 'first_aid_kit_stocked', 'housekeeping_checked']),
            ('Checklist Inspection Points', ['step_01_compliant', 'step_01_comments', 'step_02_compliant', 'step_02_comments', 'step_03_compliant', 'step_03_comments', 'step_04_compliant', 'step_04_comments', 'step_05_compliant', 'step_05_comments', 'step_06_compliant', 'step_06_comments', 'step_07_compliant', 'step_07_comments', 'step_08_compliant', 'step_08_comments', 'step_09_compliant', 'step_09_comments', 'step_10_compliant', 'step_10_comments', 'step_11_compliant', 'step_11_comments', 'step_12_compliant', 'step_12_comments', 'step_13_compliant', 'step_13_comments', 'step_14_compliant', 'step_14_comments', 'step_15_compliant', 'step_15_comments', 'step_16_compliant', 'step_16_comments', 'step_17_compliant', 'step_17_comments', 'step_18_compliant', 'step_18_comments', 'step_19_compliant', 'step_19_comments', 'step_20_compliant', 'step_20_comments', 'step_21_compliant', 'step_21_comments', 'step_22_compliant', 'step_22_comments', 'step_23_compliant', 'step_23_comments', 'step_24_compliant', 'step_24_comments', 'step_25_compliant', 'step_25_comments', 'step_26_compliant', 'step_26_comments', 'step_27_compliant', 'step_27_comments', 'step_28_compliant', 'step_28_comments', 'step_29_compliant', 'step_29_comments', 'step_30_compliant', 'step_30_comments', 'step_31_compliant', 'step_31_comments', 'step_32_compliant', 'step_32_comments', 'step_33_compliant', 'step_33_comments', 'step_34_compliant', 'step_34_comments', 'step_35_compliant', 'step_35_comments', 'step_36_compliant', 'step_36_comments', 'step_37_compliant', 'step_37_comments', 'step_38_compliant', 'step_38_comments', 'step_39_compliant', 'step_39_comments', 'step_40_compliant', 'step_40_comments', 'step_41_compliant', 'step_41_comments', 'step_42_compliant', 'step_42_comments', 'step_43_compliant', 'step_43_comments', 'step_44_compliant', 'step_44_comments', 'step_45_compliant', 'step_45_comments', 'step_46_compliant', 'step_46_comments', 'step_47_compliant', 'step_47_comments']),
            ('Findings and Actions', ['operational_status', 'findings', 'actions_required', 'verified_by', 'next_due_date']),
            ('Signatures', ['operator_signature', 'site_supervisor_signature', 'maintenance_supervisor_signature']),
            ('Deviation Report', ['deviation_date', 'deviation_problem', 'deviation_reported_to', 'deviation_action_taken']),
            ('Comments and Evidence', ['comments', 'checklist_file']),
        ],
        extra_context={
            'template_field_map': checklist_field_map,
            'template_step_map': checklist_step_map,
            'template_meta_map': checklist_meta_map,
        },
    )


def toolbox_talks_page(request):
    def _sync_attendance(request, instance):
        count = instance.attendee_employees.count()
        ToolboxTalk.objects.filter(pk=instance.pk).update(attendance_count=count)

    return _module_page(
        request,
        model=ToolboxTalk,
        form_class=ToolboxTalkForm,
        title='Toolbox Talks',
        description='Plan and record toolbox talks, hazards discussed, agreed controls, attendance and follow-ups.',
        route_name='toolbox_talks_page',
        auto_user_fields=['conducted_by'],
        post_save_callback=_sync_attendance,
        list_fields=[
            ('title', 'Title'),
            ('talk_date', 'Talk Date'),
            ('site', 'Site'),
            ('facilitator_name', 'Facilitator'),
            ('attendance_count', 'Attendance'),
            ('follow_up_required', 'Follow-up'),
        ],
        form_sections=[
            ('Talk Header', ['site', 'title', 'talk_date', 'facilitator_name', 'department', 'work_group']),
            ('Topic and Risk Discussion', ['topic_details', 'hazards_discussed', 'controls_agreed']),
            ('Attendance', ['attendee_employees', 'attendees']),
            ('Actions and Follow-up', ['action_items', 'follow_up_required', 'follow_up_owner', 'follow_up_due_date']),
            ('Evidence', ['toolbox_file']),
        ],
    )


def employees_page(request):
    return _module_page(
        request,
        model=Employee,
        form_class=EmployeeForm,
        title='Employees',
        description='Manage employee records for the selected tenant.',
        route_name='employees_page',
        user_role_min='supervisor',
        list_fields=[
            ('name', 'Name'),
            ('position', 'Position'),
            ('department', 'Department'),
            ('scope', 'Scope'),
            ('site', 'Site'),
            ('user', 'User Account'),
        ],
        form_sections=[
            ('Identity', ['site', 'name', 'user', 'position', 'department']),
            ('Scope & Expertise', ['scope', 'expert_traits']),
            ('Contacts', ['contact_number', 'emergency_contact', 'employee_file']),
            ('Certifications', ['certifications']),
        ],
    )


def attendance_page(request):
    return _module_page(
        request,
        model=AttendanceRecord,
        form_class=AttendanceRecordForm,
        title='Attendance',
        description='Record daily employee attendance and track man-hours.',
        route_name='attendance_page',
        user_role_min='supervisor',
        list_fields=[
            ('date', 'Date'),
            ('employee', 'Employee'),
            ('site_project', 'Site'),
            ('start_time', 'Start'),
            ('end_time', 'End'),
        ],
        form_sections=[
            ('Attendance Details', ['site_project', 'employee', 'date']),
            ('Times', ['start_time', 'end_time', 'break_duration_minutes']),
            ('Notes', ['notes']),
        ],
        list_header_info=[
            ('Total Man-Hours', lambda records: round(sum(r.get_man_hours() for r in records), 2))
        ],
    )


def monthly_site_health_reports_page(request):
    return _module_page(
        request,
        model=MonthlySiteHealthReport,
        form_class=MonthlySiteHealthReportForm,
        title='Monthly Site Health Reports',
        description='Create monthly project health and safety summaries for each site.',
        route_name='monthly_site_health_reports_page',
        user_role_min='supervisor',
        list_fields=[
            ('report_month', 'Month'),
            ('report_year', 'Year'),
            ('site_project', 'Site'),
            ('incident_count', 'Incidents'),
            ('man_hours', 'Man-Hours'),
        ],
        form_sections=[
            ('Reporting Period', ['site_project', 'report_month', 'report_year']),
            ('Performance Summary', ['incident_count', 'near_miss_count', 'observation_count', 'inspection_count', 'training_hours', 'man_hours']),
            ('Summary Notes', ['safety_summary']),
        ],
        list_header_info=[
            ('Total Reports', lambda records: len(records)),
            ('Total Man-Hours', lambda records: round(sum(float(getattr(r, 'man_hours', 0) or 0) for r in records), 2)),
            ('Total Incidents', lambda records: sum(int(getattr(r, 'incident_count', 0) or 0) for r in records)),
            ('Average Training Hours', lambda records: round((sum(float(getattr(r, 'training_hours', 0) or 0) for r in records) / len(records)) if records else 0, 2)),
        ],
    )


@login_required
def monthly_report_autofill(request):
    """Return computed stats for a site+month+year as JSON so the form can pre-fill."""
    import json
    from calendar import monthrange

    current_tenant = getattr(request, 'current_tenant', None)
    site_id = request.GET.get('site_id')
    month = request.GET.get('month')
    year = request.GET.get('year')

    if not (current_tenant and site_id and month and year):
        return HttpResponse(json.dumps({}), content_type='application/json')

    try:
        month = int(month)
        year = int(year)
        site = SiteProject.objects.get(pk=site_id, tenant=current_tenant)
    except (ValueError, SiteProject.DoesNotExist):
        return HttpResponse(json.dumps({}), content_type='application/json')

    _, last_day = monthrange(year, month)
    from datetime import date as _date
    date_from = _date(year, month, 1)
    date_to = _date(year, month, last_day)

    incident_count = Incident.objects.filter(tenant=current_tenant, site=site, event_datetime__date__range=(date_from, date_to)).count()
    near_miss_count = Incident.objects.filter(tenant=current_tenant, site=site, event_datetime__date__range=(date_from, date_to), severity='Near Miss').count()
    observation_count = Observation.objects.filter(tenant=current_tenant, site=site, date_observed__range=(date_from, date_to)).count()
    inspection_count = SafetyChecklist.objects.filter(tenant=current_tenant, site=site, date_completed__range=(date_from, date_to)).count()

    attendance_records = AttendanceRecord.objects.filter(tenant=current_tenant, site_project=site, date__range=(date_from, date_to))
    man_hours = round(sum(r.get_man_hours() for r in attendance_records), 2)

    training_count = TrainingMatrix.objects.filter(
        tenant=current_tenant, site=site,
        training_date__range=(date_from, date_to)
    ).count()
    training_hours = float(training_count)

    data = {
        'incident_count': incident_count,
        'near_miss_count': near_miss_count,
        'observation_count': observation_count,
        'inspection_count': inspection_count,
        'man_hours': man_hours,
        'training_hours': training_hours,
    }
    return HttpResponse(json.dumps(data), content_type='application/json')


def contractors_page(request):
    return _module_page(
        request,
        model=Contractor,
        form_class=ContractorForm,
        title='Contractors',
        description='Register and manage contractor onboarding records.',
        route_name='contractors_page',
        user_role_min='supervisor',
        list_fields=[
            ('name', 'Name'),
            ('company', 'Company'),
            ('site', 'Site'),
            ('onboarded', 'Onboarded'),
            ('onboarding_date', 'Onboarding Date'),
        ],
        form_sections=[
            ('Contractor Details', ['site', 'name', 'company', 'onboarded', 'certifications']),
            ('Attachments', ['id_document', 'contractor_file']),
        ],
    )


def certifications_page(request):
    return _module_page(
        request,
        model=Certification,
        form_class=CertificationForm,
        title='Certifications',
        description='Track worker and contractor certifications.',
        route_name='certifications_page',
        user_role_min='supervisor',
        list_fields=[
            ('name', 'Certification'),
            ('employee', 'Employee User'),
            ('issue_date', 'Issue Date'),
            ('expiry_date', 'Expiry Date'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Certification Record', ['site', 'employee', 'name', 'issuing_body', 'issue_date', 'expiry_date', 'certificate_file']),
        ],
    )


def training_page(request):
    return _module_page(
        request,
        model=TrainingMatrix,
        form_class=TrainingMatrixForm,
        title='Training Matrix',
        description='Assign and monitor training items for employees.',
        route_name='training_page',
        user_role_min='supervisor',
        list_fields=[
            ('title', 'Title'),
            ('status', 'Status'),
            ('training_date', 'Training Date'),
            ('due_date', 'Due Date'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Training Overview', ['site', 'title', 'description', 'status', 'assigned_employees']),
            ('Timeline and Evidence', ['training_date', 'due_date', 'certificate_required', 'training_material', 'certificate_upload']),
        ],
    )


def documents_page(request):
    return _module_page(
        request,
        model=Document,
        form_class=DocumentForm,
        title='Documents',
        description='Upload SDS and SOP files from the front-end.',
        route_name='documents_page',
        user_role_min='supervisor',
        auto_user_fields=['uploaded_by'],
        list_fields=[
            ('name', 'Name'),
            ('doc_type', 'Type'),
            ('site', 'Site'),
            ('upload_date', 'Uploaded On'),
            ('uploaded_by', 'Uploaded By'),
        ],
        form_sections=[
            ('Document Entry', ['site', 'name', 'doc_type', 'related_material', 'file']),
        ],
    )


def materials_page(request):
    return _module_page(
        request,
        model=Material,
        form_class=MaterialForm,
        title='Materials',
        description='Manage material and safety data context by site.',
        route_name='materials_page',
        user_role_min='supervisor',
        list_fields=[
            ('name', 'Material'),
            ('quantity', 'Quantity'),
            ('unit', 'Unit'),
            ('sds_available', 'SDS Available'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Material Details', ['site', 'name', 'description', 'date_received', 'quantity', 'unit', 'sds_available', 'material_file']),
        ],
    )


def objectives_page(request):
    return _module_page(
        request,
        model=Objective,
        form_class=ObjectiveForm,
        title='Objectives',
        description='Create and update ISO objective tracking records.',
        route_name='objectives_page',
        user_role_min='supervisor',
        list_fields=[
            ('name', 'Objective'),
            ('status', 'Status'),
            ('current', 'Current'),
            ('target', 'Target'),
            ('due_date', 'Due Date'),
        ],
        form_sections=[
            ('Objective Details', ['site', 'name', 'description', 'target', 'current', 'status', 'assigned_to', 'due_date', 'objective_file']),
        ],
    )


def schedules_page(request):
    return _module_page(
        request,
        model=ScheduleItem,
        form_class=ScheduleItemForm,
        title='Schedules',
        description='Create recurring schedule items and due dates.',
        route_name='schedules_page',
        user_role_min='supervisor',
        auto_user_fields=['created_by'],
        list_fields=[
            ('title', 'Title'),
            ('module', 'Module'),
            ('frequency', 'Frequency'),
            ('next_due_date', 'Next Due'),
            ('is_active', 'Active'),
        ],
        form_sections=[
            ('Schedule Setup', ['site', 'title', 'description', 'module', 'frequency', 'interval_value']),
            ('Timing', ['starts_on', 'next_due_date', 'last_completed_on', 'reminder_days_before']),
            ('Ownership', ['assigned_to', 'is_active']),
        ],
    )


def capa_page(request):
    return _module_page(
        request,
        model=CAPAAction,
        form_class=CAPAActionForm,
        title='CAPA Actions',
        description='Manage corrective and preventive actions from one page.',
        route_name='capa_page',
        user_role_min='supervisor',
        auto_user_fields=['created_by'],
        list_fields=[
            ('title', 'Title'),
            ('priority', 'Priority'),
            ('status', 'Status'),
            ('owner', 'Owner'),
            ('due_date', 'Due Date'),
        ],
        form_sections=[
            ('Action Details', ['site', 'title', 'description', 'priority', 'status', 'due_date', 'owner']),
            ('Root Cause and Actions', ['root_cause', 'immediate_correction', 'corrective_action', 'preventive_action', 'effectiveness_review']),
            ('References and Verification', ['incident', 'observation', 'safety_checklist', 'objective', 'verified_by', 'verification_date', 'closed_on']),
        ],
    )


def medical_profiles_page(request):
    return _module_page(
        request,
        model=MedicalProfile,
        form_class=MedicalProfileForm,
        title='Medical Profiles',
        description='Maintain worker fitness and surveillance profile records.',
        route_name='medical_profiles_page',
        user_role_min='site_manager',
        list_fields=[
            ('employee', 'Employee'),
            ('fitness_status', 'Fitness'),
            ('surveillance_required', 'Surveillance'),
            ('next_medical_due', 'Next Due'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Medical Profile', ['site', 'employee', 'fitness_status', 'surveillance_required', 'next_medical_due', 'restrictions', 'notes']),
        ],
    )


def medical_assessments_page(request):
    return _module_page(
        request,
        model=MedicalAssessment,
        form_class=MedicalAssessmentForm,
        title='Medical Assessments',
        description='Record periodic or pre-employment medical assessments.',
        route_name='medical_assessments_page',
        user_role_min='site_manager',
        auto_user_fields=['assessor'],
        list_fields=[
            ('profile', 'Profile'),
            ('exam_type', 'Exam Type'),
            ('assessment_date', 'Assessment Date'),
            ('outcome', 'Outcome'),
            ('valid_until', 'Valid Until'),
        ],
        form_sections=[
            ('Assessment Record', ['profile', 'exam_type', 'assessment_date', 'valid_until', 'outcome', 'provider', 'report_file', 'notes']),
        ],
    )


# ─── EMS — ISO 14001 Module Views ─────────────────────────────────────────────

def ems_aspects_page(request):
    return _module_page(
        request,
        model=EnvironmentalAspect,
        form_class=EnvironmentalAspectForm,
        title='Environmental Aspects Register',
        description='Identify and evaluate environmental aspects and their significance as required by ISO 14001 Clause 6.1.2.',
        route_name='ems_aspects_page',
        list_fields=[
            ('activity', 'Activity'),
            ('aspect', 'Aspect'),
            ('impact_type', 'Impact Type'),
            ('significance', 'Significance'),
            ('operating_condition', 'Condition'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Aspect Identification', ['site', 'activity', 'aspect', 'potential_impact', 'impact_type', 'operating_condition', 'significance']),
            ('Controls and Compliance', ['control_measure', 'legal_requirement', 'monitoring_required', 'review_date', 'notes']),
        ],
    )


def ems_waste_page(request):
    return _module_page(
        request,
        model=WasteManagementLog,
        form_class=WasteManagementLogForm,
        title='Waste Management Log',
        description='Track waste generation, disposal methods, and contractor manifests aligned with ISO 14001 Clause 8.1.',
        route_name='ems_waste_page',
        auto_user_fields=['recorded_by'],
        list_fields=[
            ('log_date', 'Date'),
            ('waste_type', 'Waste Type'),
            ('description', 'Description'),
            ('quantity_kg', 'Quantity (kg)'),
            ('disposal_method', 'Disposal Method'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Waste Record', ['site', 'log_date', 'waste_type', 'description', 'quantity_kg', 'disposal_method']),
            ('Contractor & Tracking', ['disposal_contractor', 'manifest_number', 'notes']),
        ],
    )


def ems_spills_page(request):
    return _module_page(
        request,
        model=SpillReleaseIncident,
        form_class=SpillReleaseIncidentForm,
        title='Spill & Release Incidents',
        description='Log environmental spills and releases for investigation, cleanup tracking, and regulatory reporting per ISO 14001 Clause 8.2.',
        route_name='ems_spills_page',
        auto_user_fields=['reported_by'],
        list_fields=[
            ('incident_date', 'Date'),
            ('substance', 'Substance'),
            ('severity', 'Severity'),
            ('cleanup_completed', 'Cleaned Up'),
            ('regulatory_notification_required', 'Reg. Notification'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Incident Details', ['site', 'incident_date', 'substance', 'quantity_litres', 'severity', 'location_description']),
            ('Response & Follow-up', ['cause', 'immediate_action', 'cleanup_completed', 'cleanup_date']),
            ('Regulatory', ['regulatory_notification_required', 'regulatory_notification_sent', 'notes']),
        ],
    )


def ems_objectives_page(request):
    return _module_page(
        request,
        model=EnvironmentalObjective,
        form_class=EnvironmentalObjectiveForm,
        title='Environmental Objectives',
        description='Set and monitor measurable environmental objectives and targets per ISO 14001 Clause 6.2.',
        route_name='ems_objectives_page',
        list_fields=[
            ('title', 'Objective'),
            ('indicator', 'Indicator'),
            ('status', 'Status'),
            ('due_date', 'Due Date'),
            ('responsible_person', 'Responsible'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Objective', ['site', 'title', 'target_description', 'indicator', 'due_date']),
            ('Progress', ['status', 'responsible_person', 'notes']),
        ],
    )


def ems_energy_page(request):
    return _module_page(
        request,
        model=EnergyWaterConsumption,
        form_class=EnergyWaterConsumptionForm,
        title='Energy & Water Consumption',
        description='Record energy and water meter readings to monitor consumption trends and support ISO 14001 Clause 6.2 environmental targets.',
        route_name='ems_energy_page',
        auto_user_fields=['recorded_by'],
        list_fields=[
            ('reading_date', 'Date'),
            ('resource_type', 'Resource'),
            ('quantity', 'Quantity'),
            ('unit_cost', 'Unit Cost'),
            ('meter_reference', 'Meter Ref'),
            ('site', 'Site'),
        ],
        form_sections=[
            ('Reading', ['site', 'reading_date', 'resource_type', 'quantity', 'unit_cost', 'meter_reference', 'notes']),
        ],
    )
