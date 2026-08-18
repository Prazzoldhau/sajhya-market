from django.db import models
from personal_account.models import AddPatient, get_nepal_time


class AppOpenEvent(models.Model):
    """One row per patient per calendar day the app was opened -- upserted
    (get_or_create on patient+opened_on), not appended, so this stays a
    clean daily-active-patient signal instead of growing one row per
    request/session like django_session does. Pinged once from the
    dashboard on launch, after the patient is confirmed logged in."""
    patient = models.ForeignKey(AddPatient, on_delete=models.CASCADE, related_name='app_open_events')
    opened_on = models.DateField(help_text='Calendar date (Asia/Kathmandu) the app was opened')
    first_opened_at = models.DateTimeField(default=get_nepal_time)
    ping_count = models.PositiveIntegerField(default=1, help_text='How many times the ping fired that day -- informational only, not a distinct metric')

    class Meta:
        unique_together = ['patient', 'opened_on']
        ordering = ['-opened_on']

    def __str__(self):
        return f"{self.patient.patient_name} opened app on {self.opened_on}"


class VideoClickEvent(models.Model):
    """Logged each time a patient taps the YouTube video button for a
    prescribed exercise. Mirrors ExerciseFeedback's shape (FK to the
    PrescriptionExercise, not the library exercise, so it's tied to what
    the patient actually saw) plus a library-id snapshot so the record
    survives the exercise being edited or removed from the library."""
    prescription_exercise = models.ForeignKey(
        'exercise_app.PrescriptionExercise',
        on_delete=models.CASCADE,
        related_name='video_click_events',
    )
    exercise_id_in_library = models.IntegerField(db_index=True)
    exercise_name = models.CharField(max_length=200, blank=True, default='')
    clicked_at = models.DateTimeField(default=get_nepal_time)

    class Meta:
        ordering = ['-clicked_at']

    def __str__(self):
        return f"Video click — {self.exercise_name} @ {self.clicked_at}"


class PushSubscription(models.Model):
    """A browser's Web Push subscription for a patient -- one row per
    device, since a patient may have their dashboard open on more than
    one phone/browser."""
    patient = models.ForeignKey(AddPatient, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['patient', 'endpoint']

    def __str__(self):
        return f"Push subscription for {self.patient.patient_name}"
