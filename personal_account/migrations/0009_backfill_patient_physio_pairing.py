from django.db import migrations


def backfill_pairings(apps, schema_editor):
    AddPatient = apps.get_model('personal_account', 'AddPatient')
    PatientPhysioPairing = apps.get_model('personal_account', 'PatientPhysioPairing')
    rows = [
        PatientPhysioPairing(
            patient_id=p.id,
            physio_id=p.created_by_id,
            source='physio_created',
            paired_at=p.created_at,
        )
        for p in AddPatient.objects.exclude(created_by__isnull=True).only('id', 'created_by_id', 'created_at')
    ]
    PatientPhysioPairing.objects.bulk_create(rows)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('personal_account', '0008_alter_addpatient_created_by_patientphysiopairing'),
    ]

    operations = [
        migrations.RunPython(backfill_pairings, noop_reverse),
    ]
