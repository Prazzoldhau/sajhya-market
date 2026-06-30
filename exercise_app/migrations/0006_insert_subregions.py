# exercise_app/migrations/0005_insert_subregions.py

from django.db import migrations

def insert_subregions(apps, schema_editor):
    SubRegion = apps.get_model('exercise_app', 'SubRegion')
    Region = apps.get_model('exercise_app', 'Region')

    # Your data: (region_fk_id, sub_region_name)
    data = [
        (1, 'brain'), (1, 'mid brain'), (1, 'spinal cord'), (1, 'tmj'), (1, 'cranial nerves'),
        (2, 'Cervical'), (2, 'Thoracic'), (2, 'Lumbar'), (2, 'Pelvis'), (2, 'Coccygeal'),
        (3, 'Shoulder'), (3, 'Elbow'), (3, 'Wrist'), (3, 'Hand'),
        (4, 'Hip'), (4, 'Knee'), (4, 'Leg'), (4, 'Ankle'), (4, 'Foot'),
        (2, 'cervicothoracic'), (2, 'thoracolumbar'), (2, 'lumbopelvic'),
        (5, 'sternum'), (5, 'xiphoid'), (5, 'ribs'),
        (2, 'wholespine'),
    ]

    # Use get_or_create to avoid duplicates if migration is re-run
    for region_id, sub_name in data:
        region = Region.objects.get(pk=region_id)
        SubRegion.objects.get_or_create(
            region_fk=region,           # ForeignKey field name (adjust if yours differs)
            sub_region_name=sub_name,   # Adjust field name if needed
        )

def reverse_subregions(apps, schema_editor):
    SubRegion = apps.get_model('exercise_app', 'SubRegion')
    # Delete only the ones we inserted (by matching names & region ids)
    region_names_map = {
        1: ['brain', 'mid brain', 'spinal cord', 'tmj', 'cranial nerves'],
        2: ['Cervical', 'Thoracic', 'Lumbar', 'Pelvis', 'Coccygeal', 'cervicothoracic', 'thoracolumbar', 'lumbopelvic', 'wholespine'],
        3: ['Shoulder', 'Elbow', 'Wrist', 'Hand'],
        4: ['Hip', 'Knee', 'Leg', 'Ankle', 'Foot'],
        5: ['sternum', 'xiphoid', 'ribs'],
    }
    for region_id, names in region_names_map.items():
        SubRegion.objects.filter(region_fk_id=region_id, sub_region_name__in=names).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('exercise_app', '0005_insert_regions'),  # the migration that inserted Regions
        # If you used a different migration name, adjust accordingly.
    ]

    operations = [
        migrations.RunPython(insert_subregions, reverse_subregions),
    ]