import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from core.formatting import format_display_time


logger = logging.getLogger(__name__)


def build_admin_service_log_url(service_log, request=None):
    path = reverse("service_log_detail", args=[service_log.id])
    admin_base_url = getattr(settings, "BSC_ADMIN_BASE_URL", "").rstrip("/")
    if admin_base_url:
        return f"{admin_base_url}{path}"
    if request is not None:
        return request.build_absolute_uri(path)
    return path


def notify_admin_service_log_submitted(service_log, request=None):
    recipients = getattr(settings, "ADMIN_NOTIFICATION_EMAILS", [])
    if not recipients:
        return False

    review_url = build_admin_service_log_url(service_log, request=request)
    subject = f"New service log submitted - {service_log.participant}"
    body = "\n".join(
        [
            "A support worker has submitted a service log.",
            "",
            f"Participant: {service_log.participant}",
            f"Worker: {service_log.worker}",
            f"Service date: {service_log.service_date:%d/%m/%Y}",
            (
                "Actual time: "
                f"{format_display_time(service_log.actual_start_time)} - "
                f"{format_display_time(service_log.actual_end_time)}"
            ),
            f"Actual hours: {service_log.actual_hours:.2f}",
            f"Kilometres: {service_log.kilometres:.2f}",
            "",
            f"Review in admin: {review_url}",
        ]
    )

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning("Failed to send service log notification email: %s", exc)
        return False

    return True
