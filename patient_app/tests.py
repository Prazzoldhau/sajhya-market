import json

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from personal_account.models import AddPatient, PatientPhysioPairing
from .models import PushSubscription


class DeleteAccountTests(TestCase):
    """Covers the Play-mandated account deletion path.

    The AddPatient row survives deletion (anonymised) so linked clinical and
    financial records stay intact, which means the lockout has to be enforced
    explicitly on every entry point. Those guards are the part worth testing:
    without them a "deleted" patient can sign straight back in.
    """

    def setUp(self):
        self.password = 'test-pass-123'
        self.patient = AddPatient.objects.create(
            patient_name='Test Patient',
            patient_contact='9800000000',
            patient_diagnosis='Low back pain',
            password=make_password(self.password),
        )
        self.patient.refresh_from_db()  # pick up generated patient_code

    def _login(self):
        return self.client.post(
            reverse('patient_api_login'),
            data=json.dumps({
                'username': self.patient.patient_code,
                'password': self.password,
            }),
            content_type='application/json',
        )

    def _delete(self):
        return self.client.post(reverse('patient_api_delete_account'))

    def test_login_works_before_deletion(self):
        self.assertEqual(self._login().status_code, 200)

    def test_delete_requires_authentication(self):
        self.assertEqual(self._delete().status_code, 401)

    def test_delete_anonymises_instead_of_dropping_the_row(self):
        self._login()
        self.assertEqual(self._delete().status_code, 200)

        # Row must survive: prescriptions, visit notes and orders point at it.
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_deleted)
        self.assertIsNotNone(self.patient.deleted_at)

        # ...but nothing identifying may remain on it.
        self.assertEqual(self.patient.patient_name, 'Deleted patient')
        self.assertEqual(self.patient.patient_contact, '')
        self.assertIsNone(self.patient.password)
        self.assertIsNone(self.patient.qr_token)

    def test_delete_removes_linked_personal_data(self):
        PushSubscription.objects.create(
            patient=self.patient,
            endpoint='https://push.example/abc',
            p256dh='k',
            auth='a',
        )
        physio = get_user_model().objects.create_user(
            username='physio1', password='x'
        )
        PatientPhysioPairing.objects.create(
            patient=self.patient, physio=physio, source='physio_created'
        )

        self._login()
        self.assertEqual(self._delete().status_code, 200)

        self.assertFalse(PushSubscription.objects.filter(patient=self.patient).exists())
        self.assertFalse(PatientPhysioPairing.objects.filter(patient=self.patient).exists())

    def test_cannot_log_in_after_deletion(self):
        self._login()
        self._delete()

        response = self._login()
        self.assertEqual(response.status_code, 401)
        # Must not reveal that the code was ever valid.
        self.assertEqual(response.json().get('error'), 'Invalid credentials')

    def test_session_on_another_device_is_rejected_after_deletion(self):
        other = self.client_class()
        other.post(
            reverse('patient_api_login'),
            data=json.dumps({
                'username': self.patient.patient_code,
                'password': self.password,
            }),
            content_type='application/json',
        )
        self.assertEqual(other.get(reverse('patient_api_me')).status_code, 200)

        self._login()
        self._delete()

        # The second device still holds a valid session cookie; the is_deleted
        # guard is what stops it reading the record.
        self.assertEqual(other.get(reverse('patient_api_me')).status_code, 401)
        self.assertEqual(other.get(reverse('patient_api_orders')).status_code, 401)

    def test_web_deletion_page_requires_correct_credentials(self):
        url = reverse('patient-delete-account-web')
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(url, {
            'patient_code': self.patient.patient_code,
            'password': 'wrong-password',
            'confirm': 'DELETE',
        })
        self.assertEqual(response.status_code, 200)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_deleted)

    def test_web_deletion_requires_the_confirm_word(self):
        response = self.client.post(reverse('patient-delete-account-web'), {
            'patient_code': self.patient.patient_code,
            'password': self.password,
            'confirm': '',
        })
        self.assertEqual(response.status_code, 200)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_deleted)

    def test_web_deletion_succeeds(self):
        response = self.client.post(reverse('patient-delete-account-web'), {
            'patient_code': self.patient.patient_code,
            'password': self.password,
            'confirm': 'DELETE',
        })
        self.assertEqual(response.status_code, 200)
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_deleted)
