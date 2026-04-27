from django.contrib import admin
from .tenant_context import has_minimum_role, resolve_current_tenant, user_role_for_tenant, user_tenants
from .models import (
    Tenant,
    SubscriptionPlan,
    TenantSubscription,
    SiteProject,
    TenantMembership,
    Incident,
    JSA,
    JSAStep,
    FRA,
    FLRA,
    Document,
    Material,
    Observation,
    SafetyChecklist,
    Certification,
    Contractor,
    Employee,
    Objective,
    TrainingMatrix,
    PTOChemicalHazardousSubstance,
    ScheduleItem,
    Reminder,
    ToolboxTalk,
    CAPAAction,
    CCVCriticalControlVerification,
    MedicalProfile,
    MedicalAssessment,
    KPIDailySnapshot,
    AnalyticsWarehouseDaily,
    AuditLog,
)


class TenantScopedAdmin(admin.ModelAdmin):
    """Applies tenant filtering and auto-assignment for tenant-bound models."""

    write_min_role = 'supervisor'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        if not hasattr(self.model, 'tenant'):
            return queryset

        current_tenant = resolve_current_tenant(request)
        if current_tenant is None:
            return queryset.none()
        return queryset.filter(tenant=current_tenant)

    def save_model(self, request, obj, form, change):
        if hasattr(obj, 'tenant_id') and not obj.tenant_id:
            obj.tenant = resolve_current_tenant(request)
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'tenant' and not request.user.is_superuser:
            kwargs['queryset'] = user_tenants(request.user)
        elif db_field.name == 'site' and not request.user.is_superuser:
            current_tenant = resolve_current_tenant(request)
            if current_tenant is not None:
                kwargs['queryset'] = SiteProject.objects.filter(tenant=current_tenant)
            else:
                kwargs['queryset'] = SiteProject.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'selected_employees' and not request.user.is_superuser:
            current_tenant = resolve_current_tenant(request)
            if current_tenant is not None:
                kwargs['queryset'] = Employee.objects.filter(tenant=current_tenant).order_by('name')
            else:
                kwargs['queryset'] = Employee.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def _has_write_access(self, request):
        if request.user.is_superuser:
            return True

        current_tenant = resolve_current_tenant(request)
        current_role = user_role_for_tenant(request.user, current_tenant)
        return has_minimum_role(current_role, self.write_min_role)

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return self._has_write_access(request)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if request.user.is_superuser:
            return True

        if obj is not None and hasattr(obj, 'tenant'):
            current_tenant = resolve_current_tenant(request)
            if current_tenant is None or obj.tenant_id != current_tenant.id:
                return False

        return self._has_write_access(request)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        return self._has_write_access(request)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'monthly_price', 'max_users', 'max_sites', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(TenantScopedAdmin):
    write_min_role = 'admin'
    list_display = ('tenant', 'plan', 'status', 'start_date', 'renewal_date', 'auto_renew')
    list_filter = ('status', 'auto_renew', 'plan')
    search_fields = ('tenant__name', 'plan__name', 'plan__code')


@admin.register(SiteProject)
class SiteProjectAdmin(TenantScopedAdmin):
    write_min_role = 'admin'
    list_display = ('name', 'tenant', 'status', 'location', 'manager', 'start_date', 'end_date')
    list_filter = ('status', 'tenant')
    search_fields = ('name', 'code', 'location', 'tenant__name')


@admin.register(TenantMembership)
class TenantMembershipAdmin(TenantScopedAdmin):
    write_min_role = 'admin'
    list_display = ('tenant', 'user', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'tenant')
    search_fields = ('tenant__name', 'user__username', 'user__email')


@admin.register(Objective)
class ObjectiveAdmin(TenantScopedAdmin):
    list_display = ('name', 'tenant', 'site', 'target', 'current', 'status', 'assigned_to', 'due_date')
    list_filter = ('status', 'assigned_to', 'tenant', 'site')
    search_fields = ('name', 'description')


@admin.register(TrainingMatrix)
class TrainingMatrixAdmin(TenantScopedAdmin):
    list_display = ('title', 'tenant', 'site', 'status', 'training_date', 'due_date', 'certificate_required')
    list_filter = ('status', 'certificate_required', 'tenant', 'site')
    search_fields = ('title', 'description')


@admin.register(Incident)
class IncidentAdmin(TenantScopedAdmin):
    list_display = ('title', 'tenant', 'site', 'incident_category', 'severity', 'reportable_to_regulator', 'reported_by', 'date_reported')
    list_filter = ('severity', 'reportable_to_regulator', 'employment_type', 'tenant', 'site')
    search_fields = ('title', 'description', 'location')


class JSAStepInline(admin.TabularInline):
    model = JSAStep
    extra = 1
    fields = ('step_number', 'job_step', 'job_step_hazard', 'current_controls', 'evaluation_control_type', 'likelihood_before', 'consequence_before', 'residual_risk_before', 'required_additional_actions', 'likelihood_after', 'consequence_after', 'residual_risk_after')


@admin.register(JSA)
class JSAAdmin(TenantScopedAdmin):
    list_display = ('jsa_number', 'job_task', 'plant_area', 'senior_supervisor_name', 'work_group_supervisor_name', 'assessment_date', 'signed', 'tenant', 'site')
    list_filter = ('signed', 'pre_job_briefing_completed', 'tenant', 'site', 'assessment_date', 'permit_to_work', 'confined_space_permit')
    search_fields = ('jsa_number', 'job_task', 'plant_area', 'location', 'hazards', 'controls')
    inlines = [JSAStepInline]
    readonly_fields = ('date', 'created_at', 'updated_at')
    fieldsets = (
        ('Document Information', {
            'fields': ('document_reference', 'revision_number', 'total_pages', 'date_of_issue', 'date_of_next_review', 'date', 'created_at', 'updated_at')
        }),
        ('JSA Summary', {
            'fields': ('jsa_number', 'work_order_number', 'job_task', 'plant_area', 'location', 'assessment_date', 'site', 'tenant')
        }),
        ('Supervisors', {
            'fields': ('senior_supervisor_name', 'senior_supervisor_signature', 'work_group_supervisor_name', 'work_group_supervisor_signature')
        }),
        ('Permits & Execution', {
            'fields': ('permit_to_work', 'excavation_permit', 'hot_work_permit', 'hv_electrical_isolation_permit', 'hv_vicinity_permit', 'radiation_work_permit', 'working_at_height_permit', 'chemical_pump_pipe_permit', 'confined_space_permit', 'other_permit', 'other_permit_description', 'additional_ppe_requirements', 'special_tools_equipment')
        }),
        ('Fatality Prevention', {
            'fields': ('fpc_competent_capable_controlled', 'fpc_identify_control_hazards', 'fpc_safe_lifting_operations', 'fpc_drive_safely', 'fpc_energy_isolation', 'fpc_confined_space_entry', 'fpc_work_at_heights', 'fpc_surface_underground', 'fpc_equipment_safeguards', 'fpc_chemicals_hazardous_substances')
        }),
        ('Hazards & Controls', {
            'fields': ('hazards', 'hazard_flora_fauna', 'hazard_electrical', 'hazard_mechanical', 'hazard_chemical', 'hazard_dust_fume', 'hazard_soil_erosion', 'hazard_stored_energy', 'hazard_live_equipment', 'hazard_manual_handling', 'hazard_radiation', 'hazard_spills_water', 'hazard_falling_equipment', 'hazard_noise', 'hazard_ignition_sources', 'hazard_spills_ground', 'hazard_fire_explosives', 'hazard_light_dark', 'hazard_rock_falls', 'hazard_concealed_services', 'controls')
        }),
        ('Environment & Equipment', {
            'fields': ('hazardous_materials', 'fire_emergency_equipment', 'weather_rain', 'weather_thunder', 'weather_lightning', 'weather_extreme_temperatures', 'weather_other', 'weather_other_description')
        }),
        ('Supporting Documents', {
            'fields': ('supports_lift_plan', 'supports_sds', 'supports_emergency_action_plan')
        }),
        ('Approval & Review', {
            'fields': ('performed_by', 'pre_job_briefing_completed', 'supervisor_approval', 'signed', 'valid_from', 'valid_to', 'jsa_file', 'team_member_acknowledgements', 'senior_supervisor_acknowledgement', 'daily_review_log')
        }),
    )


@admin.register(JSAStep)
class JSAStepAdmin(admin.ModelAdmin):
    list_display = ('jsa', 'step_number', 'job_step', 'evaluation_control_type', 'residual_risk_before', 'residual_risk_after')
    list_filter = ('jsa', 'evaluation_control_type')
    search_fields = ('jsa__jsa_number', 'job_step', 'job_step_hazard')
    readonly_fields = ('jsa',)


@admin.register(FRA)
class FRAAdmin(TenantScopedAdmin):
    list_display = ('activity', 'tenant', 'site', 'location', 'risk_level', 'initial_risk_score', 'residual_risk_score', 'acceptable', 'date_assessed')
    list_filter = ('risk_level', 'acceptable', 'tenant', 'site')
    search_fields = ('activity', 'location', 'risk_identified')


@admin.register(FLRA)
class FLRAAdmin(TenantScopedAdmin):
    list_display = ('task_description', 'tenant', 'site', 'location', 'shift', 'selected_employee_summary', 'energy_isolation_confirmed', 'escalation_required', 'date')
    list_filter = ('energy_isolation_confirmed', 'escalation_required', 'tenant', 'site')
    search_fields = ('task_description', 'location', 'identified_hazards', 'selected_employees__name', 'crew')

    def selected_employee_summary(self, obj):
        return obj.selected_employee_names

    selected_employee_summary.short_description = 'Employees'


@admin.register(Document)
class DocumentAdmin(TenantScopedAdmin):
    list_display = ('name', 'doc_type', 'tenant', 'site', 'uploaded_by', 'upload_date')
    list_filter = ('doc_type', 'tenant', 'site')
    search_fields = ('name',)


@admin.register(Material)
class MaterialAdmin(TenantScopedAdmin):
    list_display = ('name', 'tenant', 'site', 'quantity', 'unit', 'sds_available', 'date_received')
    list_filter = ('sds_available', 'tenant', 'site')
    search_fields = ('name', 'description')


@admin.register(Observation)
class ObservationAdmin(TenantScopedAdmin):
    list_display = ('task', 'observation_type', 'tenant', 'site', 'observed_by', 'date', 'follow_up_required')
    list_filter = ('observation_type', 'follow_up_required', 'tenant', 'site')
    search_fields = ('task', 'findings', 'controls_verified')


@admin.register(PTOChemicalHazardousSubstance)
class PTOChemicalHazardousSubstanceAdmin(TenantScopedAdmin):
    list_display = (
        'pto_type',
        'employee_name',
        'observer_name',
        'tenant',
        'site',
        'competency_result',
        'follow_up_pto_recommended',
        'created_at',
    )
    list_filter = ('competency_result', 'follow_up_pto_recommended', 'tenant', 'site')
    search_fields = ('employee_name', 'employee_id', 'observer_name', 'observer_employee_id')


@admin.register(CCVCriticalControlVerification)
class CCVCriticalControlVerificationAdmin(TenantScopedAdmin):
    list_display = (
        'ccv_type',
        'assessor_name',
        'location',
        'department',
        'tenant',
        'site',
        'created_at',
    )
    list_filter = ('ccv_type', 'tenant', 'site')
    search_fields = ('assessor_name', 'location', 'department', 'section')


@admin.register(SafetyChecklist)
class SafetyChecklistAdmin(TenantScopedAdmin):
    list_display = ('checklist_type', 'checklist_title', 'tenant', 'site', 'completed_by', 'operational_status', 'date_completed')
    list_filter = ('checklist_type', 'tenant', 'site')
    search_fields = ('checklist_title', 'equipment_id', 'inspection_area', 'findings', 'actions_required')


@admin.register(ToolboxTalk)
class ToolboxTalkAdmin(TenantScopedAdmin):
    list_display = ('title', 'talk_date', 'tenant', 'site', 'facilitator_name', 'attendance_count', 'follow_up_required')
    list_filter = ('talk_date', 'follow_up_required', 'tenant', 'site')
    search_fields = ('title', 'facilitator_name', 'department', 'work_group', 'topic_details', 'hazards_discussed')


@admin.register(Certification)
class CertificationAdmin(TenantScopedAdmin):
    list_display = ('name', 'tenant', 'site', 'employee', 'issuing_body', 'issue_date', 'expiry_date')
    list_filter = ('tenant', 'site', 'issuing_body')
    search_fields = ('name', 'issuing_body', 'employee__username')


@admin.register(Contractor)
class ContractorAdmin(TenantScopedAdmin):
    list_display = ('name', 'company', 'tenant', 'site', 'onboarded', 'onboarding_date')
    list_filter = ('onboarded', 'tenant', 'site', 'company')
    search_fields = ('name', 'company')


@admin.register(Employee)
class EmployeeAdmin(TenantScopedAdmin):
    list_display = ('name', 'tenant', 'site', 'position', 'department', 'contact_number', 'user')
    list_filter = ('tenant', 'site', 'department')
    search_fields = ('name', 'position', 'department')


@admin.register(ScheduleItem)
class ScheduleItemAdmin(TenantScopedAdmin):
    list_display = (
        'title',
        'tenant',
        'site',
        'module',
        'frequency',
        'next_due_date',
        'assigned_to',
        'is_active',
    )
    list_filter = ('tenant', 'site', 'module', 'frequency', 'is_active')
    search_fields = ('title', 'description')


@admin.register(Reminder)
class ReminderAdmin(TenantScopedAdmin):
    list_display = ('title', 'tenant', 'site', 'channel', 'status', 'remind_on', 'due_date')
    list_filter = ('tenant', 'site', 'channel', 'status')
    search_fields = ('title', 'message', 'schedule__title')


@admin.register(CAPAAction)
class CAPAActionAdmin(TenantScopedAdmin):
    list_display = ('title', 'tenant', 'site', 'priority', 'status', 'owner', 'due_date', 'closed_on')
    list_filter = ('tenant', 'site', 'priority', 'status')
    search_fields = ('title', 'description', 'root_cause', 'corrective_action', 'preventive_action')


@admin.register(MedicalProfile)
class MedicalProfileAdmin(TenantScopedAdmin):
    write_min_role = 'site_manager'
    list_display = ('employee', 'tenant', 'site', 'fitness_status', 'surveillance_required', 'next_medical_due')
    list_filter = ('tenant', 'site', 'fitness_status', 'surveillance_required')
    search_fields = ('employee__name', 'employee__position', 'restrictions')


@admin.register(MedicalAssessment)
class MedicalAssessmentAdmin(TenantScopedAdmin):
    write_min_role = 'site_manager'
    list_display = ('profile', 'tenant', 'site', 'exam_type', 'assessment_date', 'valid_until', 'outcome')
    list_filter = ('tenant', 'site', 'outcome', 'exam_type')
    search_fields = ('profile__employee__name', 'exam_type', 'provider', 'notes')


@admin.register(AuditLog)
class AuditLogAdmin(TenantScopedAdmin):
    list_display = ('created_at', 'tenant', 'site', 'action', 'model_name', 'object_id', 'user')
    list_filter = ('action', 'model_name', 'tenant', 'site')
    search_fields = ('model_name', 'object_id', 'object_repr', 'change_summary')
    readonly_fields = ('tenant', 'site', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'change_summary', 'payload', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(KPIDailySnapshot)
class KPIDailySnapshotAdmin(TenantScopedAdmin):
    write_min_role = 'admin'
    list_display = (
        'snapshot_date',
        'tenant',
        'site',
        'incident_count',
        'open_capa_count',
        'overdue_capa_count',
        'observation_count',
        'checklist_count',
    )
    list_filter = ('snapshot_date', 'tenant', 'site')
    search_fields = ('tenant__name', 'site__name')


@admin.register(AnalyticsWarehouseDaily)
class AnalyticsWarehouseDailyAdmin(TenantScopedAdmin):
    write_min_role = 'admin'
    list_display = (
        'snapshot_date',
        'tenant',
        'site',
        'incident_count',
        'open_capa_count',
        'overdue_capa_count',
        'training_completion_rate',
        'overdue_capa_rate',
    )
    list_filter = ('snapshot_date', 'tenant', 'site')
    search_fields = ('tenant__name', 'site__name')

# Change admin site header
admin.site.site_header = "ISO CSystem"
admin.site.site_title = "ISO CSystem Admin"
admin.site.index_title = "Welcome to ISO_CSystem Administration"
