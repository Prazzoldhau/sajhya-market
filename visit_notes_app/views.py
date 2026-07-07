from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from personal_account.models import AddPatient
from .models import VisitNote
from .forms import VisitNoteForm


@login_required
def create_visit_note(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)

    if request.method == 'POST':
        form = VisitNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.patient = patient
            note.created_by = request.user
            note.save()
            messages.success(request, f'Visit note saved for {patient.patient_name}.')
            return redirect('visit-notes-list', patient_id=patient.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VisitNoteForm()

    return render(request, 'visit_notes/create-visit-note.html', {'form': form, 'patient': patient})


@login_required
def edit_visit_note(request, note_id):
    note = get_object_or_404(VisitNote, id=note_id)

    if request.method == 'POST':
        form = VisitNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, f'Visit note updated for {note.patient.patient_name}.')
            return redirect('visit-note-detail', note_id=note.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VisitNoteForm(instance=note)

    return render(request, 'visit_notes/create-visit-note.html', {
        'form': form,
        'patient': note.patient,
        'editing': True,
        'note': note,
    })


@login_required
def visit_notes_list(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    notes = patient.visit_notes.all()
    return render(request, 'visit_notes/visit-notes-list.html', {'patient': patient, 'notes': notes})


@login_required
def visit_note_detail(request, note_id):
    note = get_object_or_404(VisitNote, id=note_id)
    return render(request, 'visit_notes/visit-note-detail.html', {'note': note})
