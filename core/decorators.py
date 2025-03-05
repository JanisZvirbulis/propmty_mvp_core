from functools import wraps
from django.http import Http404

def tenant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            raise Http404("Company not found")
        return view_func(request, *args, **kwargs)
    return wrapper