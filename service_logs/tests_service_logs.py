from datetime import date, time
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from documents.models import Document
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class FailingEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise RuntimeError("SMTP unavailable")


class ServiceLogCompletionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media_dir.name)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.media_dir.cleanup()
        super().tearDownClass()

    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
            email=f"{username}@example.com",
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            is_active_worker=role == UserProfile.Role.SUPPORT_WORKER,
        )
        return user

    def setUp(self):
        self.admin_user = self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.worker_user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.other_worker_user = self.create_user_with_role(
            "otherworker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.worker = SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.other_worker = SupportWorker.objects.create(
            user=self.other_worker_user,
            first_name="Oscar",
            last_name="Other",
            email="other@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )

    def create_shift(self, **overrides):
        data = {
            "participant": self.participant,
            "worker": self.worker,
            "service_date": date(2026, 6, 1),
            "start_time": time(9, 0),
            "end_time": time(11, 30),
            "break_minutes": 30,
            "planned_hours": Decimal("2.00"),
            "support_item": self.support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "status": Shift.Status.PUBLISHED,
            "created_by": self.admin_user,
        }
        data.update(overrides)
        return Shift.objects.create(**data)

    def log_payload(self, **overrides):
        data = {
            "actual_start_time": "09:00",
            "actual_end_time": "11:30",
            "break_minutes": "30",
            "kilometres": "4.5",
            "case_notes": "Supported participant with personal care.",
            "worker_notes": "No issues.",
        }
        data.update(overrides)
        return data

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def test_worker_can_complete_own_published_shift(self):
        shift = self.create_shift()
        self.login_worker()

        response = self.client.post(
            reverse("worker_service_log_create", args=[shift.id]),
            self.log_payload(),
        )

        service_log = ServiceLog.objects.get()
        shift.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("worker_service_log_detail", args=[service_log.id]),
        )
        self.assertEqual(service_log.shift, shift)
        self.assertEqual(service_log.status, ServiceLog.Status.SUBMITTED)
        self.assertEqual(service_log.actual_hours, Decimal("2.00"))
        self.assertEqual(service_log.participant, self.participant)
        self.assertEqual(service_log.worker, self.worker)
        self.assertEqual(shift.status, Shift.Status.COMPLETED)
        self.assertIsNotNone(shift.completed_at)

    def test_worker_service_log_submission_creates_attachment_documents(self):
        shift = self.create_shift()
        self.login_worker()

        response = self.client.post(
            reverse("worker_service_log_create", args=[shift.id]),
            {
                **self.log_payload(),
                "attachments": [
                    SimpleUploadedFile("progress-photo.jpg", b"photo", content_type="image/jpeg"),
                    SimpleUploadedFile("receipt.pdf", b"receipt", content_type="application/pdf"),
                ],
            },
        )

        service_log = ServiceLog.objects.get()
        attachments = list(Document.objects.filter(service_log=service_log).order_by("title"))
        self.assertRedirects(
            response,
            reverse("worker_service_log_detail", args=[service_log.id]),
        )
        self.assertEqual(len(attachments), 2)
        self.assertEqual({document.category for document in attachments}, {Document.Category.SERVICE_LOG})
        self.assertEqual({document.worker for document in attachments}, {self.worker})
        self.assertEqual({document.participant for document in attachments}, {self.participant})
        self.assertEqual({document.uploaded_by for document in attachments}, {self.worker_user})
        self.assertEqual({document.review_status for document in attachments}, {Document.ReviewStatus.PENDING_REVIEW})

    def test_worker_service_log_submission_rejects_too_many_attachments(self):
        shift = self.create_shift()
        self.login_worker()

        response = self.client.post(
            reverse("worker_service_log_create", args=[shift.id]),
            {
                **self.log_payload(),
                "attachments": [
                    SimpleUploadedFile(f"attachment-{index}.pdf", b"file", content_type="application/pdf")
                    for index in range(4)
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attach no more than 3 files")
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertEqual(Document.objects.count(), 0)

    @override_settings(
        ADMIN_NOTIFICATION_EMAILS=["kun-bi@hotmail.com"],
        BSC_ADMIN_BASE_URL="https://admin.bscare.com.au",
        DEFAULT_FROM_EMAIL="notifications@bscare.com.au",
    )
    def test_worker_service_log_submission_emails_admin_notification(self):
        shift = self.create_shift()
        self.login_worker()

        response = self.client.post(
            reverse("worker_service_log_create", args=[shift.id]),
            self.log_payload(),
        )

        service_log = ServiceLog.objects.get()
        self.assertRedirects(
            response,
            reverse("worker_service_log_detail", args=[service_log.id]),
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["kun-bi@hotmail.com"])
        self.assertEqual(message.from_email, "notifications@bscare.com.au")
        self.assertIn("New service log submitted - Ava Nguyen", message.subject)
        self.assertIn("Participant: Ava Nguyen", message.body)
        self.assertIn("Worker: Wendy Worker", message.body)
        self.assertIn("Service date: 01/06/2026", message.body)
        self.assertIn("Actual hours: 2.00", message.body)
        self.assertIn("Kilometres: 4.50", message.body)
        self.assertIn(
            f"https://admin.bscare.com.au{reverse('service_log_detail', args=[service_log.id])}",
            message.body,
        )

    @override_settings(
        ADMIN_NOTIFICATION_EMAILS=["kun-bi@hotmail.com"],
        EMAIL_BACKEND="service_logs.tests_service_logs.FailingEmailBackend",
    )
    def test_worker_service_log_submission_continues_when_email_fails(self):
        shift = self.create_shift()
        self.login_worker()

        with self.assertLogs("service_logs.notifications", level="WARNING") as logs:
            response = self.client.post(
                reverse("worker_service_log_create", args=[shift.id]),
                self.log_payload(),
            )

        service_log = ServiceLog.objects.get()
        shift.refresh_from_db()
        self.assertIn("Failed to send service log notification email", logs.output[0])
        self.assertRedirects(
            response,
            reverse("worker_service_log_detail", args=[service_log.id]),
        )
        self.assertEqual(service_log.status, ServiceLog.Status.SUBMITTED)
        self.assertEqual(shift.status, Shift.Status.COMPLETED)

    def test_worker_can_open_complete_form_with_shift_defaults(self):
        shift = self.create_shift(status=Shift.Status.CONFIRMED)
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_create", args=[shift.id]))

        self.assertContains(response, "Complete Service Log")
        self.assertContains(response, "09:00")
        self.assertContains(response, "11:30")

    def test_worker_complete_form_displays_australian_shift_date(self):
        shift = self.create_shift(status=Shift.Status.CONFIRMED)
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_create", args=[shift.id]))

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, "<dt>Date</dt>", html=True)
        self.assertContains(response, "<dd>01/06/2026</dd>", html=True)
        self.assertNotContains(response, "Ava Nguyen | June 1, 2026 |")

    def test_worker_complete_form_uses_mobile_layout_hooks(self):
        shift = self.create_shift(status=Shift.Status.CONFIRMED)
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_create", args=[shift.id]))

        self.assertContains(response, 'class="worker-card worker-service-log-form-page"')
        self.assertContains(response, 'class="worker-log-shift-summary"')
        self.assertContains(response, 'class="worker-log-field-grid"')
        self.assertContains(response, 'class="worker-log-notes-grid"')
        self.assertContains(response, 'class="button-row worker-log-form-actions worker-bottom-actions"')
        self.assertContains(response, 'name="actual_start_time"')
        self.assertContains(response, 'name="actual_end_time"')
        self.assertContains(response, 'name="break_minutes"')
        self.assertContains(response, 'name="kilometres"')
        self.assertContains(response, 'name="case_notes"')
        self.assertContains(response, "Submit Service Log")

    def test_shift_can_only_have_one_service_log(self):
        shift = self.create_shift()
        ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("0.0"),
            case_notes="Already submitted.",
            worker_notes="",
        )
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_create", args=[shift.id]))

        self.assertEqual(response.status_code, 404)

    def test_worker_cannot_complete_another_workers_shift(self):
        shift = self.create_shift(worker=self.other_worker)
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_create", args=[shift.id]))

        self.assertEqual(response.status_code, 404)

    def test_worker_cannot_complete_draft_shift(self):
        shift = self.create_shift(status=Shift.Status.DRAFT)
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_create", args=[shift.id]))

        self.assertEqual(response.status_code, 404)

    def test_actual_end_time_must_be_after_start_time(self):
        shift = self.create_shift()
        self.login_worker()

        response = self.client.post(
            reverse("worker_service_log_create", args=[shift.id]),
            self.log_payload(actual_start_time="12:00", actual_end_time="11:00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Actual end time must be after actual start time")
        self.assertEqual(ServiceLog.objects.count(), 0)

    def test_worker_log_list_only_shows_own_logs(self):
        own_shift = self.create_shift()
        other_shift = self.create_shift(worker=self.other_worker)
        ServiceLog.objects.create_from_shift(
            shift=own_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("1.0"),
            case_notes="Own log.",
            worker_notes="",
        )
        ServiceLog.objects.create_from_shift(
            shift=other_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("1.0"),
            case_notes="Other worker log.",
            worker_notes="",
        )
        self.login_worker()

        response = self.client.get(reverse("worker_log_list"))

        self.assertContains(response, "Own log")
        self.assertNotContains(response, "Other worker log")

    def test_worker_log_surfaces_display_australian_dates(self):
        shift = self.create_shift()
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("1.0"),
            case_notes="Own log.",
            worker_notes="",
        )
        self.login_worker()

        list_response = self.client.get(reverse("worker_log_list"))
        detail_response = self.client.get(reverse("worker_service_log_detail", args=[service_log.id]))

        self.assertContains(list_response, "01/06/2026")
        self.assertNotContains(list_response, "June 1, 2026")
        self.assertContains(detail_response, "<dt>Date</dt><dd>01/06/2026</dd>", html=True)
        self.assertNotContains(detail_response, "<dt>Date</dt><dd>June 1, 2026</dd>", html=True)

    def test_worker_log_detail_displays_noon_as_numeric_time(self):
        shift = self.create_shift(end_time=time(12, 0))
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(12, 0),
            break_minutes=0,
            actual_hours=Decimal("3.00"),
            kilometres=Decimal("0.0"),
            case_notes="Noon finish.",
            worker_notes="",
        )
        self.login_worker()

        response = self.client.get(reverse("worker_service_log_detail", args=[service_log.id]))

        self.assertContains(response, "<dt>Actual time</dt><dd>9:00 am - 12:00 pm</dd>", html=True)
        self.assertNotContains(response, "noon")

    def test_admin_log_detail_displays_noon_as_numeric_time(self):
        shift = self.create_shift(end_time=time(12, 0))
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(12, 0),
            break_minutes=0,
            actual_hours=Decimal("3.00"),
            kilometres=Decimal("0.0"),
            case_notes="Noon finish.",
            worker_notes="",
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[service_log.id]))

        self.assertContains(response, "<dt>Actual time</dt><dd>9:00 am - 12:00 pm</dd>", html=True)
        self.assertNotContains(response, "noon")

    def test_admin_can_view_submitted_service_log_detail(self):
        shift = self.create_shift()
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("1.0"),
            case_notes="Submitted for review.",
            worker_notes="",
        )
        self.login_admin()

        list_response = self.client.get(reverse("service_log_list"))
        detail_response = self.client.get(reverse("service_log_detail", args=[service_log.id]))

        self.assertContains(list_response, "Submitted for review")
        self.assertContains(detail_response, "Submitted for review")
        self.assertContains(detail_response, str(shift.id))
