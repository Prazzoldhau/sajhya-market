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
from .models import ExerciseMain, ExerciseStepImage
from .resources import ExerciseResource, ExerciseStepImageResource


class ExerciseStepImageInline(admin.TabularInline):
    model = ExerciseStepImage
    extra = 1
    ordering = ('order',)


@admin.register(ExerciseMain)
class ExerciseMainAdmin(ImportExportModelAdmin):
    resource_class = ExerciseResource
    inlines = [ExerciseStepImageInline]
    list_display = ('exercise_name', 'sub_region_fk', 'exercise_type', 'difficulty_level')
    list_filter = ('exercise_type', 'difficulty_level', 'sub_region_fk')
    search_fields = ('exercise_name', 'exercise_description')


@admin.register(ExerciseStepImage)
class ExerciseStepImageAdmin(ImportExportModelAdmin):
    resource_class = ExerciseStepImageResource
    list_display = ('exercise', 'order', 'label', 'image_url')
    list_filter = ('exercise',)
    search_fields = ('exercise__exercise_name', 'label')