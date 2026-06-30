from django.db import models


class APKRelease(models.Model):
    version = models.CharField(max_length=20)
    file = models.FileField(upload_to='apks/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=False)
    release_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"v{self.version} ({'latest' if self.is_latest else 'old'})"

    def save(self, *args, **kwargs):
        if self.is_latest:
            APKRelease.objects.exclude(pk=self.pk).update(is_latest=False)
        super().save(*args, **kwargs)
