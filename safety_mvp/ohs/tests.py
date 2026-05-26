import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class EnsureSuperuserCommandTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def tearDown(self):
        for key in (
            'DJANGO_SUPERUSER_USERNAME',
            'DJANGO_SUPERUSER_EMAIL',
            'DJANGO_SUPERUSER_PASSWORD',
        ):
            os.environ.pop(key, None)

    def test_creates_superuser_when_missing(self):
        username = 'auto-superuser'
        email = 'auto-superuser@example.com'
        password = 'test-password-123'

        with patch.dict(
            os.environ,
            {
                'DJANGO_SUPERUSER_USERNAME': username,
                'DJANGO_SUPERUSER_EMAIL': email,
                'DJANGO_SUPERUSER_PASSWORD': password,
            },
            clear=False,
        ):
            call_command('ensure_superuser')

        user = self.User.objects.get(username=username)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_is_idempotent_and_updates_existing_user(self):
        username = 'existing-superuser'
        user = self.User.objects.create_user(
            username=username,
            email='before@example.com',
            password='old-password',
        )

        with patch.dict(
            os.environ,
            {
                'DJANGO_SUPERUSER_USERNAME': username,
                'DJANGO_SUPERUSER_EMAIL': 'after@example.com',
                'DJANGO_SUPERUSER_PASSWORD': 'new-password',
            },
            clear=False,
        ):
            call_command('ensure_superuser')

        user.refresh_from_db()
        self.assertEqual(self.User.objects.filter(username=username).count(), 1)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.email, 'after@example.com')
        self.assertTrue(user.check_password('new-password'))

    def test_fails_fast_when_required_env_vars_missing(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in (
                'DJANGO_SUPERUSER_USERNAME',
                'DJANGO_SUPERUSER_EMAIL',
                'DJANGO_SUPERUSER_PASSWORD',
            ):
                os.environ.pop(key, None)

            with self.assertRaises(CommandError):
                call_command('ensure_superuser')
