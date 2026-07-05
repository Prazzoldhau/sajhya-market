from functools import wraps

from django.shortcuts import redirect

from .models import Ward


def ward_required(view_func):
    """Gates a ward's request-form behind its PIN. Mirrors summit_app's
    table_required -- a shared ICU/HDU computer bookmarks the ward's URL
    (keyed by access_token), and a PIN is the second factor rather than
    per-person login, since there's no individual identity to model for a
    shared ward workstation."""

    @wraps(view_func)
    def wrapper(request, token, *args, **kwargs):
        ward_id = request.session.get("ward_id")
        ward = None
        if ward_id:
            ward = Ward.objects.filter(id=ward_id, access_token=token).first()
        if ward is None:
            return redirect("ward-login", token=token)
        request.ward = ward
        return view_func(request, token, *args, **kwargs)

    return wrapper
