from datetime import date, datetime, time, timezone as datetime_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from documents.models import Document
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class ServiceLogReviewTests(TestCase):
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
        self.support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 30),
            break_minutes=30,
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        self.service_log = ServiceLog.objects.create_from_shift(
            shift=self.shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 30),
            break_minutes=30,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("1.0"),
            case_notes="Submitted for review.",
            worker_notes="",
        )

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def test_admin_can_approve_submitted_service_log(self):
        self.login_admin()

        response = self.client.post(
            reverse("service_log_approve", args=[self.service_log.id]),
        )

        self.service_log.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("service_log_detail", args=[self.service_log.id]),
        )
        self.assertEqual(self.service_log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(self.service_log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.service_log.reviewed_at)

    def test_admin_can_reject_submitted_service_log_with_reason(self):
        self.login_admin()

        response = self.client.post(
            reverse("service_log_reject", args=[self.service_log.id]),
            {"rejection_reason": "Please clarify case notes."},
        )

        self.service_log.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("service_log_detail", args=[self.service_log.id]),
        )
        self.assertEqual(self.service_log.status, ServiceLog.Status.REJECTED)
        self.assertEqual(self.service_log.rejection_reason, "Please clarify case notes.")
        self.assertEqual(self.service_log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.service_log.reviewed_at)

    def test_reject_requires_reason(self):
        self.login_admin()

        response = self.client.post(
            reverse("service_log_reject", args=[self.service_log.id]),
            {"rejection_reason": "   "},
        )

        self.service_log.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("service_log_detail", args=[self.service_log.id]),
        )
        self.assertEqual(self.service_log.status, ServiceLog.Status.SUBMITTED)
        self.assertEqual(self.service_log.rejection_reason, "")

    def test_worker_can_see_rejection_reason(self):
        self.service_log.status = ServiceLog.Status.REJECTED
        self.service_log.rejection_reason = "Please clarify case notes."
        self.service_log.reviewed_by = self.admin_user
        self.service_log.save(
            update_fields=["status", "rejection_reason", "reviewed_by", "updated_at"],
        )
        self.login_worker()

        response = self.client.get(
            reverse("worker_service_log_detail", args=[self.service_log.id]),
        )

        self.assertContains(response, "Rejected")
        self.assertContains(response, "Please clarify case notes.")

    def test_worker_cannot_approve_service_log(self):
        self.login_worker()

        response = self.client.post(
            reverse("service_log_approve", args=[self.service_log.id]),
        )

        self.service_log.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.service_log.status, ServiceLog.Status.SUBMITTED)

    def test_admin_can_filter_service_logs_by_status(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        other_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 2),
            start_time=time(12, 0),
            end_time=time(13, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        ServiceLog.objects.create_from_shift(
            shift=other_shift,
            actual_start_time=time(12, 0),
            actual_end_time=time(13, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Submitted log.",
            worker_notes="",
        )
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, "Submitted for review.")
        self.assertNotContains(response, "Submitted log.")

    def test_service_log_list_renders_status_specific_class(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="status-pill status-approved"')

    def test_service_log_list_displays_australian_date_format(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, ">01/06/2026</a>")
        self.assertNotContains(response, ">June 1, 2026</a>")

    def test_service_log_detail_displays_australian_date_format(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, "01/06/2026 |")
        self.assertNotContains(response, "June 1, 2026 |")

    def test_service_log_detail_displays_australian_datetime_format(self):
        self.service_log.reviewed_by = self.admin_user
        self.service_log.reviewed_at = datetime(2026, 6, 3, 23, 30, tzinfo=datetime_timezone.utc)
        self.service_log.submitted_at = datetime(2026, 6, 3, 22, 15, tzinfo=datetime_timezone.utc)
        self.service_log.save(update_fields=["reviewed_by", "reviewed_at", "submitted_at", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, "<dt>Reviewed at</dt><dd>04/06/2026 09:30</dd>", html=True)
        self.assertContains(response, "<dt>Submitted</dt><dd>04/06/2026 08:15</dd>", html=True)
        self.assertNotContains(response, "June 4, 2026")

    def test_submitted_service_log_detail_hides_empty_review_metadata(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertNotContains(response, "<dt>Reviewed by</dt>")
        self.assertNotContains(response, "<dt>Reviewed at</dt>")
        self.assertNotContains(response, "<dt>Rejection reason</dt>")

    def test_rejected_service_log_detail_shows_rejection_reason(self):
        self.service_log.status = ServiceLog.Status.REJECTED
        self.service_log.rejection_reason = "Please clarify case notes."
        self.service_log.reviewed_by = self.admin_user
        self.service_log.reviewed_at = datetime(2026, 6, 3, 23, 30, tzinfo=datetime_timezone.utc)
        self.service_log.save(
            update_fields=[
                "status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ],
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(
            response,
            "<dt>Rejection reason</dt><dd>Please clarify case notes.</dd>",
            html=True,
        )

    def test_admin_can_download_service_log_pdf(self):
        self.service_log.worker_notes = "Worker confirms support was completed."
        self.service_log.save(update_fields=["worker_notes", "updated_at"])
        Document.objects.create(
            title="Service log attachment - progress-photo.jpg",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file=SimpleUploadedFile(
                "progress-photo.jpg",
                b"photo",
                content_type="image/jpeg",
            ),
            original_filename="progress-photo.jpg",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_pdf", args=[self.service_log.id]))

        content = response.content.decode("latin-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("SERVICE LOG", content)
        self.assertIn("Ava Nguyen", content)
        self.assertIn("Wendy Worker", content)
        self.assertIn("01/06/2026", content)
        self.assertIn("01_011_0107_1_1", content)
        self.assertIn("Submitted for review.", content)
        self.assertIn("Worker confirms support was completed.", content)
        self.assertIn("progress-photo.jpg", content)

    def test_service_log_pdf_uses_clear_download_filename(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_pdf", args=[self.service_log.id]))

        self.assertIn(
            f'filename="ServiceLog_20260601_{self.service_log.id}_Ava_Nguyen.pdf"',
            response["Content-Disposition"],
        )

    def test_admin_service_log_detail_links_to_pdf(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, "Download PDF")
        self.assertContains(response, reverse("service_log_pdf", args=[self.service_log.id]))

    def test_admin_service_log_detail_marks_unscheduled_service(self):
        self.shift.source = "unscheduled"
        self.shift.save(update_fields=["source", "updated_at"])
        self.service_log.source = "unscheduled"
        self.service_log.unscheduled_reason = "Participant requested urgent support."
        self.service_log.save(update_fields=["source", "unscheduled_reason", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, "<dt>Service type</dt><dd>Unscheduled</dd>", html=True)
        self.assertContains(
            response,
            "<dt>Unscheduled reason</dt><dd>Participant requested urgent support.</dd>",
            html=True,
        )

    def test_service_log_list_marks_unscheduled_service(self):
        self.shift.source = "unscheduled"
        self.shift.save(update_fields=["source", "updated_at"])
        self.service_log.source = "unscheduled"
        self.service_log.unscheduled_reason = "Participant requested urgent support."
        self.service_log.save(update_fields=["source", "unscheduled_reason", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="status-source-stack"')
        self.assertContains(response, '<span class="source-pill source-unscheduled">Unscheduled</span>')

    def test_service_log_pdf_marks_unscheduled_service(self):
        self.shift.source = "unscheduled"
        self.shift.save(update_fields=["source", "updated_at"])
        self.service_log.source = "unscheduled"
        self.service_log.unscheduled_reason = "Participant requested urgent support."
        self.service_log.save(update_fields=["source", "unscheduled_reason", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_pdf", args=[self.service_log.id]))

        content = response.content.decode("latin-1")
        self.assertIn("Service type", content)
        self.assertIn("Unscheduled", content)
        self.assertIn("Participant requested urgent support.", content)

    def test_admin_service_log_detail_uses_preview_cards_for_image_attachments(self):
        document = Document.objects.create(
            title="Service log attachment - progress-photo.jpg",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file="documents/progress-photo.jpg",
            original_filename="progress-photo.jpg",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, 'class="service-log-attachment-card"')
        self.assertContains(response, 'data-preview-kind="image"')
        self.assertContains(response, reverse("document_preview", args=[document.id]))
        self.assertContains(response, "Download")
        self.assertNotContains(
            response,
            f'href="{reverse("document_detail", args=[document.id])}"',
        )

    def test_admin_service_log_detail_uses_pdf_preview_and_doc_download_only(self):
        pdf_document = Document.objects.create(
            title="Service log attachment - incident-summary.pdf",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file="documents/incident-summary.pdf",
            original_filename="incident-summary.pdf",
            uploaded_by=self.worker_user,
        )
        doc_document = Document.objects.create(
            title="Service log attachment - worker-notes.docx",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file="documents/worker-notes.docx",
            original_filename="worker-notes.docx",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, 'data-preview-kind="pdf"')
        self.assertContains(response, reverse("document_preview", args=[pdf_document.id]))
        self.assertNotContains(response, "Download to review")
        self.assertContains(response, reverse("document_download", args=[doc_document.id]))
        self.assertNotContains(response, reverse("document_preview", args=[doc_document.id]))

    def test_submitted_service_log_detail_uses_reject_disclosure(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_detail", args=[self.service_log.id]))

        self.assertContains(response, 'class="service-log-detail-page"')
        self.assertContains(response, 'class="service-log-review-actions"')
        self.assertContains(response, '<summary class="button danger-outline">Reject</summary>', html=True)
        self.assertContains(response, "Reject with reason")
        self.assertContains(response, 'name="rejection_reason"')

    def test_worker_cannot_download_admin_service_log_pdf(self):
        self.login_worker()

        response = self.client.get(reverse("service_log_pdf", args=[self.service_log.id]))

        self.assertEqual(response.status_code, 403)

    def test_service_log_list_shows_status_filter_summary(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, "Showing approved service logs.")
        self.assertContains(response, reverse("service_log_list"))

    def test_service_log_list_shows_status_overview_cards(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        submitted_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 2),
            start_time=time(12, 0),
            end_time=time(13, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        ServiceLog.objects.create_from_shift(
            shift=submitted_shift,
            actual_start_time=time(12, 0),
            actual_end_time=time(13, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Another submitted log.",
            worker_notes="",
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="service-log-status-grid"')
        self.assertContains(response, "All logs")
        self.assertContains(response, "2 records")
        self.assertContains(response, "Submitted")
        self.assertContains(response, "1 waiting")
        self.assertContains(response, "Approved")
        self.assertContains(response, "1 ready")
        self.assertContains(response, f'?status={ServiceLog.Status.SUBMITTED}')
        self.assertContains(response, f'?status={ServiceLog.Status.APPROVED}')

    def test_service_log_list_marks_active_status_overview_card(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, 'class="service-log-status-card active"')
        self.assertContains(response, "Ready to invoice")

    def test_service_log_list_uses_workbench_filter_and_bulk_actions(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="filter-bar service-log-filter-bar"')
        self.assertContains(response, 'class="bulk-actions service-log-bulk-actions"')
        self.assertContains(response, "Billing action")
        self.assertContains(response, "Select approved rows to create an invoice.")

    def test_service_log_list_uses_readable_record_cells(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="service-log-date-stack"')
        self.assertContains(response, 'class="service-log-person-stack"')
        self.assertContains(response, 'class="service-log-person-name"')
        self.assertContains(response, 'class="service-log-role-label"')
        self.assertContains(response, "Participant")
        self.assertContains(response, "Support worker")
        self.assertContains(response, 'class="service-log-notes-preview"')
        self.assertContains(response, "Submitted")

    def test_service_log_list_is_paginated_and_preserves_filters(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        for index in range(2, 26):
            shift = Shift.objects.create(
                participant=self.participant,
                worker=self.worker,
                service_date=date(2026, 6, index),
                start_time=time(9, 0),
                end_time=time(10, 0),
                break_minutes=0,
                planned_hours=Decimal("1.00"),
                support_item=self.support_item,
                service_type=Shift.ServiceType.PERSONAL_CARE,
                status=Shift.Status.COMPLETED,
                created_by=self.admin_user,
            )
            service_log = ServiceLog.objects.create_from_shift(
                shift=shift,
                actual_start_time=time(9, 0),
                actual_end_time=time(10, 0),
                break_minutes=0,
                actual_hours=Decimal("1.00"),
                kilometres=Decimal("0.0"),
                case_notes=f"Approved log {index}",
                worker_notes="",
            )
            service_log.status = ServiceLog.Status.APPROVED
            service_log.save(update_fields=["status", "updated_at"])
        submitted_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 26),
            start_time=time(9, 0),
            end_time=time(10, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        ServiceLog.objects.create_from_shift(
            shift=submitted_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(10, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Submitted log outside filter.",
            worker_notes="",
        )
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertEqual(response.context["service_logs"].paginator.count, 25)
        self.assertEqual(len(response.context["service_logs"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(response, "?status=approved&amp;page=2")
        self.assertNotContains(response, "Submitted log outside filter.")

    def test_service_log_list_can_sort_by_date_and_preserve_filters(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        later_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 3),
            start_time=time(9, 0),
            end_time=time(10, 0),
            break_minutes=0,
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        later_log = ServiceLog.objects.create_from_shift(
            shift=later_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(10, 0),
            break_minutes=0,
            actual_hours=Decimal("1.00"),
            kilometres=Decimal("0.0"),
            case_notes="Later approved log.",
            worker_notes="",
        )
        later_log.status = ServiceLog.Status.APPROVED
        later_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED, "sort": "date", "direction": "asc"},
        )
        content = response.content.decode()

        self.assertLess(content.index("01/06/2026"), content.index("03/06/2026"))
        self.assertContains(response, "?status=approved&amp;sort=date&amp;direction=desc")

    def test_service_log_list_distinguishes_empty_filter_results(self):
        self.login_admin()

        response = self.client.get(
            reverse("service_log_list"),
            {"status": ServiceLog.Status.APPROVED},
        )

        self.assertContains(response, "No service logs match the current filters.")
        self.assertContains(response, "Clear filters")
        self.assertNotContains(response, "Service logs appear here after workers complete")

    def test_admin_service_log_list_has_explicit_view_action(self):
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, "Actions")
        self.assertContains(response, reverse("service_log_detail", args=[self.service_log.id]))
        self.assertContains(response, "View")

    def test_service_log_list_uses_dense_table_structure(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="service-log-table"')
        self.assertContains(response, 'class="notes-cell"')
        self.assertContains(response, 'name="service_log_ids"')
        self.assertContains(response, "Create Invoice")

    def test_service_log_list_uses_readability_table_classes(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, 'class="card table-card service-log-table-card"')
        self.assertContains(response, 'class="service-log-date-cell"')
        self.assertContains(response, 'class="service-log-person-cell"')
        self.assertContains(response, 'class="service-log-status-cell"')
        self.assertContains(response, 'class="service-log-hours-cell numeric-cell"')
        self.assertContains(response, 'class="actions service-log-actions-cell"')

    def test_service_log_detail_back_link_preserves_list_state(self):
        self.service_log.status = ServiceLog.Status.APPROVED
        self.service_log.save(update_fields=["status", "updated_at"])
        list_path = f"{reverse('service_log_list')}?status=approved&sort=date&direction=desc&page=2"
        self.login_admin()

        list_response = self.client.get(list_path)
        detail_response = self.client.get(
            reverse("service_log_detail", args=[self.service_log.id]),
            {"next": list_path},
        )

        self.assertContains(
            list_response,
            f"{reverse('service_log_detail', args=[self.service_log.id])}?next=",
        )
        self.assertContains(detail_response, f'href="{list_path.replace("&", "&amp;")}"')
