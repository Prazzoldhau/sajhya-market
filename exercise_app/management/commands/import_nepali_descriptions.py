import csv

from django.core.management.base import BaseCommand
from exercise_app.models import ExerciseMain


class Command(BaseCommand):
    help = (
        'Bulk-update ExerciseMain.exercise_description_nepali from a CSV '
        '(columns: exercise_name, description_nepali), matched by exact '
        'exercise_name. Uses the ORM so long multi-line text with quotes/'
        'apostrophes is handled safely (no manual SQL escaping).'
    )

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be updated without saving anything.',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']

        updated = 0
        not_found = []

        with open(csv_path, encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['exercise_name'].strip()
                nepali = row['description_nepali']

                exercise = ExerciseMain.objects.filter(exercise_name=name).first()
                if not exercise:
                    not_found.append(name)
                    continue

                if dry_run:
                    self.stdout.write(f'[dry-run] would update: {name} (id={exercise.id})')
                else:
                    exercise.exercise_description_nepali = nepali
                    exercise.save(update_fields=['exercise_description_nepali'])
                    self.stdout.write(f'Updated: {name} (id={exercise.id})')
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'\n{updated} exercise(s) matched and updated.'))
        if not_found:
            self.stdout.write(self.style.WARNING(f'{len(not_found)} name(s) not found in the database:'))
            for name in not_found:
                self.stdout.write(f'  - {name}')
