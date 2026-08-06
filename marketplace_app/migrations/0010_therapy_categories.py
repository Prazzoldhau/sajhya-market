from django.db import migrations


THERAPY_CATEGORIES = [
    ('Behavioural Therapy', 'Behavioral therapy tools and aids'),
    ('Occupational Therapy', 'Occupational therapy tools and equipment'),
    ('Speech Therapy', 'Speech therapy tools and materials'),
]


def create_therapy_categories(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    for name, description in THERAPY_CATEGORIES:
        # icon left blank -- the Category.icon column is utf8 (not utf8mb4),
        # so emoji break it (see 0008_pharmacy_category's fix history).
        Category.objects.get_or_create(name=name, defaults={'icon': '', 'description': description})


def remove_therapy_categories(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    Category.objects.filter(name__in=[name for name, _ in THERAPY_CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace_app', '0009_productvariant_orderitem_variant'),
    ]

    operations = [
        migrations.RunPython(create_therapy_categories, remove_therapy_categories),
    ]
