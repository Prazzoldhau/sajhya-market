import random

from django.core.management.base import BaseCommand

from summit_app.content import TABLE_NUMBERS
from summit_app.models import Table


class Command(BaseCommand):
    help = "Create (or reset) the MAPS Summit tables with fresh PINs. PINs are only ever shown here."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Regenerate a new PIN for tables that already exist, not just missing ones.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        for number in TABLE_NUMBERS:
            table, created = Table.objects.get_or_create(number=number, defaults={"label": f"Table {number}"})
            if created or reset:
                pin = f"{random.randint(0, 999999):06d}"
                table.set_pin(pin)
                table.save()
                self.stdout.write(self.style.SUCCESS(f"Table {number}: PIN = {pin}"))
            else:
                self.stdout.write(f"Table {number}: already exists (use --reset to generate a new PIN)")
