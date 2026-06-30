from django.contrib import admin
from .models import Region, SubRegion,ExerciseMain,Prescription,PrescriptionExercise
# from import_export import resources
# from import_export.admin import ImportExportModelAdmin
# Register your models here.
admin.site.register(Region)
admin.site.register(SubRegion)
admin.site.register(Prescription)
admin.site.register(PrescriptionExercise)

from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import ExerciseMain
from .resources import ExerciseResource

@admin.register(ExerciseMain)
class ExerciseMainAdmin(ImportExportModelAdmin):
    resource_class = ExerciseResource
    list_display = ('exercise_name', 'sub_region_fk', 'exercise_type', 'difficulty_level')
    list_filter = ('exercise_type', 'difficulty_level', 'sub_region_fk')
    search_fields = ('exercise_name', 'exercise_description')