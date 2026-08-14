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


# Cropped from the composite "logo for sajhya.png" the user provided
# (2026-08-13) -- one oval photo per category, static/categorized_product/
# category_icons/. Only these 11 exist; categories not in this dict fall
# back to their `icon` emoji (or the default) in the template.
CATEGORY_ICON_IMAGES = {
    'Behavioural Therapy': 'behavioural-therapy.png',
    'Bioderma': 'bioderma.png',
    'Diapers': 'diapers.png',
    'Electrical Therapy': 'electrical-therapy.png',
    'Exercise Equipment': 'exercise-equipment.png',
    'Fixderma': 'fixderma.png',
    'Gels & Lubricants': 'gels-lubricants.png',
    'Hospital Linens & Accessories': 'hospital-linens-accessories.png',
    'Kleida': 'kleida.png',
    'Lab Coats': 'lab-coats.png',
    'Massage Tools': 'massage-tools.png',
}


@register.filter(name='category_icon_image')
def category_icon_image(category_name):
    """Static URL for that category's cropped photo, or '' if none exists
    yet -- template falls back to the emoji icon in that case."""
    filename = CATEGORY_ICON_IMAGES.get(category_name)
    if not filename:
        return ''
    return f'{settings.STATIC_URL}categorized_product/category_icons/{quote(filename)}'
