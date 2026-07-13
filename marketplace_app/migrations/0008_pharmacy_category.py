from django.db import migrations


def create_pharmacy_category(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    Category.objects.get_or_create(
        name='Pharmacy',
        defaults={'icon': '', 'description': 'Medicines and pharmacy products'},
    )


def remove_pharmacy_category(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    Category.objects.filter(name='Pharmacy').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace_app', '0007_alter_diagnosisproductmap_options'),
    ]

    operations = [
        migrations.RunPython(create_pharmacy_category, remove_pharmacy_category),
    ]
