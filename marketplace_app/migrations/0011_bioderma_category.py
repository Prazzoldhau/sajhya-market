from django.db import migrations


def create_bioderma_category(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    Category.objects.get_or_create(
        name='Bioderma',
        defaults={'icon': '', 'description': 'Dermo-cosmetics test category'},
    )


def remove_bioderma_category(apps, schema_editor):
    Category = apps.get_model('marketplace_app', 'Category')
    Category.objects.filter(name='Bioderma').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace_app', '0010_therapy_categories'),
    ]

    operations = [
        migrations.RunPython(create_bioderma_category, remove_bioderma_category),
    ]
