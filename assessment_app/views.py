import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from personal_account.models import AddPatient
from .models import RegionalAssessment, SpecialTestReference
from .forms import RegionalAssessmentForm


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
    return render(request, 'assessment/assessment-list.html', {'patient': patient, 'assessments': assessments})


@login_required
def assessment_detail(request, assessment_id):
    assessment = get_object_or_404(RegionalAssessment, id=assessment_id)
    return render(request, 'assessment/assessment-detail.html', {'assessment': assessment})


def _reference_tests_json():
    """Grouped by region, as a JSON string embedded in the create/edit
    assessment page so its extra_js can swap the cheat-sheet in as the
    physio changes the region dropdown (region -> [{name, purpose}])."""
    tests = SpecialTestReference.objects.filter(is_active=True).order_by('region', 'order', 'name')
    grouped = {}
    for t in tests:
        grouped.setdefault(t.region, []).append({'name': t.name, 'purpose': t.purpose})
    return json.dumps(grouped)
