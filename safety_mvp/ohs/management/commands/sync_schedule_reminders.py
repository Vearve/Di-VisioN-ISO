from datetime import timedelta

from django.core.management.base import BaseCommand

from safety_mvp.ohs.models import Reminder, ScheduleItem


class Command(BaseCommand):
    help = 'Create pending reminders from active schedule items for their next due dates.'

    def handle(self, *args, **options):
        created_count = 0

        schedules = ScheduleItem.objects.filter(is_active=True)
        for schedule in schedules:
            due_date = schedule.next_due_date
            remind_on = due_date - timedelta(days=schedule.reminder_days_before)

            exists = Reminder.objects.filter(
                schedule=schedule,
                due_date=due_date,
                status__in=['pending', 'sent'],
            ).exists()
            if exists:
                continue

            Reminder.objects.create(
                tenant=schedule.tenant,
                site=schedule.site,
                schedule=schedule,
                title=f'Reminder: {schedule.title}',
                message=f'{schedule.title} is due on {due_date}.',
                due_date=due_date,
                remind_on=remind_on,
                channel='in_app',
                status='pending',
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Schedule reminders synced. Created: {created_count}'))
