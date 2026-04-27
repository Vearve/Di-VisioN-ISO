from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import localdate

from safety_mvp.ohs.models import (
    CAPAAction,
    AnalyticsWarehouseDaily,
    Incident,
    KPIDailySnapshot,
    MedicalProfile,
    Observation,
    SafetyChecklist,
    SiteProject,
    Tenant,
    TrainingMatrix,
)


class Command(BaseCommand):
    help = 'Capture daily KPI snapshots for all tenants and sites.'

    def handle(self, *args, **options):
        today = localdate()

        for tenant in Tenant.objects.filter(is_active=True):
            self._capture_for_scope(tenant, None, today)
            for site in SiteProject.objects.filter(tenant=tenant):
                self._capture_for_scope(tenant, site, today)

        self.stdout.write(self.style.SUCCESS('KPI snapshots captured successfully.'))

    def _capture_for_scope(self, tenant, site, snapshot_date):
        incidents = Incident.objects.filter(tenant=tenant)
        capa = CAPAAction.objects.filter(tenant=tenant)
        observations = Observation.objects.filter(tenant=tenant)
        checklists = SafetyChecklist.objects.filter(tenant=tenant)
        training = TrainingMatrix.objects.filter(tenant=tenant)
        medical = MedicalProfile.objects.filter(tenant=tenant)

        if site is not None:
            incidents = incidents.filter(site=site)
            capa = capa.filter(site=site)
            observations = observations.filter(site=site)
            checklists = checklists.filter(site=site)
            training = training.filter(site=site)
            medical = medical.filter(site=site)

        training_total = training.count()
        training_completed = training.filter(status='completed').count()

        snapshot_values = {
            'incident_count': incidents.count(),
            'open_capa_count': capa.exclude(status='closed').count(),
            'overdue_capa_count': capa.exclude(status='closed').filter(due_date__lt=snapshot_date).count(),
            'observation_count': observations.count(),
            'checklist_count': checklists.count(),
            'training_completed_count': training_completed,
            'training_total_count': training_total,
            'medical_due_count': medical.filter(
                next_medical_due__isnull=False,
                next_medical_due__lte=snapshot_date + timedelta(days=30),
            ).count(),
        }

        KPIDailySnapshot.objects.update_or_create(
            tenant=tenant,
            site=site,
            snapshot_date=snapshot_date,
            defaults=snapshot_values,
        )

        training_total = snapshot_values['training_total_count']
        open_capa = snapshot_values['open_capa_count']
        training_completion_rate = (
            snapshot_values['training_completed_count'] / training_total
            if training_total
            else 0
        )
        overdue_capa_rate = (
            snapshot_values['overdue_capa_count'] / open_capa
            if open_capa
            else 0
        )

        warehouse_values = {
            **snapshot_values,
            'training_completion_rate': training_completion_rate,
            'overdue_capa_rate': overdue_capa_rate,
        }

        AnalyticsWarehouseDaily.objects.update_or_create(
            tenant=tenant,
            site=site,
            snapshot_date=snapshot_date,
            defaults=warehouse_values,
        )
