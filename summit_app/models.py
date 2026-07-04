from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from .content import SESSION_ORDER, SESSIONS

SESSION_CHOICES = [(key, SESSIONS[key]["short_title"]) for key in SESSION_ORDER]


class Table(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    label = models.CharField(max_length=50, blank=True)
    pin_hash = models.CharField(max_length=128)
    pin = models.CharField(
        max_length=10,
        blank=True,
        help_text="Plaintext copy shown to staff on the admin dashboard. Login still checks pin_hash.",
    )
    is_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return self.label or f"Table {self.number}"

    def set_pin(self, raw_pin):
        self.pin = raw_pin
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin):
        return check_password(raw_pin, self.pin_hash)

    def claim(self):
        self.is_claimed = True
        self.claimed_at = timezone.now()
        self.save(update_fields=["is_claimed", "claimed_at"])

    def release(self):
        self.is_claimed = False
        self.claimed_at = None
        self.save(update_fields=["is_claimed", "claimed_at"])


class SessionSubmission(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name="submissions")
    session_key = models.CharField(max_length=20, choices=SESSION_CHOICES)
    facilitator_name = models.CharField(max_length=100, blank=True)
    data = models.JSONField(default=dict, blank=True)
    current_step = models.PositiveSmallIntegerField(default=1)
    is_complete = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["table__number", "session_key"]
        unique_together = ["table", "session_key"]

    def __str__(self):
        return f"{self.table} — {self.get_session_key_display()}"

    @property
    def total_steps(self):
        return len(SESSIONS[self.session_key]["steps"])
