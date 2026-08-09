from urllib.parse import quote

from django import template
from django.conf import settings

register = template.Library()


@register.filter(name='plain_static')
def plain_static(image_path):
    """Build a /static/... URL directly from STATIC_URL, deliberately
    bypassing collectstatic's manifest (staticfiles.json) via
    {% static %}/ManifestStaticFilesStorage.

    On production that manifest is stale relative to what's actually on
    disk for these dynamically-named product images: the hashed
    filenames it points to 404, while the plain (unhashed) filename
    works. physio_api_app._product_image_url and
    patient_app._image_url already use this same workaround for the
    mobile API -- this filter brings the web marketplace/pharmacy
    templates in line with that, since they were still using
    {% static product.image %} and hitting the same stale-manifest 404s.
    """
    if not image_path:
        return ''
    return f'{settings.STATIC_URL}{quote(str(image_path), safe="/")}'
