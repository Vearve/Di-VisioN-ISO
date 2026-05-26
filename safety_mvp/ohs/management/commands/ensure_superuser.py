import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Ensure a superuser exists from environment variables.'

    def handle(self, *args, **options):
        required_keys = (
            'DJANGO_SUPERUSER_USERNAME',
            'DJANGO_SUPERUSER_EMAIL',
            'DJANGO_SUPERUSER_PASSWORD',
        )
        missing = [key for key in required_keys if not os.getenv(key)]

        if missing:
            raise CommandError(
                'Missing required environment variables: ' + ', '.join(missing)
            )

        username = os.environ['DJANGO_SUPERUSER_USERNAME']
        email = os.environ['DJANGO_SUPERUSER_EMAIL']
        password = os.environ['DJANGO_SUPERUSER_PASSWORD']

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )

        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))
            return

        changed = False

        if user.email != email:
            user.email = email
            changed = True

        if not user.is_staff:
            user.is_staff = True
            changed = True

        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        user.set_password(password)
        changed = True

        if changed:
            user.save()

        self.stdout.write(self.style.SUCCESS(f'Ensured superuser: {username}'))
