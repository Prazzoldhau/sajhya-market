from marketplace_app.models import PatientProductRecommendation, DiagnosisProductMap
from personal_account.models import AddPatient
from marketplace_app.views import get_recommended_for_diagnosis

patients = AddPatient.objects.all()[:5]
for p in patients:
    recs, label = get_recommended_for_diagnosis(p.patient_diagnosis)
    print(f'Patient: {p.patient_name!r} | diagnosis: {p.patient_diagnosis!r} | auto_recs: {recs.count()} | label: {label!r}')

print()
print('DiagnosisProductMap count:', DiagnosisProductMap.objects.count())
print('Manual recs in DB:', PatientProductRecommendation.objects.count())
