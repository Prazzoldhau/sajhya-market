from django.db import models
from django.conf import settings
from personal_account.models import AddPatient
from .scales import SCALE_CHOICES, SCALE_DEFINITIONS, interpret


REGION_CHOICES = [
    ('low_back', 'Low Back Pain'),
    ('cervical', 'Cervical'),
    ('knee', 'Knee'),
    ('parkinsons', "Parkinson's Disease"),
]


class SpecialTestReference(models.Model):
    """A small reference library of standard orthopedic special tests, one
    per region -- shown as a cheat-sheet alongside RegionalAssessment's
    free-text `special_tests` field so a physio knows what's conventionally
    checked for that region, without this app trying to score or structure
    the actual finding (that stays free text, same as VisitNote.special_tests)."""

    region = models.CharField(max_length=20, choices=REGION_CHOICES)
    name = models.CharField(max_length=150, help_text='e.g. "Straight Leg Raise (SLR) Test"')
    purpose = models.CharField(max_length=255, help_text='What it screens for, e.g. "Lumbar nerve root irritation / disc herniation"')
    procedure = models.TextField(blank=True, help_text='Brief how-to')
    positive_sign = models.TextField(blank=True, help_text='What a positive result looks like')
    order = models.PositiveSmallIntegerField(default=0, help_text='Display order within the region')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['region', 'order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_region_display()})"


class RegionalAssessment(models.Model):
    """A standalone, region-scoped clinical assessment -- distinct from
    VisitNote, which is the full per-visit SOAP note. This is the lighter
    intake/re-assessment form a physio fills in for a specific region
    (Low Back / Cervical / Knee), with no scoring -- same free-text style
    as VisitNote's own objective fields."""

    patient = models.ForeignKey(AddPatient, on_delete=models.CASCADE, related_name='regional_assessments')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='regional_assessments_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    region = models.CharField(max_length=20, choices=REGION_CHOICES)
    chief_complaint = models.TextField(blank=True, help_text='Why this assessment -- presenting complaint')
    observation = models.TextField(blank=True, help_text='Posture, gait, swelling, deformity')
    range_of_motion = models.TextField(blank=True)
    palpation = models.TextField(blank=True)
    special_tests = models.TextField(blank=True, help_text='Which tests performed and findings -- see reference list for this region')
    neurovascular_screen = models.TextField(blank=True, help_text='Sensation, reflexes, pulses, red flags')
    clinical_impression = models.TextField(blank=True, help_text="Physio's summary / working diagnosis from this assessment")
    plan = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient.patient_name} - {self.get_region_display()} ({self.created_at:%Y-%m-%d})"


class PatientScaleAssessment(models.Model):
    """One administration of a standardized assessment scale (Hoehn &
    Yahr, TUG, Berg Balance Scale, LPAS, NFOG-Q -- see scales.py) for a
    patient, scored and stored so a physio can track change over time.
    Distinct from RegionalAssessment, which is a free-text SOAP-style
    note -- this is a real structured, scored instrument.

    `items` holds the raw per-item scores (shape varies by scale --
    scales.py's SCALE_DEFINITIONS says how to interpret it), since a
    14-item Berg Balance Scale, a single Hoehn & Yahr stage, and a
    single TUG time don't share one schema. total_score and
    interpretation are computed once at save time from `items` via
    compute_score(), not recomputed on every read."""

    patient = models.ForeignKey(AddPatient, on_delete=models.CASCADE, related_name='scale_assessments')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='scale_assessments_created')
    created_at = models.DateTimeField(auto_now_add=True)

    scale = models.CharField(max_length=20, choices=SCALE_CHOICES)
    items = models.JSONField(default=dict, help_text='Raw per-item scores/values -- shape depends on scale, see scales.py')
    total_score = models.CharField(max_length=20, blank=True, help_text='The headline number/stage for this administration')
    interpretation = models.CharField(max_length=255, blank=True, help_text='Auto-computed from total_score at save time')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def compute_score(self):
        """Fills total_score/interpretation from self.items, per the
        scale's definition. Called explicitly by the view before save()
        -- not in save() itself, so a view can inspect/validate items
        first without triggering this twice."""
        definition = SCALE_DEFINITIONS[self.scale]
        kind = definition['type']

        if kind == 'single_choice':
            value = self.items.get('value', '')
            self.total_score = value
            label = dict(definition['options']).get(value, '')
            self.interpretation = label.split('—', 1)[-1].strip() if '—' in label else label

        elif kind == 'single_number':
            value = self.items.get('value')
            self.total_score = str(value) if value is not None else ''
            try:
                self.interpretation = interpret(definition['interpretation_bands'], float(value))
            except (TypeError, ValueError):
                self.interpretation = ''

        elif kind == 'scored_items':
            scores = self.items.get('scores', {})
            total = sum(int(v) for v in scores.values() if str(v).strip() != '')
            item_max = definition['item_max']
            max_total = item_max * len(definition['items'])
            self.total_score = f"{total}/{max_total}"
            self.interpretation = interpret(definition.get('interpretation_bands', []), total)

    def get_scale_label(self):
        return SCALE_DEFINITIONS[self.scale]['label']

    def __str__(self):
        return f"{self.get_scale_label()} - {self.patient.patient_name} ({self.created_at:%Y-%m-%d})"
