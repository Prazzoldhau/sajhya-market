from django.db import migrations

ZONE_NAMES = [
    'Sajhya Pickup',
    'Koteshwor',
    'Baneshwor',
    'Tinkune',
    'Putalisadak',
    'Maitidevi',
    'Dillibazar',
]


def seed_zones(apps, schema_editor):
    Zone = apps.get_model('delivery_app', 'Zone')
    for name in ZONE_NAMES:
        Zone.objects.get_or_create(name=name)


def unseed_zones(apps, schema_editor):
    Zone = apps.get_model('delivery_app', 'Zone')
    Zone.objects.filter(name__in=ZONE_NAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_zones, unseed_zones),
    ]
