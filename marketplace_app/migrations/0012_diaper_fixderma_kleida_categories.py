from django.db import migrations


CATEGORIES = [
    ('Diapers', 'Baby diapers by brand and size'),
    ('Fixderma', 'Fixderma dermo-cosmetics'),
    ('Kleida', 'Kleida skin care'),
]


def create_categories(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    for name, description in CATEGORIES:
        Category.objects.get_or_create(name=name, defaults={'icon': '', 'description': description})


def remove_categories(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    Category.objects.filter(name__in=[name for name, _ in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace_app', '0011_bioderma_category'),
    ]

    operations = [
        migrations.RunPython(create_categories, remove_categories),
    ]
