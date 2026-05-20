from django.db.models import QuerySet

from .models import Tenant, TenantMembership


SESSION_TENANT_KEY = "current_tenant_id"
SESSION_SITE_KEY = "current_site_id"

ROLE_ORDER = {
    'auditor': 10,
    'worker': 20,
    'supervisor': 30,
    'site_manager': 40,
    'admin': 50,
    'owner': 60,
    'superuser': 100,
}


def user_tenants(user) -> QuerySet[Tenant]:
    """
    Return tenants accessible to user.
    - Superusers: all active tenants
    - Regular users: only tenants with active membership
    """
    if not user.is_authenticated:
        return Tenant.objects.none()
    if user.is_superuser:
        return Tenant.objects.filter(is_active=True).order_by('name')
    return Tenant.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        is_active=True,
    ).distinct().order_by('name')


def resolve_current_tenant(request):
    if not request.user.is_authenticated:
        return None

    tenants = user_tenants(request.user)
    if not tenants.exists():
        return None

    query_tenant_id = request.GET.get("tenant")
    if query_tenant_id:
        candidate = tenants.filter(id=query_tenant_id).first()
        if candidate:
            request.session[SESSION_TENANT_KEY] = candidate.id
            return candidate

    session_tenant_id = request.session.get(SESSION_TENANT_KEY)
    if session_tenant_id:
        candidate = tenants.filter(id=session_tenant_id).first()
        if candidate:
            return candidate

    default_tenant = tenants.order_by("id").first()
    if default_tenant:
        request.session[SESSION_TENANT_KEY] = default_tenant.id
    return default_tenant


def resolve_current_site(request, tenant=None):
    if tenant is None:
        return None

    available_sites = tenant.sites.filter(status='active').order_by('name')
    query_site_id = request.GET.get("site")

    if query_site_id == 'all':
        request.session.pop(SESSION_SITE_KEY, None)
        return None

    if query_site_id:
        candidate = available_sites.filter(id=query_site_id).first()
        if candidate:
            request.session[SESSION_SITE_KEY] = candidate.id
            return candidate

    session_site_id = request.session.get(SESSION_SITE_KEY)
    if session_site_id:
        candidate = available_sites.filter(id=session_site_id).first()
        if candidate:
            return candidate
        request.session.pop(SESSION_SITE_KEY, None)

    return None


def user_role_for_tenant(user, tenant):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "superuser"
    if tenant is None:
        return None
    membership = TenantMembership.objects.filter(
        user=user,
        tenant=tenant,
        is_active=True,
    ).first()
    return membership.role if membership else None


def has_minimum_role(user_role, minimum_role):
    if not user_role:
        return False
    return ROLE_ORDER.get(user_role, 0) >= ROLE_ORDER.get(minimum_role, 0)
