import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404
from django.contrib.auth.decorators import login_required
from personal_account.models import AddPatient
from .models import RegionalAssessment, SpecialTestReference, PatientScaleAssessment
from .forms import RegionalAssessmentForm
from .scales import SCALE_CHOICES, SCALE_DEFINITIONS


@login_required
def create_assessment(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)

    if request.method == 'POST':
        form = RegionalAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.patient = patient
            assessment.created_by = request.user
            assessment.save()
            messages.success(request, f'Assessment saved for {patient.patient_name}.')
            return redirect('assessment-list', patient_id=patient.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegionalAssessmentForm()

    return render(request, 'assessment/create-assessment.html', {
        'form': form,
        'patient': patient,
        'reference_tests_json': _reference_tests_json(),
    })


@login_required
def edit_assessment(request, assessment_id):
    assessment = get_object_or_404(RegionalAssessment, id=assessment_id)

    if request.method == 'POST':
        form = RegionalAssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Assessment updated for {assessment.patient.patient_name}.')
            return redirect('assessment-detail', assessment_id=assessment.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegionalAssessmentForm(instance=assessment)

    return render(request, 'assessment/create-assessment.html', {
        'form': form,
        'patient': assessment.patient,
        'editing': True,
        'assessment': assessment,
        'reference_tests_json': _reference_tests_json(),
    })


@login_required
def assessment_list(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    assessments = patient.regional_assessments.all()
    scale_assessments = patient.scale_assessments.all()
    return render(request, 'assessment/assessment-list.html', {
        'patient': patient,
        'assessments': assessments,
        'scale_assessments': scale_assessments,
        'scale_choices': SCALE_CHOICES,
    })


@login_required
def assessment_detail(request, assessment_id):
    assessment = get_object_or_404(RegionalAssessment, id=assessment_id)
    return render(request, 'assessment/assessment-detail.html', {'assessment': assessment})


@login_required
def create_scale_assessment(request, patient_id, scale):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if scale not in SCALE_DEFINITIONS:
        raise Http404('Unknown scale')
    definition = SCALE_DEFINITIONS[scale]

    if request.method == 'POST':
        items = _parse_scale_items(request.POST, definition)
        assessment = PatientScaleAssessment(
            patient=patient, created_by=request.user, scale=scale,
            items=items, notes=request.POST.get('notes', '').strip(),
        )
        assessment.compute_score()
        assessment.save()
        messages.success(request, f'{definition["label"]} saved for {patient.patient_name}.')
        return redirect('assessment-list', patient_id=patient.id)

    return render(request, 'assessment/create-scale-assessment.html', {
        'patient': patient,
        'scale': scale,
        'definition': definition,
        'score_options': range(definition.get('item_max', 0) + 1) if definition['type'] == 'scored_items' else [],
    })


@login_required
def scale_assessment_detail(request, assessment_id):
    assessment = get_object_or_404(PatientScaleAssessment, id=assessment_id)
    definition = SCALE_DEFINITIONS[assessment.scale]
    item_rows = []
    if definition['type'] == 'scored_items':
        scores = assessment.items.get('scores', {})
        item_rows = [(label, scores.get(key, '')) for key, label in definition['items']]
    return render(request, 'assessment/scale-assessment-detail.html', {
        'assessment': assessment,
        'definition': definition,
        'item_rows': item_rows,
    })


def _parse_scale_items(post_data, definition):
    """Pulls the raw per-item values out of POST into the shape
    PatientScaleAssessment.compute_score() expects for this scale type."""
    if definition['type'] in ('single_choice', 'single_number'):
        return {'value': post_data.get('value', '').strip()}
    if definition['type'] == 'scored_items':
        scores = {}
        for key, _label in definition['items']:
            raw = post_data.get(f'item_{key}', '').strip()
            if raw != '':
                scores[key] = raw
        return {'scores': scores}
    return {}


def _reference_tests_json():
    """Grouped by region, as a JSON string embedded in the create/edit
    assessment page so its extra_js can swap the cheat-sheet in as the
    physio changes the region dropdown (region -> [{name, purpose}])."""
    tests = SpecialTestReference.objects.filter(is_active=True).order_by('region', 'order', 'name')
    grouped = {}
    for t in tests:
        grouped.setdefault(t.region, []).append({'name': t.name, 'purpose': t.purpose})
    return json.dumps(grouped)
