from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import Table


def table_required(view_func):
    """Gates a table's pages behind its PIN. Mirrors the lightweight,
    ad-hoc access-check style used elsewhere in this project
    (enterprise_account/decorators.py) rather than full Django auth --
    there's no per-person identity to model here, just 4 shared laptops."""

    @wraps(view_func)
    def wrapper(request, table_number, *args, **kwargs):
        table_id = request.session.get("summit_table_id")
        table = None
        if table_id:
            table = Table.objects.filter(id=table_id, number=table_number).first()
        if table is None:
            # Not logged in, or logged into a *different* table than this URL's.
            # Don't touch the session here -- a facilitator who is legitimately
            # logged into Table 1 and merely visits Table 2's URL should just be
            # bounced to Table 2's login, not silently logged out of Table 1.
            return redirect("summit-table-login", table_number=table_number)
        request.summit_table = table
        return view_func(request, table_number, *args, **kwargs)

    return wrapper


def summit_staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            messages.error(request, "Staff login required.")
            return redirect(f"/acc/login/?next={request.path}")
        return view_func(request, *args, **kwargs)

    return wrapper
