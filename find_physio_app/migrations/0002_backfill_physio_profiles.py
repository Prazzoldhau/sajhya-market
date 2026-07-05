from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model('account_app', 'User')
    PhysioProfile = apps.get_model('find_physio_app', 'PhysioProfile')
    existing_ids = set(PhysioProfile.objects.values_list('physio_id', flat=True))
    new_profiles = [
        PhysioProfile(physio_id=user_id)
        for user_id in User.objects.exclude(id__in=existing_ids).exclude(is_superuser=True).values_list('id', flat=True)
    ]
    PhysioProfile.objects.bulk_create(new_profiles)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('find_physio_app', '0001_initial'),
        ('account_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, noop_reverse),
    ]
