#!/bin/bash
set -o errexit

echo "Running migrations..."
python manage.py migrate

echo "Ensuring default admin user exists..."
python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "ChangeMeNow123!")

if not User.objects.filter(username=username).exists():
	User.objects.create_superuser(username=username, email=email, password=password)
	print(f"Created default admin user: {username}")
else:
	print(f"Default admin user already exists: {username}")
PY

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
