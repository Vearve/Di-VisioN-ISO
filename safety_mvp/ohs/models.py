# Updated MVP Django App Structure for OHS ISO 45001 Tool

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, timedelta


class Tenant(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_active_subscription(self):
        return self.subscriptions.filter(status__in=['trial', 'active']).order_by('-start_date').first()

    def get_plan_limit(self, key, default_value=None):
        subscription = self.get_active_subscription()
        if subscription is None:
            return default_value
        return getattr(subscription.plan, key, default_value)


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=50, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=25)
    max_sites = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class TenantSubscription(models.Model):
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.plan.code} ({self.status})"


class SiteProject(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('closed', 'Closed'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=60, blank=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    site_attachment = models.FileField(upload_to='site_projects/', blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_sites')

    class Meta:
        unique_together = ('tenant', 'name')

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"

    def clean(self):
        super().clean()
        max_sites = self.tenant.get_plan_limit('max_sites') if self.tenant_id else None
        if max_sites is None:
            return

        current_sites = SiteProject.objects.filter(tenant=self.tenant).exclude(pk=self.pk).count()
        if current_sites >= max_sites:
            raise ValidationError({'tenant': f'This tenant reached its plan site limit ({max_sites}).'})


class SiteProjectAttachment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='site_project_attachments')
    site_project = models.ForeignKey(SiteProject, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='site_projects/attachments/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='site_project_attachments_uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-uploaded_at',)

    def __str__(self):
        return f"{self.site_project.name} attachment {self.id}"


class TenantMembership(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('site_manager', 'Site Manager'),
        ('supervisor', 'Supervisor'),
        ('worker', 'Worker'),
        ('auditor', 'Auditor'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'user')

    def __str__(self):
        return f"{self.tenant.name} - {self.user.username} ({self.role})"

    def clean(self):
        super().clean()
        max_users = self.tenant.get_plan_limit('max_users') if self.tenant_id else None
        if max_users is None:
            return

        active_members = TenantMembership.objects.filter(
            tenant=self.tenant,
            is_active=True,
        ).exclude(pk=self.pk).count()

        if self.is_active and active_members >= max_users:
            raise ValidationError({'tenant': f'This tenant reached its plan user limit ({max_users}).'})


class TenantPreset(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='presets')
    ccv_target = models.PositiveIntegerField(default=20)
    pto_target = models.PositiveIntegerField(default=20)
    flra_target = models.PositiveIntegerField(default=500)
    employee_target = models.PositiveIntegerField(default=0)
    objective_target = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} presets"


# Project-Level Presets
class ProjectPreset(models.Model):
    """KPI targets for a specific site/project."""
    site_project = models.OneToOneField(SiteProject, on_delete=models.CASCADE, related_name='preset')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='project_presets')
    man_hours_target = models.PositiveIntegerField(default=1000, help_text='Monthly man-hours target')
    incident_target = models.PositiveIntegerField(default=0, help_text='Target incidents (0 = zero tolerance)')
    jsa_target = models.PositiveIntegerField(default=10, help_text='Monthly JSAs target')
    fra_target = models.PositiveIntegerField(default=5, help_text='Monthly FRAs target')
    flra_target = models.PositiveIntegerField(default=100, help_text='Monthly FLRAs target')
    ccv_target = models.PositiveIntegerField(default=20, help_text='Monthly CCVs target')
    safety_incidents_severity_target = models.CharField(
        max_length=20,
        choices=[('none', 'Zero High Severity'), ('low', 'Only Low Severity'), ('any', 'All Types')],
        default='low'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('site_project', 'tenant')

    def __str__(self):
        return f"{self.site_project.name} - KPI Preset"


# Incident Reporting
class Incident(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('employee', 'Employee'),
        ('contractor', 'Contractor'),
        ('visitor', 'Visitor'),
    ]

    TREATMENT_LEVEL_CHOICES = [
        ('none', 'None'),
        ('first_aid', 'First Aid'),
        ('medical_treatment', 'Medical Treatment'),
        ('hospitalization', 'Hospitalization'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='incidents')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    title = models.CharField(max_length=255)
    description = models.TextField()

    @property
    def site_project(self):
        return self.site
    date_reported = models.DateField(auto_now_add=True)
    event_datetime = models.DateTimeField(null=True, blank=True)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='incidents/', blank=True, null=True)
    incident_file = models.FileField(upload_to='incidents/files/', blank=True, null=True)  # <-- Add this
    location = models.CharField(max_length=255)
    incident_category = models.CharField(max_length=120, blank=True)
    affected_person_name = models.CharField(max_length=255, blank=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, blank=True)
    department = models.CharField(max_length=255, blank=True)
    crew = models.CharField(max_length=255, blank=True)
    witnesses = models.TextField(blank=True)
    immediate_action_taken = models.TextField(blank=True)
    injury_type = models.CharField(max_length=255, blank=True)
    body_part_affected = models.CharField(max_length=255, blank=True)
    lost_time_days = models.PositiveIntegerField(default=0)
    treatment_level = models.CharField(max_length=30, choices=TREATMENT_LEVEL_CHOICES, default='none')
    root_cause = models.TextField(blank=True)
    contributing_factors = models.TextField(blank=True)
    corrective_actions = models.TextField(blank=True)
    action_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incident_actions_owned')
    investigation_lead = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incident_investigations_led')
    investigation_completion_date = models.DateField(null=True, blank=True)
    reportable_to_regulator = models.BooleanField(default=False)
    regulator_notification_date = models.DateField(null=True, blank=True)
    closeout_verification = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    severity = models.CharField(max_length=50, choices=[
        ('Near Miss', 'Near Miss'),
        ('First Aid', 'First Aid'),
        ('Medical Treatment', 'Medical Treatment'),
        ('Lost Time', 'Lost Time'),
        ('Fatality', 'Fatality'),
    ])

# JSA (Job Safety Analysis)
class JSA(models.Model):
    # Document metadata (FM0464, Rev 09, etc.)
    document_reference = models.CharField(max_length=50, default='FM0464')
    revision_number = models.CharField(max_length=50, default='09')
    total_pages = models.CharField(max_length=20, blank=True)
    date_of_issue = models.DateField(default=date(2024, 5, 15))
    date_of_next_review = models.DateField(default=date(2026, 5, 14))
    
    # JSA Summary section
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='jsas')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='jsas')
    jsa_number = models.CharField(max_length=100, blank=True)
    work_order_number = models.CharField(max_length=100, blank=True)
    job_task = models.CharField(max_length=500)
    plant_area = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255)
    assessment_date = models.DateField(null=True, blank=True)
    
    # Supervisors
    senior_supervisor_name = models.CharField(max_length=255, blank=True)
    senior_supervisor_signature = models.TextField(blank=True)  # Can store signature as base64 or path
    work_group_supervisor_name = models.CharField(max_length=255, blank=True)
    work_group_supervisor_signature = models.TextField(blank=True)
    
    # Permit types (checkboxes)
    permit_to_work = models.BooleanField(default=False)
    excavation_permit = models.BooleanField(default=False)
    hot_work_permit = models.BooleanField(default=False)
    hv_electrical_isolation_permit = models.BooleanField(default=False)
    hv_vicinity_permit = models.BooleanField(default=False)
    radiation_work_permit = models.BooleanField(default=False)
    working_at_height_permit = models.BooleanField(default=False)
    chemical_pump_pipe_permit = models.BooleanField(default=False)
    confined_space_permit = models.BooleanField(default=False)
    other_permit = models.BooleanField(default=False)
    other_permit_description = models.CharField(max_length=255, blank=True)
    
    # PPE and Equipment
    additional_ppe_requirements = models.TextField(blank=True)
    special_tools_equipment = models.TextField(blank=True)
    
    # Fatality Prevention Commitments
    fpc_competent_capable_controlled = models.BooleanField(default=False)
    fpc_identify_control_hazards = models.BooleanField(default=False)
    fpc_safe_lifting_operations = models.BooleanField(default=False)
    fpc_drive_safely = models.BooleanField(default=False)
    fpc_energy_isolation = models.BooleanField(default=False)
    fpc_confined_space_entry = models.BooleanField(default=False)
    fpc_work_at_heights = models.BooleanField(default=False)
    fpc_surface_underground = models.BooleanField(default=False)
    fpc_equipment_safeguards = models.BooleanField(default=False)
    fpc_chemicals_hazardous_substances = models.BooleanField(default=False)
    
    # Hazardous Materials & Fire/Emergency Equipment
    hazardous_materials = models.TextField(blank=True)
    fire_emergency_equipment = models.TextField(blank=True)
    
    # Supporting Documents
    supports_lift_plan = models.BooleanField(default=False)
    supports_sds = models.BooleanField(default=False)
    supports_emergency_action_plan = models.BooleanField(default=False)
    safe_work_procedure_possible = models.BooleanField(null=True, blank=True)
    
    # Potential Hazards (checkboxes)
    hazard_flora_fauna = models.BooleanField(default=False)
    hazard_electrical = models.BooleanField(default=False)
    hazard_mechanical = models.BooleanField(default=False)
    hazard_chemical = models.BooleanField(default=False)
    hazard_dust_fume = models.BooleanField(default=False)
    hazard_soil_erosion = models.BooleanField(default=False)
    hazard_stored_energy = models.BooleanField(default=False)
    hazard_live_equipment = models.BooleanField(default=False)
    hazard_manual_handling = models.BooleanField(default=False)
    hazard_radiation = models.BooleanField(default=False)
    hazard_spills_water = models.BooleanField(default=False)
    hazard_falling_equipment = models.BooleanField(default=False)
    hazard_noise = models.BooleanField(default=False)
    hazard_ignition_sources = models.BooleanField(default=False)
    hazard_spills_ground = models.BooleanField(default=False)
    hazard_fire_explosives = models.BooleanField(default=False)
    hazard_light_dark = models.BooleanField(default=False)
    hazard_rock_falls = models.BooleanField(default=False)
    hazard_concealed_services = models.BooleanField(default=False)
    
    # Weather conditions
    weather_rain = models.BooleanField(default=False)
    weather_thunder = models.BooleanField(default=False)
    weather_lightning = models.BooleanField(default=False)
    weather_extreme_temperatures = models.BooleanField(default=False)
    weather_other = models.BooleanField(default=False)
    weather_other_description = models.CharField(max_length=255, blank=True)
    
    # Legacy or additional fields
    task = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    pre_job_briefing_completed = models.BooleanField(default=False)
    supervisor_approval = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_jsas')
    required_competency = models.TextField(blank=True)
    responsible_person_per_control = models.TextField(blank=True)
    additional_controls_required = models.TextField(blank=True)
    hazards = models.TextField(blank=True)
    controls = models.TextField(blank=True)
    signed = models.BooleanField(default=False)
    jsa_file = models.FileField(upload_to='jsa/files/', blank=True, null=True)
    
    # Acknowledgements  
    team_member_acknowledgements = models.JSONField(default=list, blank=True)  # [{name, id_no, date, signature}, ...]
    senior_supervisor_acknowledgement = models.TextField(blank=True)
    daily_review_log = models.JSONField(default=list, blank=True)  # For multi-shift reviews
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"JSA {self.jsa_number} - {self.job_task} ({self.document_reference})"


class JSAStep(models.Model):
    """Job Safety Analysis Step - represents each row in the Job Safety Analysis Log table"""
    HIERARCHY_CHOICES = [
        ('elimination', 'Elimination'),
        ('substitution', 'Substitution'),
        ('engineering', 'Engineering'),
        ('administrative', 'Administrative'),
        ('ppe', 'PPE'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('1', 'Very Low'),
        ('2', 'Low'),
        ('3', 'Medium'),
        ('4', 'High'),
        ('5', 'Very High'),
    ]
    
    jsa = models.ForeignKey(JSA, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField()
    job_step = models.TextField()  # Description of the step
    job_step_hazard = models.TextField()  # Potential hazards
    current_controls = models.TextField()  # Existing controls
    
    # Evaluation of Controls - Before
    evaluation_control_type = models.CharField(max_length=20, choices=HIERARCHY_CHOICES, blank=True)
    likelihood_before = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    consequence_before = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    residual_risk_before = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    
    # Required Additional Actions
    required_additional_actions = models.TextField(blank=True)
    
    # After improvements
    likelihood_after = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    consequence_after = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    residual_risk_after = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    
    class Meta:
        unique_together = ('jsa', 'step_number')
        ordering = ('jsa', 'step_number')
    
    def __str__(self):
        return f"Step {self.step_number} - {self.job_step[:50]}"

# FRA (Formal Risk Assessment)
class FRA(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='fras')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='fras')
    activity = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    hazard_category = models.CharField(max_length=120, blank=True)
    persons_at_risk = models.TextField(blank=True)
    existing_controls = models.TextField(blank=True)
    likelihood = models.PositiveIntegerField(null=True, blank=True)
    severity_score = models.PositiveIntegerField(null=True, blank=True)
    initial_risk_score = models.PositiveIntegerField(null=True, blank=True)
    additional_controls = models.TextField(blank=True)
    residual_likelihood = models.PositiveIntegerField(null=True, blank=True)
    residual_severity = models.PositiveIntegerField(null=True, blank=True)
    residual_risk_score = models.PositiveIntegerField(null=True, blank=True)
    acceptable = models.BooleanField(default=True)
    review_frequency = models.CharField(max_length=100, blank=True)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_fras')
    risk_identified = models.TextField()
    risk_level = models.CharField(max_length=50)
    control_measures = models.TextField()
    assessed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date_assessed = models.DateField(auto_now_add=True)
    fra_file = models.FileField(upload_to='fra/files/', blank=True, null=True)  # <-- Add this

# FLRA (Field Level Risk Assessment)
class FLRA(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='flras')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='flras')
    date = models.DateField(auto_now_add=True)
    shift = models.CharField(max_length=100, blank=True)
    selected_employees = models.ManyToManyField('Employee', blank=True, related_name='flra_entries')
    crew = models.CharField(max_length=255, blank=True)
    weather_conditions = models.CharField(max_length=255, blank=True)
    simultaneous_operations = models.BooleanField(default=False)
    energy_isolation_confirmed = models.BooleanField(default=False)
    stop_work_authority_used = models.BooleanField(default=False)
    worker_signatures = models.TextField(blank=True)
    supervisor_signature = models.CharField(max_length=255, blank=True)
    dynamic_changes_noticed = models.TextField(blank=True)
    additional_controls_added = models.TextField(blank=True)
    escalation_required = models.BooleanField(default=False)
    location = models.CharField(max_length=255)
    assessed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    task_description = models.TextField()
    identified_hazards = models.TextField()
    control_measures = models.TextField()
    flra_file = models.FileField(upload_to='flra/files/', blank=True, null=True)  # <-- Add this

    @property
    def selected_employee_names(self):
        names = list(self.selected_employees.values_list('name', flat=True))
        return ', '.join(names) if names else '-'

# SDS and SOP
class Document(models.Model):
    DOC_TYPE_CHOICES = [
        ('SDS', 'Safety Data Sheet'),
        ('SOP', 'Standard Operating Procedure')
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=10, choices=DOC_TYPE_CHOICES)
    related_material = models.ForeignKey('Material', on_delete=models.SET_NULL, null=True, blank=True)
    upload_date = models.DateField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/')

# Material and related SDS
class Material(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='materials')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='materials')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date_received = models.DateField()
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=50)
    sds_available = models.BooleanField(default=False)
    material_file = models.FileField(upload_to='materials/files/', blank=True, null=True)  # <-- Add this

# PTO/CCV - Planned Task Observation / Critical Control Verification
class Observation(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='observations')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations')
    observed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    task = models.CharField(max_length=255)
    observation_type = models.CharField(max_length=10, choices=[
        ('PTO', 'Planned Task Observation'),
        ('CCV', 'Critical Control Verification')
    ])
    controls_verified = models.TextField()
    findings = models.TextField()
    follow_up_required = models.BooleanField(default=False)
    attachments = models.ManyToManyField('Document', blank=True)
    file = models.FileField(upload_to='observations/', blank=True, null=True)  # Already present


class PTOChemicalHazardousSubstance(models.Model):
    PTO_TYPE_CHOICES = [
        ('chemicals_hazardous_substances', 'Chemicals & Hazardous Substances PTO'),
        ('work_at_heights', 'Work at Heights PTO'),
        ('energy_isolation', 'Energy Isolation PTO'),
        ('equipment_safeguards_protective_devices', 'Equipment Safeguards & Protective Devices PTO'),
        ('identify_control_hazards', 'Identify and Control Hazards PTO'),
        ('mobile_equipment_light_vehicles', 'Mobile Equipment & Light Vehicles PTO'),
        ('competent_capable_controlled', 'Competent, Capable and Controlled PTO'),
        ('safe_operation_forklifts', 'Safe Operation for Forklifts PTO'),
    ]

    COMPETENCY_CHOICES = [
        ('C', 'Competent'),
        ('NYC', 'Not Yet Competent'),
    ]

    SHIFT_MINING_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('night', 'Night'),
    ]

    SHIFT_OTHER_CHOICES = [
        ('day', 'Day'),
        ('night', 'Night'),
    ]

    CREW_MINING_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]

    CREW_OTHER_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('N/A', 'N/A'),
    ]

    REASON_CHOICES = [
        ('incident_follow_up', 'Incident follow up'),
        ('training_follow_up', 'Training follow up'),
        ('task_infrequent', 'Task infrequently performed'),
        ('critical_task_audit', 'Critical task audit'),
        ('periodic_pto', 'Periodic PTO'),
        ('new_employee', 'New Employee'),
    ]

    NOTIFICATION_CHOICES = [
        ('in_advance', 'Told in Advance'),
        ('not_in_advance', 'Not Told in Advance'),
    ]

    FORM_TITLE = 'CHEMICALS & HAZARDOUS SUBSTANCES FPC PTO'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pto_chemical_hazardous_substances')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='pto_chemical_hazardous_substances')
    pto_type = models.CharField(max_length=60, choices=PTO_TYPE_CHOICES, default='chemicals_hazardous_substances')

    reference_number = models.CharField(max_length=20, default='0623', editable=False)
    version = models.CharField(max_length=10, default='00', editable=False)
    authored_by = models.CharField(max_length=120, default='E Hinamanjolo', editable=False)
    approved_by = models.CharField(max_length=120, default='T Zulu', editable=False)
    form_issue_date = models.DateField(default=date(2022, 2, 15), editable=False)

    observer_name = models.CharField(max_length=255)
    observer_employee_id = models.CharField(max_length=50, blank=True)
    observer_job_title = models.CharField(max_length=255, blank=True)
    observer_department = models.CharField(max_length=255, blank=True)
    observer_date = models.DateField(null=True, blank=True)
    observer_signature = models.CharField(max_length=255, blank=True)

    employee_name = models.CharField(max_length=255)
    employee_id = models.CharField(max_length=50, blank=True)
    employee_job_title = models.CharField(max_length=255, blank=True)
    employee_department = models.CharField(max_length=255, blank=True)
    employee_observed_at = models.DateTimeField(null=True, blank=True)
    employee_signature = models.CharField(max_length=255, blank=True)

    shift_mining = models.CharField(max_length=20, choices=SHIFT_MINING_CHOICES, blank=True)
    shift_other = models.CharField(max_length=20, choices=SHIFT_OTHER_CHOICES, blank=True)
    crew_mining = models.CharField(max_length=10, choices=CREW_MINING_CHOICES, blank=True)
    crew_other = models.CharField(max_length=10, choices=CREW_OTHER_CHOICES, blank=True)
    reason_for_observation = models.CharField(max_length=40, choices=REASON_CHOICES, blank=True)
    notification_of_pto = models.CharField(max_length=20, choices=NOTIFICATION_CHOICES, blank=True)

    competency_result = models.CharField(max_length=3, choices=COMPETENCY_CHOICES, blank=True)
    forwarded_to_hr = models.BooleanField(null=True, blank=True)
    follow_up_pto_recommended = models.BooleanField(null=True, blank=True)

    action_1 = models.CharField(max_length=255, blank=True)
    action_1_responsible = models.CharField(max_length=255, blank=True)
    action_1_by_when = models.DateField(null=True, blank=True)
    action_2 = models.CharField(max_length=255, blank=True)
    action_2_responsible = models.CharField(max_length=255, blank=True)
    action_2_by_when = models.DateField(null=True, blank=True)
    action_3 = models.CharField(max_length=255, blank=True)
    action_3_responsible = models.CharField(max_length=255, blank=True)
    action_3_by_when = models.DateField(null=True, blank=True)
    employee_superintendent_name = models.CharField(max_length=255, blank=True)
    employee_superintendent_signature = models.CharField(max_length=255, blank=True)

    step_01_compliant = models.BooleanField(null=True, blank=True)
    step_01_comments = models.TextField(blank=True)
    step_02_compliant = models.BooleanField(null=True, blank=True)
    step_02_comments = models.TextField(blank=True)
    step_03_compliant = models.BooleanField(null=True, blank=True)
    step_03_comments = models.TextField(blank=True)
    step_04_compliant = models.BooleanField(null=True, blank=True)
    step_04_comments = models.TextField(blank=True)
    step_05_compliant = models.BooleanField(null=True, blank=True)
    step_05_comments = models.TextField(blank=True)
    step_06_compliant = models.BooleanField(null=True, blank=True)
    step_06_comments = models.TextField(blank=True)
    step_07_compliant = models.BooleanField(null=True, blank=True)
    step_07_comments = models.TextField(blank=True)
    step_08_compliant = models.BooleanField(null=True, blank=True)
    step_08_comments = models.TextField(blank=True)
    step_09_compliant = models.BooleanField(null=True, blank=True)
    step_09_comments = models.TextField(blank=True)
    step_10_compliant = models.BooleanField(null=True, blank=True)
    step_10_comments = models.TextField(blank=True)
    step_11_compliant = models.BooleanField(null=True, blank=True)
    step_11_comments = models.TextField(blank=True)
    step_12_compliant = models.BooleanField(null=True, blank=True)
    step_12_comments = models.TextField(blank=True)
    step_13_compliant = models.BooleanField(null=True, blank=True)
    step_13_comments = models.TextField(blank=True)
    step_14_compliant = models.BooleanField(null=True, blank=True)
    step_14_comments = models.TextField(blank=True)
    step_15_compliant = models.BooleanField(null=True, blank=True)
    step_15_comments = models.TextField(blank=True)
    step_16_compliant = models.BooleanField(null=True, blank=True)
    step_16_comments = models.TextField(blank=True)
    step_17_compliant = models.BooleanField(null=True, blank=True)
    step_17_comments = models.TextField(blank=True)
    step_18_compliant = models.BooleanField(null=True, blank=True)
    step_18_comments = models.TextField(blank=True)
    step_19_compliant = models.BooleanField(null=True, blank=True)
    step_19_comments = models.TextField(blank=True)
    step_20_compliant = models.BooleanField(null=True, blank=True)
    step_20_comments = models.TextField(blank=True)
    step_21_compliant = models.BooleanField(null=True, blank=True)
    step_21_comments = models.TextField(blank=True)
    step_22_compliant = models.BooleanField(null=True, blank=True)
    step_22_comments = models.TextField(blank=True)
    step_23_compliant = models.BooleanField(null=True, blank=True)
    step_23_comments = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.get_pto_type_display()} - {self.employee_name}'


class CCVCriticalControlVerification(models.Model):
    CCV_TYPE_CHOICES = [
        ('mobile_equipment', 'Mobile Equipment CCV'),
        ('rotating_equipment', 'Rotating Equipment CCV'),
        ('fall_from_heights', 'Fall From Heights CCV'),
        ('confined_space', 'Confined Space CCV'),
        ('fall_of_ground', 'Fall of Ground CCV'),
        ('hazardous_substances_chemicals', 'Hazardous Substances and Chemicals CCV'),
        ('stored_energy', 'Stored Energy CCV'),
        ('lifting', 'Lifting CCV'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ccv_critical_control_verifications')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='ccv_critical_control_verifications')
    ccv_type = models.CharField(max_length=60, choices=CCV_TYPE_CHOICES, default='mobile_equipment')

    assessor_name = models.CharField(max_length=255)
    assessment_datetime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    section = models.CharField(max_length=255, blank=True)

    step_01_compliant = models.BooleanField(null=True, blank=True)
    step_01_comments = models.TextField(blank=True)
    step_02_compliant = models.BooleanField(null=True, blank=True)
    step_02_comments = models.TextField(blank=True)
    step_03_compliant = models.BooleanField(null=True, blank=True)
    step_03_comments = models.TextField(blank=True)
    step_04_compliant = models.BooleanField(null=True, blank=True)
    step_04_comments = models.TextField(blank=True)
    step_05_compliant = models.BooleanField(null=True, blank=True)
    step_05_comments = models.TextField(blank=True)
    step_06_compliant = models.BooleanField(null=True, blank=True)
    step_06_comments = models.TextField(blank=True)
    step_07_compliant = models.BooleanField(null=True, blank=True)
    step_07_comments = models.TextField(blank=True)
    step_08_compliant = models.BooleanField(null=True, blank=True)
    step_08_comments = models.TextField(blank=True)
    step_09_compliant = models.BooleanField(null=True, blank=True)
    step_09_comments = models.TextField(blank=True)
    step_10_compliant = models.BooleanField(null=True, blank=True)
    step_10_comments = models.TextField(blank=True)
    step_11_compliant = models.BooleanField(null=True, blank=True)
    step_11_comments = models.TextField(blank=True)
    step_12_compliant = models.BooleanField(null=True, blank=True)
    step_12_comments = models.TextField(blank=True)
    step_13_compliant = models.BooleanField(null=True, blank=True)
    step_13_comments = models.TextField(blank=True)
    step_14_compliant = models.BooleanField(null=True, blank=True)
    step_14_comments = models.TextField(blank=True)
    step_15_compliant = models.BooleanField(null=True, blank=True)
    step_15_comments = models.TextField(blank=True)
    step_16_compliant = models.BooleanField(null=True, blank=True)
    step_16_comments = models.TextField(blank=True)
    step_17_compliant = models.BooleanField(null=True, blank=True)
    step_17_comments = models.TextField(blank=True)
    step_18_compliant = models.BooleanField(null=True, blank=True)
    step_18_comments = models.TextField(blank=True)
    step_19_compliant = models.BooleanField(null=True, blank=True)
    step_19_comments = models.TextField(blank=True)
    step_20_compliant = models.BooleanField(null=True, blank=True)
    step_20_comments = models.TextField(blank=True)
    step_21_compliant = models.BooleanField(null=True, blank=True)
    step_21_comments = models.TextField(blank=True)
    step_22_compliant = models.BooleanField(null=True, blank=True)
    step_22_comments = models.TextField(blank=True)
    step_23_compliant = models.BooleanField(null=True, blank=True)
    step_23_comments = models.TextField(blank=True)

    action_1 = models.CharField(max_length=255, blank=True)
    action_1_responsible = models.CharField(max_length=255, blank=True)
    action_1_due_date = models.DateField(null=True, blank=True)
    action_2 = models.CharField(max_length=255, blank=True)
    action_2_responsible = models.CharField(max_length=255, blank=True)
    action_2_due_date = models.DateField(null=True, blank=True)
    action_3 = models.CharField(max_length=255, blank=True)
    action_3_responsible = models.CharField(max_length=255, blank=True)
    action_3_due_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.get_ccv_type_display()} - {self.assessor_name}'

# Safety Checklists (Daily, Weekly, Monthly - ISO 45001 aligned)
class SafetyChecklist(models.Model):
    TYPE_CHOICES = [
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
        ('Mobile Equipment', 'Mobile Equipment Checklist'),
        ('Lighting Tower', 'Lighting Tower Inspection Checklist'),
        ('Drilling Machine Surface', 'Drilling Machine Surface Checklist'),
        ('Environmental', 'Environmental Checklist'),
        ('Generator', 'Generator Checklist'),
        ('Other Operational', 'Other Operational Checklist'),
    ]

    OPERATIONAL_STATUS_CHOICES = [
        ('good', 'Good'),
        ('needs_attention', 'Needs Attention'),
        ('out_of_service', 'Out Of Service'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='safety_checklists')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='safety_checklists')
    checklist_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    checklist_title = models.CharField(max_length=255, blank=True)
    equipment_id = models.CharField(max_length=120, blank=True)
    inspection_area = models.CharField(max_length=255, blank=True)
    document_number = models.CharField(max_length=50, blank=True)
    revision_number = models.CharField(max_length=20, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    document_status = models.CharField(max_length=30, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    area_name = models.CharField(max_length=255, blank=True)
    operator_name = models.CharField(max_length=255, blank=True)
    supervisor_name = models.CharField(max_length=255, blank=True)
    drill_rig_number = models.CharField(max_length=100, blank=True)
    lighting_tower_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    completed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date_completed = models.DateField(default=date.today)
    ppe_inspection = models.BooleanField(default=False)
    fire_safety_check = models.BooleanField(default=False)
    equipment_condition = models.BooleanField(default=False)
    emergency_exits_clear = models.BooleanField(default=False)
    safety_signage_visible = models.BooleanField(default=False)
    first_aid_kit_stocked = models.BooleanField(default=False)
    housekeeping_checked = models.BooleanField(default=False)
    step_01_compliant = models.BooleanField(null=True, blank=True)
    step_01_comments = models.TextField(blank=True)
    step_02_compliant = models.BooleanField(null=True, blank=True)
    step_02_comments = models.TextField(blank=True)
    step_03_compliant = models.BooleanField(null=True, blank=True)
    step_03_comments = models.TextField(blank=True)
    step_04_compliant = models.BooleanField(null=True, blank=True)
    step_04_comments = models.TextField(blank=True)
    step_05_compliant = models.BooleanField(null=True, blank=True)
    step_05_comments = models.TextField(blank=True)
    step_06_compliant = models.BooleanField(null=True, blank=True)
    step_06_comments = models.TextField(blank=True)
    step_07_compliant = models.BooleanField(null=True, blank=True)
    step_07_comments = models.TextField(blank=True)
    step_08_compliant = models.BooleanField(null=True, blank=True)
    step_08_comments = models.TextField(blank=True)
    step_09_compliant = models.BooleanField(null=True, blank=True)
    step_09_comments = models.TextField(blank=True)
    step_10_compliant = models.BooleanField(null=True, blank=True)
    step_10_comments = models.TextField(blank=True)
    step_11_compliant = models.BooleanField(null=True, blank=True)
    step_11_comments = models.TextField(blank=True)
    step_12_compliant = models.BooleanField(null=True, blank=True)
    step_12_comments = models.TextField(blank=True)
    step_13_compliant = models.BooleanField(null=True, blank=True)
    step_13_comments = models.TextField(blank=True)
    step_14_compliant = models.BooleanField(null=True, blank=True)
    step_14_comments = models.TextField(blank=True)
    step_15_compliant = models.BooleanField(null=True, blank=True)
    step_15_comments = models.TextField(blank=True)
    step_16_compliant = models.BooleanField(null=True, blank=True)
    step_16_comments = models.TextField(blank=True)
    step_17_compliant = models.BooleanField(null=True, blank=True)
    step_17_comments = models.TextField(blank=True)
    step_18_compliant = models.BooleanField(null=True, blank=True)
    step_18_comments = models.TextField(blank=True)
    step_19_compliant = models.BooleanField(null=True, blank=True)
    step_19_comments = models.TextField(blank=True)
    step_20_compliant = models.BooleanField(null=True, blank=True)
    step_20_comments = models.TextField(blank=True)
    step_21_compliant = models.BooleanField(null=True, blank=True)
    step_21_comments = models.TextField(blank=True)
    step_22_compliant = models.BooleanField(null=True, blank=True)
    step_22_comments = models.TextField(blank=True)
    step_23_compliant = models.BooleanField(null=True, blank=True)
    step_23_comments = models.TextField(blank=True)
    step_24_compliant = models.BooleanField(null=True, blank=True)
    step_24_comments = models.TextField(blank=True)
    step_25_compliant = models.BooleanField(null=True, blank=True)
    step_25_comments = models.TextField(blank=True)
    step_26_compliant = models.BooleanField(null=True, blank=True)
    step_26_comments = models.TextField(blank=True)
    step_27_compliant = models.BooleanField(null=True, blank=True)
    step_27_comments = models.TextField(blank=True)
    step_28_compliant = models.BooleanField(null=True, blank=True)
    step_28_comments = models.TextField(blank=True)
    step_29_compliant = models.BooleanField(null=True, blank=True)
    step_29_comments = models.TextField(blank=True)
    step_30_compliant = models.BooleanField(null=True, blank=True)
    step_30_comments = models.TextField(blank=True)
    step_31_compliant = models.BooleanField(null=True, blank=True)
    step_31_comments = models.TextField(blank=True)
    step_32_compliant = models.BooleanField(null=True, blank=True)
    step_32_comments = models.TextField(blank=True)
    step_33_compliant = models.BooleanField(null=True, blank=True)
    step_33_comments = models.TextField(blank=True)
    step_34_compliant = models.BooleanField(null=True, blank=True)
    step_34_comments = models.TextField(blank=True)
    step_35_compliant = models.BooleanField(null=True, blank=True)
    step_35_comments = models.TextField(blank=True)
    step_36_compliant = models.BooleanField(null=True, blank=True)
    step_36_comments = models.TextField(blank=True)
    step_37_compliant = models.BooleanField(null=True, blank=True)
    step_37_comments = models.TextField(blank=True)
    step_38_compliant = models.BooleanField(null=True, blank=True)
    step_38_comments = models.TextField(blank=True)
    step_39_compliant = models.BooleanField(null=True, blank=True)
    step_39_comments = models.TextField(blank=True)
    step_40_compliant = models.BooleanField(null=True, blank=True)
    step_40_comments = models.TextField(blank=True)
    step_41_compliant = models.BooleanField(null=True, blank=True)
    step_41_comments = models.TextField(blank=True)
    step_42_compliant = models.BooleanField(null=True, blank=True)
    step_42_comments = models.TextField(blank=True)
    step_43_compliant = models.BooleanField(null=True, blank=True)
    step_43_comments = models.TextField(blank=True)
    step_44_compliant = models.BooleanField(null=True, blank=True)
    step_44_comments = models.TextField(blank=True)
    step_45_compliant = models.BooleanField(null=True, blank=True)
    step_45_comments = models.TextField(blank=True)
    step_46_compliant = models.BooleanField(null=True, blank=True)
    step_46_comments = models.TextField(blank=True)
    step_47_compliant = models.BooleanField(null=True, blank=True)
    step_47_comments = models.TextField(blank=True)
    operational_status = models.CharField(max_length=20, choices=OPERATIONAL_STATUS_CHOICES, blank=True)
    findings = models.TextField(blank=True)
    actions_required = models.TextField(blank=True)
    verified_by = models.CharField(max_length=255, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    operator_signature = models.CharField(max_length=255, blank=True)
    site_supervisor_signature = models.CharField(max_length=255, blank=True)
    maintenance_supervisor_signature = models.CharField(max_length=255, blank=True)
    deviation_date = models.DateField(null=True, blank=True)
    deviation_problem = models.TextField(blank=True)
    deviation_reported_to = models.CharField(max_length=255, blank=True)
    deviation_action_taken = models.TextField(blank=True)
    comments = models.TextField(blank=True, null=True)
    checklist_file = models.FileField(upload_to='checklists/files/', blank=True, null=True)  # <-- Add this

    class Meta:
        ordering = ('-date_completed',)

    @property
    def compliance_score(self):
        """Percentage of answered steps that are compliant."""
        answered = [
            getattr(self, f'step_{i:02d}_compliant')
            for i in range(1, 48)
            if getattr(self, f'step_{i:02d}_compliant') is not None
        ]
        if not answered:
            return None
        return round(sum(1 for v in answered if v) / len(answered) * 100, 1)

    def __str__(self):
        return f'{self.checklist_type} - {self.site or "No site"}'


class ToolboxTalk(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='toolbox_talks')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='toolbox_talks')
    title = models.CharField(max_length=255)
    talk_date = models.DateField(default=date.today)
    facilitator_name = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    work_group = models.CharField(max_length=255, blank=True)
    conducted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='toolbox_talks')
    topic_details = models.TextField(blank=True)
    hazards_discussed = models.TextField(blank=True)
    controls_agreed = models.TextField(blank=True)
    attendance_count = models.PositiveIntegerField(default=0)
    attendees = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_owner = models.CharField(max_length=255, blank=True)
    follow_up_due_date = models.DateField(null=True, blank=True)
    toolbox_file = models.FileField(upload_to='toolbox_talks/files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-talk_date', '-id')

    def __str__(self):
        return f'{self.title} ({self.talk_date})'

# Certification Tracking
class Certification(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='certifications')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='certifications')
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    issuing_body = models.CharField(max_length=255)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    certificate_file = models.FileField(upload_to='certifications/', blank=True, null=True)  # Already present

# Contractor Onboarding
class Contractor(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='contractors')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='contractors')
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    id_document = models.FileField(upload_to='contractors/ids/', blank=True, null=True)  # Already present
    certifications = models.ManyToManyField(Certification, blank=True)
    onboarded = models.BooleanField(default=False)
    onboarding_date = models.DateField(auto_now_add=True)
    contractor_file = models.FileField(upload_to='contractors/files/', blank=True, null=True)  # <-- Add this

# Employee Model (to track internal employees separately from User auth)
class Employee(models.Model):
    SCOPE_CHOICES = [
        ('local', 'Local'),
        ('regional', 'Regional'),
        ('national', 'National'),
        ('expatriate', 'Expatriate'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='employees')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profiles')
    name = models.CharField(max_length=255, default="Unknown")
    position = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    emergency_contact = models.CharField(max_length=255)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='local')
    expert_traits = models.TextField(blank=True, help_text='Comma-separated list of expertise areas')
    certifications = models.ManyToManyField(Certification, blank=True, related_name="employees")
    employee_file = models.FileField(upload_to='employees/files/', blank=True, null=True)

# Objectives Model
class Objective(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='objectives')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='objectives')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target = models.TextField()
    current = models.PositiveIntegerField(default=0)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, choices=[
        ('not started', 'Not Started'),
        ('in progress', 'In Progress'),
        ('completed', 'Completed')
    ], default='not started')
    due_date = models.DateField(null=True, blank=True)
    objective_file = models.FileField(upload_to='objectives/files/', blank=True, null=True)  # <-- Add this

    def progress_percent(self):
        if self.target > 0:
            return min(100, int((self.current / self.target) * 100))
        return 0

    def __str__(self):
        return self.name

# Training Matrix
class TrainingMatrix(models.Model):
    TRAINING_STATUS_CHOICES = [
        ('not started', 'Not Started'),
        ('in progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='training_items')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='training_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_employees = models.ManyToManyField(Employee, related_name="trainings")
    training_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TRAINING_STATUS_CHOICES, default='not started')
    training_material = models.FileField(upload_to='training/files/', blank=True, null=True)
    certificate_required = models.BooleanField(default=False)
    certificate_upload = models.FileField(upload_to='training/certificates/', blank=True, null=True)

    def __str__(self):
        return self.title
    def progress_percent(self):
        if self.status == 'completed':
            return 100
        elif self.status == 'in progress':
            return 50
        return 0


class ScheduleItem(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ]

    MODULE_CHOICES = [
        ('checklist', 'Checklist'),
        ('inspection', 'Inspection'),
        ('training', 'Training'),
        ('medical', 'Medical'),
        ('audit', 'Audit'),
        ('custom', 'Custom'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='schedule_items')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='schedule_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=30, choices=MODULE_CHOICES, default='custom')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    interval_value = models.PositiveIntegerField(default=1)
    starts_on = models.DateField()
    next_due_date = models.DateField()
    last_completed_on = models.DateField(null=True, blank=True)
    reminder_days_before = models.PositiveIntegerField(default=2)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_schedule_items')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_schedule_items')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def _delta_days(self):
        if self.frequency == 'daily':
            return 1 * self.interval_value
        if self.frequency == 'weekly':
            return 7 * self.interval_value
        if self.frequency == 'monthly':
            return 30 * self.interval_value
        if self.frequency == 'quarterly':
            return 90 * self.interval_value
        if self.frequency == 'yearly':
            return 365 * self.interval_value
        return max(1, self.interval_value)

    def compute_next_due_date(self, from_date=None):
        base = from_date or self.next_due_date
        return base + timedelta(days=self._delta_days())

    def mark_completed(self, completed_on):
        self.last_completed_on = completed_on
        self.next_due_date = self.compute_next_due_date(completed_on)
        self.save(update_fields=['last_completed_on', 'next_due_date', 'updated_at'])


class Reminder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    CHANNEL_CHOICES = [
        ('in_app', 'In App'),
        ('email', 'Email'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='reminders')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='reminders')
    schedule = models.ForeignKey(ScheduleItem, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    due_date = models.DateField()
    remind_on = models.DateField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

    def save(self, *args, **kwargs):
        if self.schedule_id:
            self.tenant = self.schedule.tenant
            self.site = self.schedule.site
        super().save(*args, **kwargs)


class CAPAAction(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_review', 'Pending Review'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='capa_actions')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='capa_actions')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    due_date = models.DateField(null=True, blank=True)
    closed_on = models.DateField(null=True, blank=True)

    root_cause = models.TextField(blank=True)
    immediate_correction = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    preventive_action = models.TextField(blank=True)
    effectiveness_review = models.TextField(blank=True)

    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_capa_actions')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_capa_actions')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_capa_actions')
    verification_date = models.DateField(null=True, blank=True)

    incident = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True, blank=True, related_name='capa_actions')
    observation = models.ForeignKey(Observation, on_delete=models.SET_NULL, null=True, blank=True, related_name='capa_actions')
    safety_checklist = models.ForeignKey(SafetyChecklist, on_delete=models.SET_NULL, null=True, blank=True, related_name='capa_actions')
    objective = models.ForeignKey(Objective, on_delete=models.SET_NULL, null=True, blank=True, related_name='capa_actions')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class MedicalProfile(models.Model):
    FITNESS_CHOICES = [
        ('fit', 'Fit for Duty'),
        ('fit_with_restrictions', 'Fit with Restrictions'),
        ('unfit', 'Temporarily Unfit'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='medical_profiles')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_profiles')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='medical_profiles')
    fitness_status = models.CharField(max_length=30, choices=FITNESS_CHOICES, default='fit')
    restrictions = models.TextField(blank=True)
    surveillance_required = models.BooleanField(default=False)
    next_medical_due = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tenant', 'employee')

    def __str__(self):
        return f"{self.employee.name} - {self.get_fitness_status_display()}"


class MedicalAssessment(models.Model):
    OUTCOME_CHOICES = [
        ('fit', 'Fit for Duty'),
        ('fit_with_restrictions', 'Fit with Restrictions'),
        ('unfit', 'Unfit'),
        ('follow_up_required', 'Follow-up Required'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='medical_assessments')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_assessments')
    profile = models.ForeignKey(MedicalProfile, on_delete=models.CASCADE, related_name='assessments')
    exam_type = models.CharField(max_length=120)
    assessment_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES)
    provider = models.CharField(max_length=255, blank=True)
    assessor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_assessments')
    report_file = models.FileField(upload_to='medical/reports/', blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.employee.name} - {self.exam_type}"

    def save(self, *args, **kwargs):
        if self.profile_id:
            self.tenant = self.profile.tenant
            self.site = self.profile.site
        super().save(*args, **kwargs)


class KPIDailySnapshot(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='kpi_snapshots')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpi_snapshots')
    snapshot_date = models.DateField()

    incident_count = models.PositiveIntegerField(default=0)
    open_capa_count = models.PositiveIntegerField(default=0)
    overdue_capa_count = models.PositiveIntegerField(default=0)
    observation_count = models.PositiveIntegerField(default=0)
    checklist_count = models.PositiveIntegerField(default=0)
    training_completed_count = models.PositiveIntegerField(default=0)
    training_total_count = models.PositiveIntegerField(default=0)
    medical_due_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'site', 'snapshot_date')
        ordering = ('-snapshot_date',)

    def __str__(self):
        site_name = self.site.name if self.site else 'All Sites'
        return f"{self.tenant.name} - {site_name} - {self.snapshot_date}"


class AnalyticsWarehouseDaily(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='analytics_daily_facts')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='analytics_daily_facts')
    snapshot_date = models.DateField()

    incident_count = models.PositiveIntegerField(default=0)
    open_capa_count = models.PositiveIntegerField(default=0)
    overdue_capa_count = models.PositiveIntegerField(default=0)
    observation_count = models.PositiveIntegerField(default=0)
    checklist_count = models.PositiveIntegerField(default=0)
    training_completed_count = models.PositiveIntegerField(default=0)
    training_total_count = models.PositiveIntegerField(default=0)
    medical_due_count = models.PositiveIntegerField(default=0)

    training_completion_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    overdue_capa_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tenant', 'site', 'snapshot_date')
        ordering = ('-snapshot_date',)

    def __str__(self):
        site_name = self.site.name if self.site else 'All Sites'
        return f"Warehouse {self.tenant.name} - {site_name} - {self.snapshot_date}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    site = models.ForeignKey(SiteProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=120)
    object_id = models.CharField(max_length=50)
    object_repr = models.CharField(max_length=255)
    change_summary = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.model_name}:{self.object_id} - {self.action}"


# Attendance Tracking
class AttendanceRecord(models.Model):
    """Daily attendance tracking with man-hours calculation."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='attendance_records')
    site_project = models.ForeignKey(SiteProject, on_delete=models.CASCADE, related_name='attendance_records')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration_minutes = models.PositiveIntegerField(default=0, help_text='Break time in minutes')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('site_project', 'employee', 'date')
        ordering = ('-date', 'employee')

    def get_man_hours(self):
        """Calculate man-hours for the day."""
        from datetime import datetime
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        duration_minutes = (end - start).total_seconds() / 60
        net_minutes = duration_minutes - self.break_duration_minutes
        return round(max(0, net_minutes) / 60, 2)  # Return hours

    def __str__(self):
        return f"{self.employee.name} - {self.date} ({self.get_man_hours()}h)"


class MonthlySiteHealthReport(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='monthly_site_health_reports')
    site_project = models.ForeignKey(SiteProject, on_delete=models.CASCADE, related_name='monthly_site_health_reports')
    report_month = models.PositiveIntegerField(choices=[
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ], default=1)
    report_year = models.PositiveIntegerField(default=2026)
    safety_summary = models.TextField(blank=True)
    incident_count = models.PositiveIntegerField(default=0)
    near_miss_count = models.PositiveIntegerField(default=0)
    observation_count = models.PositiveIntegerField(default=0)
    inspection_count = models.PositiveIntegerField(default=0)
    training_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    man_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='monthly_health_reports_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tenant', 'site_project', 'report_month', 'report_year')
        ordering = ('-report_year', '-report_month', '-site_project')

    def __str__(self):
        month_name = dict(self._meta.get_field('report_month').choices).get(self.report_month, str(self.report_month))
        return f"{self.site_project.name} {month_name} {self.report_year}"
