from django import forms
from .models import VisitNote


def _text(placeholder, rows=None):
    widget_cls = forms.Textarea if rows else forms.TextInput
    attrs = {'class': 'form-control', 'placeholder': placeholder}
    if rows:
        attrs['rows'] = rows
    return widget_cls(attrs=attrs)


class VisitNoteForm(forms.ModelForm):
    class Meta:
        model = VisitNote
        fields = [
            'case_type',
            # Subjective (shared)
            'chief_complaint_today', 'pain_score', 'pain_at_rest', 'pain_with_activity', 'pain_worst_24hr',
            'pain_quality_location', 'hep_adherence', 'hep_adherence_reason',
            'changes_since_last_visit', 'changes_description', 'current_function_adls',
            'medication_changes', 'new_concerns_alerts',
            # Objective baseline -- orthopedic
            'vitals_hr', 'vitals_bp', 'vitals_rr', 'rom_active', 'rom_passive',
            'strength_mmt', 'palpation_swelling', 'special_tests',
            'functional_test_baseline', 'outcome_measure',
            # Objective baseline -- neurological
            'neuro_fatigue_level', 'neuro_spasm_frequency', 'neuro_bladder_bowel_status',
            'neuro_tone_pre', 'neuro_motor_control', 'neuro_sensation',
            'neuro_balance_sitting', 'neuro_balance_standing', 'neuro_gait_pre', 'neuro_skin_check_pre',
            # Objective baseline -- geriatric
            'geri_appetite', 'geri_new_medications', 'geri_bp_seated', 'geri_bp_standing_pre',
            'geri_orthostatic_dizziness_pre', 'geri_spo2_pre', 'geri_dyspnea_borg_pre',
            'geri_cognition', 'geri_tug_pre', 'geri_skin_check_pre',
            # Treatment provided (shared)
            'treatment_provided',
            # Clinical decision (shared)
            'primary_impairment_today', 'contraindications_precautions', 'patient_goals_session',
            # Post-treatment -- orthopedic
            'post_pain_score', 'post_rom', 'post_strength', 'post_functional_test',
            # Post-treatment -- neurological
            'neuro_tone_post', 'neuro_gait_post', 'neuro_fatigue_post', 'neuro_skin_check_post',
            # Post-treatment -- geriatric
            'geri_recovery_vitals', 'geri_bp_standing_post', 'geri_orthostatic_dizziness_post',
            'geri_spo2_post', 'geri_dyspnea_borg_post', 'geri_tug_post', 'geri_patient_report_post',
            # Assessment & Plan (shared)
            'assessment', 'plan',
        ]
        widgets = {
            'case_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_case_type'}),
            'chief_complaint_today': _text('e.g. Still stiff in the morning', rows=2),
            'pain_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10, 'placeholder': '0-10'}),
            'pain_quality_location': _text('e.g. Dull ache in lateral knee', rows=2),
            'hep_adherence_reason': _text('Reason if not adhered'),
            'changes_description': _text('e.g. Sleep improved, unable to walk dog', rows=2),
            'current_function_adls': _text('e.g. Can now shower standing up', rows=2),
            'medication_changes': _text('Any new pain meds, anti-inflammatories, dosage changes', rows=2),
            'new_concerns_alerts': _text('e.g. Dizziness, new joint swelling, fever', rows=2),

            'vitals_hr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HR'}),
            'vitals_bp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BP'}),
            'vitals_rr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RR'}),
            'rom_active': _text('Active ROM, e.g. Flexion 100 / Extension 10', rows=2),
            'rom_passive': _text('Passive ROM', rows=2),
            'strength_mmt': _text('e.g. Knee Extension: L 4/5, R 4+/5', rows=2),
            'palpation_swelling': _text('Warmth, effusion grade, tenderness', rows=2),
            'special_tests': _text("e.g. Lachman's: Negative, SLR: 70deg", rows=2),
            'functional_test_baseline': _text('e.g. Timed Up-and-Go: 12s, Sit-to-Stand: 8 reps', rows=2),
            'outcome_measure': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. LEFS: 55/80'}),

            'neuro_fatigue_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10, 'placeholder': '0-10'}),
            'neuro_spasm_frequency': _text('e.g. Spasms in R hamstring more frequent over the weekend', rows=2),
            'neuro_bladder_bowel_status': _text('e.g. Bowel program completed yesterday. No signs of autonomic dysreflexia.', rows=2),
            'neuro_tone_pre': _text('e.g. MAS: R elbow flexors 1+, R plantarflexors 2. Clonus: sustained (3 beats)', rows=2),
            'neuro_motor_control': _text('e.g. Unable to isolate L ankle dorsiflexion without hip flexion (flexor synergy)', rows=2),
            'neuro_sensation': _text('e.g. Light touch impaired on L foot', rows=2),
            'neuro_balance_sitting': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dynamic, can reach forward'}),
            'neuro_balance_standing': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mod assist (A) with platform'}),
            'neuro_gait_pre': _text('e.g. 10-Meter Walk Test: 18s. Circumduction on L.', rows=2),
            'neuro_skin_check_pre': _text('e.g. Sacrum and L heel intact', rows=2),

            'geri_appetite': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Poor this morning'}),
            'geri_new_medications': _text('e.g. Started Lisinopril 2 days ago', rows=2),
            'geri_bp_seated': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 148/90'}),
            'geri_bp_standing_pre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 122/78'}),
            'geri_spo2_pre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 96%'}),
            'geri_dyspnea_borg_pre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1/10'}),
            'geri_cognition': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Alert & oriented x3'}),
            'geri_tug_pre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 22s'}),
            'geri_skin_check_pre': _text('e.g. Sacrum and heels intact', rows=2),

            'treatment_provided': _text('e.g. 15 min weight-bearing through L UE/LE, 10 min gait training with AFO and cane', rows=3),

            'primary_impairment_today': _text('e.g. Quadriceps inhibition and limited knee flexion', rows=2),
            'contraindications_precautions': _text('e.g. Avoid prone position due to low back flare-up', rows=2),
            'patient_goals_session': _text('e.g. Achieve 5 degrees more knee flexion passively', rows=2),

            'post_pain_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10, 'placeholder': '0-10'}),
            'post_rom': _text('ROM after treatment', rows=2),
            'post_strength': _text('Strength after treatment', rows=2),
            'post_functional_test': _text('Functional test after treatment', rows=2),

            'neuro_tone_post': _text('e.g. MAS: R elbow flexors 1 (decreased), clonus unsustained', rows=2),
            'neuro_gait_post': _text('e.g. 10-Meter Walk Test re-test: 16s (improved 2s)', rows=2),
            'neuro_fatigue_post': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10, 'placeholder': '0-10'}),
            'neuro_skin_check_post': _text('e.g. No new friction redness', rows=2),

            'geri_recovery_vitals': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HR 90, BP 142/86'}),
            'geri_bp_standing_post': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 138/82'}),
            'geri_spo2_post': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 95%'}),
            'geri_dyspnea_borg_post': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2/10'}),
            'geri_tug_post': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 20s'}),
            'geri_patient_report_post': _text('e.g. Denies chest pain or unusual shortness of breath', rows=2),

            'assessment': _text('Compare post-treatment findings to the pre-treatment baseline above', rows=3),
            'plan': _text('Plan for next visit', rows=3),
        }
