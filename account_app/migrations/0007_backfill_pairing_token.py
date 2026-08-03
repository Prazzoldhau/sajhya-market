import secrets

from django.db import migrations


def backfill_tokens(apps, schema_editor):
    User = apps.get_model('account_app', 'User')
    existing = set(User.objects.exclude(pairing_token__isnull=True).values_list('pairing_token', flat=True))
    for user in User.objects.filter(pairing_token__isnull=True):
        token = secrets.token_urlsafe(24)
        while token in existing:
            token = secrets.token_urlsafe(24)
        existing.add(token)
        user.pairing_token = token
        user.save(update_fields=['pairing_token'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('account_app', '0006_user_pairing_token'),
    ]

    operations = [
        migrations.RunPython(backfill_tokens, noop_reverse),
    ]
