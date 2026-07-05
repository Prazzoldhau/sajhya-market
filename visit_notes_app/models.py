from django.db import models
from django.conf import settings
from personal_account.models import AddPatient


class VisitNote(models.Model):
    CASE_TYPE_CHOICES = [
        ('ortho', 'Orthopedic'),
        ('neuro', 'Neurological'),
        ('geriatric', 'Geriatric'),
    ]
    HEP_ADHERENCE_CHOICES = [
        ('100', '100%'),
        ('75', '75%'),
        ('50', '50%'),
        ('0', '0%'),
    ]
    CHANGE_CHOICES = [
        ('better', 'Better'),
        ('worse', 'Worse'),
        ('same', 'Same'),
    ]

    patient = models.ForeignKey(AddPatient, on_delete=models.CASCADE, related_name='visit_notes')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='visit_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    case_type = models.CharField(max_length=10, choices=CASE_TYPE_CHOICES, default='ortho')

    # --- Subjective (pre-treatment) -- shared across case types ---
    chief_complaint_today = models.TextField(blank=True)
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0-10')
    pain_at_rest = models.BooleanField(default=False)
    pain_with_activity = models.BooleanField(default=False)
    pain_worst_24hr = models.BooleanField(default=False)
    pain_quality_location = models.TextField(blank=True)
    hep_adherence = models.CharField(max_length=3, choices=HEP_ADHERENCE_CHOICES, blank=True)
    hep_adherence_reason = models.CharField(max_length=255, blank=True)
    changes_since_last_visit = models.CharField(max_length=10, choices=CHANGE_CHOICES, blank=True)
    changes_description = models.TextField(blank=True)
    current_function_adls = models.TextField(blank=True)
    medication_changes = models.TextField(blank=True)
    new_concerns_alerts = models.TextField(blank=True)

    # --- Objective baseline (pre-treatment) -- orthopedic ---
    vitals_hr = models.CharField(max_length=20, blank=True)
    vitals_bp = models.CharField(max_length=20, blank=True)
    vitals_rr = models.CharField(max_length=20, blank=True)
    rom_active = models.TextField(blank=True)
    rom_passive = models.TextField(blank=True)
    strength_mmt = models.TextField(blank=True)
    palpation_swelling = models.TextField(blank=True)
    special_tests = models.TextField(blank=True)
    functional_test_baseline = models.TextField(blank=True)
    outcome_measure = models.CharField(max_length=255, blank=True)

    # --- Objective (pre-treatment) -- neurological ---
    neuro_fatigue_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0-10')
    neuro_spasm_frequency = models.TextField(blank=True)
    neuro_bladder_bowel_status = models.TextField(blank=True, help_text='Esp. for SCI: bowel program, autonomic dysreflexia')
    neuro_tone_pre = models.TextField(blank=True, help_text='e.g. MAS scores by body part, clonus')
    neuro_motor_control = models.TextField(blank=True, help_text='e.g. synergy patterns, isolated movement')
    neuro_sensation = models.TextField(blank=True)
    neuro_balance_sitting = models.CharField(max_length=100, blank=True)
    neuro_balance_standing = models.CharField(max_length=100, blank=True)
    neuro_gait_pre = models.TextField(blank=True, help_text='e.g. 10-Meter Walk Test, deviations')
    neuro_skin_check_pre = models.TextField(blank=True)

    # --- Objective (pre-treatment) -- geriatric ---
    geri_appetite = models.CharField(max_length=100, blank=True)
    geri_new_medications = models.TextField(blank=True)
    geri_bp_seated = models.CharField(max_length=30, blank=True)
    geri_bp_standing_pre = models.CharField(max_length=30, blank=True, help_text='Orthostatic check -- red flag if drop >20 systolic')
    geri_orthostatic_dizziness_pre = models.BooleanField(default=False)
    geri_spo2_pre = models.CharField(max_length=10, blank=True)
    geri_dyspnea_borg_pre = models.CharField(max_length=10, blank=True)
    geri_cognition = models.CharField(max_length=100, blank=True, help_text='e.g. Alert & oriented x3')
    geri_tug_pre = models.CharField(max_length=20, blank=True, help_text='Timed Up and Go, seconds')
    geri_skin_check_pre = models.TextField(blank=True)

    # --- Treatment provided -- shared across case types ---
    treatment_provided = models.TextField(blank=True)

    # --- Clinical decision (based on pre-treatment data) -- shared ---
    primary_impairment_today = models.TextField(blank=True)
    contraindications_precautions = models.TextField(blank=True)
    patient_goals_session = models.TextField(blank=True)

    # --- Post-treatment re-assessment -- orthopedic ---
    post_pain_score = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0-10')
    post_rom = models.TextField(blank=True)
    post_strength = models.TextField(blank=True)
    post_functional_test = models.TextField(blank=True)

    # --- Post-treatment re-assessment -- neurological ---
    neuro_tone_post = models.TextField(blank=True)
    neuro_gait_post = models.TextField(blank=True)
    neuro_fatigue_post = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0-10')
    neuro_skin_check_post = models.TextField(blank=True)

    # --- Post-treatment re-assessment -- geriatric ---
    geri_recovery_vitals = models.CharField(max_length=100, blank=True)
    geri_bp_standing_post = models.CharField(max_length=30, blank=True)
    geri_orthostatic_dizziness_post = models.BooleanField(default=False)
    geri_spo2_post = models.CharField(max_length=10, blank=True)
    geri_dyspnea_borg_post = models.CharField(max_length=10, blank=True)
    geri_tug_post = models.CharField(max_length=20, blank=True)
    geri_patient_report_post = models.TextField(blank=True)

    # --- Assessment & Plan -- shared ---
    assessment = models.TextField(blank=True, help_text='Compare post-treatment findings to the pre-treatment baseline above.')
    plan = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient.patient_name} - {self.created_at:%Y-%m-%d} ({self.get_case_type_display()})"
