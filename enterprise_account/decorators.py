from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from .models import EnterpriseStaff


def enterprise_role_required(roles=None):
    """Ensures the logged-in user has an active EnterpriseStaff membership,
    optionally restricted to specific roles. Attaches the membership to
    request.enterprise_membership for the view to use.

    Mirrors this codebase's ad hoc `request.user == obj.created_by` style
    (see clinic_account.views.claim_physio) rather than Django's
    Groups/Permissions framework, which isn't used anywhere else here.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            membership = EnterpriseStaff.objects.filter(
                user=request.user, is_active=True
            ).select_related('enterprise', 'department').first()
            if membership is None:
                messages.error(request, 'You are not a member of any enterprise.')
                return redirect('enterprise-onboarding')
            if roles is not None and membership.role not in roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('enterprise-dashboard')
            request.enterprise_membership = membership
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
