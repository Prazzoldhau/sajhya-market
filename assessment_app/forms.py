from django import forms
from .models import RegionalAssessment


def _text(placeholder, rows=2):
    return forms.Textarea(attrs={'class': 'form-control', 'placeholder': placeholder, 'rows': rows})


class RegionalAssessmentForm(forms.ModelForm):
    class Meta:
        model = RegionalAssessment
        fields = [
            'region', 'chief_complaint', 'observation', 'range_of_motion',
            'palpation', 'special_tests', 'neurovascular_screen',
            'clinical_impression', 'plan',
        ]
        widgets = {
            'region': forms.Select(attrs={'class': 'form-control', 'id': 'id_region'}),
            'chief_complaint': _text('e.g. Low back pain for 2 weeks, worse with sitting'),
            'observation': _text('e.g. Flattened lumbar lordosis, antalgic gait, no visible swelling'),
            'range_of_motion': _text('e.g. Flexion 40deg (limited, painful), Extension 10deg'),
            'palpation': _text('e.g. Tenderness over L4-L5 paraspinals, no step-off'),
            'special_tests': _text("e.g. SLR: positive at 40deg on R, reproduces radicular pain. Slump test: negative."),
            'neurovascular_screen': _text('e.g. Sensation intact L4-S1 bilaterally, DTRs 2+ symmetric, no red flags'),
            'clinical_impression': _text('e.g. Mechanical low back pain with right-sided radicular irritation'),
            'plan': _text('e.g. Begin McKenzie extension protocol, reassess SLR in 1 week'),
        }
