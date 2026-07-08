from django.db import models
from personal_account.models import AddPatient


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
