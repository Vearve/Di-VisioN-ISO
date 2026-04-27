from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from safety_mvp.ohs.models import (
    CAPAAction,
    Certification,
    Contractor,
    Document,
    Employee,
    FLRA,
    FRA,
    Incident,
    JSA,
    KPIDailySnapshot,
    Material,
    MedicalAssessment,
    MedicalProfile,
    Objective,
    Observation,
    Reminder,
    SafetyChecklist,
    ScheduleItem,
    SiteProject,
    SubscriptionPlan,
    Tenant,
    TenantMembership,
    TenantSubscription,
    TrainingMatrix,
)


class Command(BaseCommand):
    help = 'Prepare rollout by creating a default tenant/subscription and backfilling tenant/site links.'

    tenant_models = [
        Incident,
        JSA,
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
        ScheduleItem,
        Reminder,
        CAPAAction,
        MedicalProfile,
        MedicalAssessment,
        KPIDailySnapshot,
    ]

    def add_arguments(self, parser):
        parser.add_argument('--tenant-name', default='Default Tenant')
        parser.add_argument('--tenant-slug', default='')
        parser.add_argument('--site-name', default='Main Site')
        parser.add_argument('--assign-site', action='store_true', help='Backfill empty site references with the default site.')

    @transaction.atomic
    def handle(self, *args, **options):
        tenant_name = options['tenant_name']
        tenant_slug = options['tenant_slug'] or slugify(tenant_name)
        site_name = options['site_name']
        assign_site = options['assign_site']

        tenant, _ = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={'name': tenant_name, 'is_active': True},
        )

        if tenant.name != tenant_name:
            tenant.name = tenant_name
            tenant.save(update_fields=['name', 'updated_at'])

        site, _ = SiteProject.objects.get_or_create(
            tenant=tenant,
            name=site_name,
            defaults={'status': 'active'},
        )

        starter_plan, _ = SubscriptionPlan.objects.get_or_create(
            code='starter',
            defaults={
                'name': 'Starter',
                'monthly_price': 0,
                'max_users': 50,
                'max_sites': 10,
                'is_active': True,
            },
        )

        if not TenantSubscription.objects.filter(tenant=tenant, status__in=['trial', 'active']).exists():
            TenantSubscription.objects.create(
                tenant=tenant,
                plan=starter_plan,
                status='trial',
                start_date=site.start_date or tenant.created_at.date(),
                auto_renew=True,
            )

        self._backfill_memberships(tenant)
        self._backfill_models(tenant, site, assign_site)

        self.stdout.write(self.style.SUCCESS('Rollout preparation complete.'))
        self.stdout.write(f'Tenant: {tenant.name} ({tenant.slug})')
        self.stdout.write(f'Default site: {site.name}')

    def _backfill_memberships(self, tenant):
        User = get_user_model()
        created_count = 0

        for user in User.objects.filter(is_superuser=True):
            _, created = TenantMembership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={'role': 'owner', 'is_active': True},
            )
            if created:
                created_count += 1

        for user in User.objects.filter(is_staff=True, is_superuser=False):
            _, created = TenantMembership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={'role': 'admin', 'is_active': True},
            )
            if created:
                created_count += 1

        if created_count:
            self.stdout.write(f'Created {created_count} tenant memberships.')

    def _backfill_models(self, tenant, site, assign_site):
        total_tenant_updates = 0
        total_site_updates = 0

        for model in self.tenant_models:
            tenant_updates = model.objects.filter(tenant__isnull=True).update(tenant=tenant)
            total_tenant_updates += tenant_updates

            site_updates = 0
            if assign_site and hasattr(model, 'site'):
                site_updates = model.objects.filter(tenant=tenant, site__isnull=True).update(site=site)
                total_site_updates += site_updates

            if tenant_updates or site_updates:
                self.stdout.write(
                    f'{model.__name__}: tenant backfill={tenant_updates}, site backfill={site_updates}'
                )

        self.stdout.write(f'Total tenant backfills: {total_tenant_updates}')
        self.stdout.write(f'Total site backfills: {total_site_updates}')
