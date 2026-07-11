from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import ExerciseMain, SubRegion, ExerciseStepImage

class ExerciseResource(resources.ModelResource):
    # Tell the importer to use the 'id' column in the CSV to find the SubRegion
    sub_region_fk = fields.Field(
        column_name='sub_region_fk',
        attribute='sub_region_fk',
        widget=ForeignKeyWidget(SubRegion, 'id')
    )

    class Meta:
        model = ExerciseMain
        # Optional: Define which CSV columns to import
        # fields = ('sub_region_fk', 'exercise_name', ...)
        # Optional: Prevent duplicate entries
        # import_id_fields = ('exercise_name',)


class ExerciseStepImageResource(resources.ModelResource):
    # CSV column 'exercise' holds the ExerciseMain id this step belongs to
    exercise = fields.Field(
        column_name='exercise',
        attribute='exercise',
        widget=ForeignKeyWidget(ExerciseMain, 'id')
    )

    class Meta:
        model = ExerciseStepImage
        # Re-importing the same exercise+order pair updates that row
        # (e.g. to fix a URL or label) instead of erroring on the
        # unique_together constraint.
        import_id_fields = ('exercise', 'order')