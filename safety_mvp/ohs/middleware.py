from .tenant_context import resolve_current_site, resolve_current_tenant


class CurrentTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_tenant = resolve_current_tenant(request)
        request.current_site = resolve_current_site(request, request.current_tenant)
        return self.get_response(request)
