from django.core.management.base import BaseCommand
from personal_account.models import ActivationCard


class Command(BaseCommand):
    help = 'Generate a batch of unused ActivationCard codes for printing/selling.'

    def add_arguments(self, parser):
        parser.add_argument('quantity', type=int)
        parser.add_argument(
            '--days', type=int, default=30,
            help='Days of access granted once redeemed (default: 30)',
        )

    def handle(self, *args, **options):
        quantity = options['quantity']
        days = options['days']

        cards = [ActivationCard.objects.create(duration_days=days) for _ in range(quantity)]

        self.stdout.write(self.style.SUCCESS(
            f'Generated {len(cards)} activation card(s), {days}-day validity each:'
        ))
        for card in cards:
            self.stdout.write(f'  {card.code}')
