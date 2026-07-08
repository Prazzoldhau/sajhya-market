import json

from django.conf import settings
from pywebpush import webpush, WebPushException

from .models import PushSubscription


def send_push_to_patient(patient, title, body):
    """Sends a Web Push notification to every device a patient has
    subscribed from. Returns how many sends actually succeeded, so a
    caller (e.g. "Call for Session") can tell staff the patient has no
    active notification device rather than silently doing nothing.

    Expired/unsubscribed devices (410/404 from the push service) are
    removed so they don't keep getting retried.
    """
    sent_count = 0
    for subscription in patient.push_subscriptions.all():
        subscription_info = {
            'endpoint': subscription.endpoint,
            'keys': {
                'p256dh': subscription.p256dh,
                'auth': subscription.auth,
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps({'title': title, 'body': body}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': settings.VAPID_CLAIM_EMAIL},
            )
            sent_count += 1
        except WebPushException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code in (404, 410):
                subscription.delete()
            # Other failures (network blip, bad payload) are logged by
            # pywebpush's own exception message; skip this device and
            # keep trying the patient's other subscriptions.

    return sent_count
