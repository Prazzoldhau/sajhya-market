"""Definitions for the standardized Parkinson's disease assessment scales
(see PatientScaleAssessment). Each entry describes how to render the
admin form and how to score a completed one -- kept separate from
models.py since this is data/config, not a schema.

Hoehn & Yahr, TUG, and Berg Balance Scale are well-established, widely
published instruments reproduced here in their standard form. LPAS and
NFOG-Q are reproduced as a faithful general representation of what they
measure (LPAS: functional gait and bed mobility in Parkinson's; NFOG-Q:
frequency/duration/impact of freezing-of-gait episodes) -- a physio
should check their item wording and scoring against the official
published instrument before relying on them for anything beyond general
tracking, the same caveat this app's seeded DiagnosisCode list carries."""

SCALE_CHOICES = [
    ('hoehn_yahr', 'Hoehn and Yahr Staging Scale'),
    ('tug', 'Timed Up and Go (TUG)'),
    ('berg_balance', 'Berg Balance Scale (BBS)'),
    ('lpas', "Lindop Parkinson's Physiotherapy Assessment Scale (LPAS)"),
    ('nfogq', 'New Freezing of Gait Questionnaire (NFOG-Q)'),
]

SCALE_DEFINITIONS = {
    'hoehn_yahr': {
        'label': 'Hoehn and Yahr Staging Scale',
        'type': 'single_choice',
        'instructions': "Select the stage that best matches the patient's overall clinical presentation today.",
        'options': [
            ('0', 'Stage 0 — No signs of disease'),
            ('1', 'Stage 1 — Unilateral involvement only'),
            ('1.5', 'Stage 1.5 — Unilateral and axial involvement'),
            ('2', 'Stage 2 — Bilateral involvement, no impairment of balance'),
            ('2.5', 'Stage 2.5 — Mild bilateral disease, recovers on pull test'),
            ('3', 'Stage 3 — Mild-moderate bilateral disease, some postural instability, physically independent'),
            ('4', 'Stage 4 — Severe disability, still able to walk or stand unassisted'),
            ('5', 'Stage 5 — Wheelchair bound or bedridden unless aided'),
        ],
    },
    'tug': {
        'label': 'Timed Up and Go (TUG)',
        'type': 'single_number',
        'instructions': 'Time the patient rising from a chair, walking 3 meters, turning, walking back, and sitting down.',
        'unit': 'seconds',
        'interpretation_bands': [
            (0, 10, 'Normal mobility, low fall risk'),
            (10, 20, 'Mostly independent, some fall risk'),
            (20, 30, 'Variable mobility, further assessment needed'),
            (30, None, 'High fall risk, likely dependent'),
        ],
    },
    'berg_balance': {
        'label': 'Berg Balance Scale (BBS)',
        'type': 'scored_items',
        'instructions': 'Score each task 0 (unable) to 4 (normal performance). Total is out of 56.',
        'item_max': 4,
        'items': [
            ('sit_to_stand', 'Sitting to standing'),
            ('standing_unsupported', 'Standing unsupported'),
            ('sitting_unsupported', 'Sitting unsupported (feet on floor)'),
            ('stand_to_sit', 'Standing to sitting'),
            ('transfers', 'Transfers'),
            ('standing_eyes_closed', 'Standing with eyes closed'),
            ('standing_feet_together', 'Standing with feet together'),
            ('reaching_forward', 'Reaching forward with outstretched arm'),
            ('retrieving_object', 'Retrieving object from floor'),
            ('turning_look_behind', 'Turning to look behind'),
            ('turning_360', 'Turning 360 degrees'),
            ('alternate_foot_stool', 'Placing alternate foot on stool'),
            ('standing_one_foot_front', 'Standing with one foot in front (tandem)'),
            ('standing_one_leg', 'Standing on one leg'),
        ],
        'interpretation_bands': [
            (41, 56, 'Low fall risk'),
            (21, 40, 'Medium fall risk'),
            (0, 20, 'High fall risk'),
        ],
    },
    'lpas': {
        'label': "Lindop Parkinson's Physiotherapy Assessment Scale (LPAS)",
        'type': 'scored_items',
        'instructions': 'Score each item 0 (severe limitation) to 3 (normal/independent).',
        'item_max': 3,
        'items': [
            ('gait_initiation', 'Gait initiation'),
            ('step_length', 'Step length / stride'),
            ('gait_freezing', 'Freezing during gait'),
            ('turning', 'Turning'),
            ('rolling_in_bed', 'Rolling in bed'),
            ('supine_to_sit', 'Supine to sit'),
            ('sit_to_stand', 'Sit to stand'),
        ],
        'note': 'General representation of what LPAS measures (functional gait and bed mobility) -- '
                'verify item wording and scoring against the official published scale before relying on it clinically.',
    },
    'nfogq': {
        'label': 'New Freezing of Gait Questionnaire (NFOG-Q)',
        'type': 'scored_items',
        'instructions': 'Score each item 0 (never/none) to 4 (always/very severe), based on the past month.',
        'item_max': 4,
        'items': [
            ('severity', 'Severity of freezing episodes'),
            ('frequency', 'Frequency of freezing episodes'),
            ('duration', 'Usual duration of freezing episodes'),
            ('turning_trigger', 'Freezing when turning'),
            ('initiation_trigger', 'Freezing when initiating gait'),
            ('narrow_spaces_trigger', 'Freezing in narrow or crowded spaces'),
            ('stress_trigger', 'Freezing under stress or time pressure'),
            ('daily_impact', 'Impact on daily activities'),
            ('fall_risk_impact', 'Freezing-related fall risk'),
        ],
        'note': 'General representation covering the frequency/duration/impact domains NFOG-Q measures -- '
                'verify item wording and scoring against the official published questionnaire before relying on it clinically.',
    },
}


def interpret(bands, value):
    if value is None:
        return ''
    for low, high, label in bands:
        if value >= low and (high is None or value <= high):
            return label
    return ''
