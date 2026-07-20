import csv

from django.core.management.base import BaseCommand
from exercise_app.models import ExerciseMain


class Command(BaseCommand):
    help = (
        'Bulk-update ExerciseMain.exercise_description and '
        'exercise_description_nepali together from a CSV '
        '(columns: exercise_id, description, description_nepali), matched '
        'by primary key. Uses the ORM so long multi-line text with quotes/ '
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
                exercise_id = int(row['exercise_id'].strip())
                description = row['description']
                nepali = row['description_nepali']

                exercise = ExerciseMain.objects.filter(id=exercise_id).first()
                if not exercise:
                    not_found.append(exercise_id)
                    continue

                if dry_run:
                    self.stdout.write(f'[dry-run] would update: id={exercise_id} ({exercise.exercise_name})')
                else:
                    exercise.exercise_description = description
                    exercise.exercise_description_nepali = nepali
                    exercise.save(update_fields=['exercise_description', 'exercise_description_nepali'])
                    self.stdout.write(f'Updated: id={exercise_id} ({exercise.exercise_name})')
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'\n{updated} exercise(s) matched and updated.'))
        if not_found:
            self.stdout.write(self.style.WARNING(f'{len(not_found)} id(s) not found in the database:'))
            for exercise_id in not_found:
                self.stdout.write(f'  - {exercise_id}')
