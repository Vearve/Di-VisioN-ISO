#!/bin/bash
set -o errexit

echo "Running migrations..."
python manage.py migrate

echo "Ensuring default admin user and tenant exist..."
python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from safety_mvp.ohs.models import Tenant, TenantMembership, SubscriptionPlan
import os

User = get_user_model()
username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "ChangeMeNow123!")

# Create/get admin user
if not User.objects.filter(username=username).exists():
    admin_user = User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created default admin user: {username}")
else:
    admin_user = User.objects.get(username=username)
    print(f"Default admin user already exists: {username}")

# Create default subscription plan if it doesn't exist
plan, _ = SubscriptionPlan.objects.get_or_create(
    code='default',
    defaults={
        'name': 'Default Plan',
        'monthly_price': 0,
        'max_users': 100,
        'max_sites': 50,
        'is_active': True,
    }
)
print(f"Subscription plan ready: {plan.name}")

# Create default tenant if it doesn't exist
tenant, created = Tenant.objects.get_or_create(
    slug='default',
    defaults={
        'name': 'Default Tenant',
        'is_active': True,
    }
)
if created:
    print(f"Created default tenant: {tenant.name}")
else:
    print(f"Default tenant already exists: {tenant.name}")

# Create default subscription for the tenant
from django.utils.timezone import localdate
from datetime import timedelta
tenant.subscriptions.get_or_create(
    plan=plan,
    defaults={
        'status': 'active',
        'start_date': localdate(),
        'end_date': localdate() + timedelta(days=365),
        'renewal_date': localdate() + timedelta(days=365),
        'auto_renew': True,
    }
)

# Add admin user to the tenant as 'admin' role if not already a member
membership, created = TenantMembership.objects.get_or_create(
    tenant=tenant,
    user=admin_user,
    defaults={
        'role': 'admin',
        'is_active': True,
    }
)
if created:
    print(f"Added {admin_user.username} to tenant {tenant.name} as 'admin'")
else:
    if membership.role != 'admin':
        membership.role = 'admin'
        membership.is_active = True
        membership.save()
        print(f"Updated {admin_user.username} role to 'admin' in tenant {tenant.name}")
    else:
        print(f"User {admin_user.username} already has 'admin' role in tenant {tenant.name}")
PY

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
