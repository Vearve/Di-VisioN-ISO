from django.core.management.base import BaseCommand

from safety_mvp.ohs.models import AnalyticsWarehouseDaily, KPIDailySnapshot


class Command(BaseCommand):
    help = 'Backfill analytics warehouse rows from KPI daily snapshots.'

    def handle(self, *args, **options):
        upserted = 0

        snapshots = KPIDailySnapshot.objects.select_related('tenant', 'site').all()
        for row in snapshots:
            training_total = row.training_total_count
            open_capa = row.open_capa_count

            training_completion_rate = (
                row.training_completed_count / training_total
                if training_total
                else 0
            )
            overdue_capa_rate = (
                row.overdue_capa_count / open_capa
                if open_capa
                else 0
            )

            defaults = {
                'incident_count': row.incident_count,
                'open_capa_count': row.open_capa_count,
                'overdue_capa_count': row.overdue_capa_count,
                'observation_count': row.observation_count,
                'checklist_count': row.checklist_count,
                'training_completed_count': row.training_completed_count,
                'training_total_count': row.training_total_count,
                'medical_due_count': row.medical_due_count,
                'training_completion_rate': training_completion_rate,
                'overdue_capa_rate': overdue_capa_rate,
            }

            AnalyticsWarehouseDaily.objects.update_or_create(
                tenant=row.tenant,
                site=row.site,
                snapshot_date=row.snapshot_date,
                defaults=defaults,
            )
            upserted += 1

        self.stdout.write(self.style.SUCCESS(f'Analytics warehouse backfill complete. Rows upserted: {upserted}'))
