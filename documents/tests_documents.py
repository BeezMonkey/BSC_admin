from datetime import date, time
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from documents.models import Document
from documents.storage import StorageOperationError
from invoices.models import Invoice
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class DocumentManagementTests(TestCase):
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
        self.shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            break_minutes=0,
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        self.service_log = ServiceLog.objects.create_from_shift(
            shift=self.shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            break_minutes=0,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("0.0"),
            case_notes="Document test log.",
            worker_notes="",
        )
        self.invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.admin_user,
        )

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def upload_file(self, name="document.pdf", content=b"file-content"):
        return SimpleUploadedFile(name, content, content_type="application/octet-stream")

    def document_payload(self, **overrides):
        data = {
            "title": "Participant plan",
            "category": Document.Category.PLAN,
            "participant": self.participant.id,
            "worker": "",
            "invoice": "",
            "service_log": "",
            "notes": "Uploaded plan.",
            "file": self.upload_file(),
        }
        data.update(overrides)
        return data

    def test_admin_can_upload_participant_document(self):
        self.login_admin()

        response = self.client.post(reverse("document_create"), self.document_payload())

        document = Document.objects.get()
        self.assertRedirects(response, reverse("document_detail", args=[document.id]))
        self.assertEqual(document.title, "Participant plan")
        self.assertEqual(document.participant, self.participant)
        self.assertEqual(document.uploaded_by, self.admin_user)
        self.assertTrue(document.file.name.startswith("documents/"))

    def test_document_create_prefills_linked_record_from_shortcut(self):
        self.login_admin()

        response = self.client.get(
            reverse("document_create"),
            {"participant": self.participant.id, "worker": self.worker.id},
        )

        self.assertContains(
            response,
            f'<option value="{self.participant.id}" selected>{self.participant.display_name}</option>',
            html=True,
        )
        self.assertContains(
            response,
            f'<option value="{self.worker.id}" selected>{self.worker.display_name}</option>',
            html=True,
        )

    def test_document_create_marks_documents_sidebar_link_as_active(self):
        self.login_admin()

        response = self.client.get(reverse("document_create"))

        self.assertContains(
            response,
            f'class="sidebar-link active" href="{reverse("document_list")}"',
        )

    def test_document_list_wraps_table_for_small_screens(self):
        self.login_admin()

        response = self.client.get(reverse("document_list"))

        self.assertContains(response, 'class="card table-card"')

    def test_admin_document_list_focuses_worker_compliance_documents(self):
        worker_document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            uploaded_by=self.worker_user,
        )
        Document.objects.create(
            title="Service receipt",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file=self.upload_file("receipt.pdf"),
            uploaded_by=self.worker_user,
        )
        Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_list"))

        self.assertContains(response, "Compliance Documents")
        self.assertContains(response, "Review worker compliance uploads")
        self.assertContains(response, worker_document.title)
        self.assertContains(response, "Wendy Worker")
        self.assertContains(response, "Police Check")
        self.assertNotContains(response, "Service receipt")
        self.assertNotContains(response, "Participant plan")

    def test_document_create_uses_record_form_layout(self):
        self.login_admin()

        response = self.client.get(reverse("document_create"))

        self.assertContains(response, 'class="record-form"')
        self.assertContains(response, 'class="card form-section"')
        self.assertNotContains(response, "<p>\n    <label")

    def test_admin_can_view_and_download_document(self):
        document = Document.objects.create(
            title="Worker compliance",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            file=self.upload_file("compliance.pdf"),
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        detail_response = self.client.get(reverse("document_detail", args=[document.id]))
        download_response = self.client.get(reverse("document_download", args=[document.id]))

        self.assertContains(detail_response, "Worker compliance")
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.content, b"file-content")

    def test_admin_can_preview_image_document_inline(self):
        document = Document.objects.create(
            title="Progress photo",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file=SimpleUploadedFile(
                "progress-photo.jpg",
                b"image-bytes",
                content_type="image/jpeg",
            ),
            original_filename="progress-photo.jpg",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_preview", args=[document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(
            response["Content-Disposition"],
            'inline; filename="progress-photo.jpg"',
        )
        self.assertEqual(response.content, b"image-bytes")

    def test_admin_can_preview_pdf_document_inline(self):
        document = Document.objects.create(
            title="Progress PDF",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file=SimpleUploadedFile(
                "progress-summary.pdf",
                b"%PDF-1.4",
                content_type="application/pdf",
            ),
            original_filename="progress-summary.pdf",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_preview", args=[document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            'inline; filename="progress-summary.pdf"',
        )

    def test_admin_preview_returns_not_found_for_unpreviewable_documents(self):
        document = Document.objects.create(
            title="Worker notes",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file=SimpleUploadedFile(
                "worker-notes.docx",
                b"docx-bytes",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            original_filename="worker-notes.docx",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_preview", args=[document.id]))

        self.assertEqual(response.status_code, 404)

    def test_worker_cannot_use_admin_document_preview(self):
        document = Document.objects.create(
            title="Progress photo",
            category=Document.Category.SERVICE_LOG,
            participant=self.participant,
            worker=self.worker,
            service_log=self.service_log,
            file=SimpleUploadedFile(
                "progress-photo.jpg",
                b"image-bytes",
                content_type="image/jpeg",
            ),
            original_filename="progress-photo.jpg",
            uploaded_by=self.worker_user,
        )
        self.login_worker()

        response = self.client.get(reverse("document_preview", args=[document.id]))

        self.assertEqual(response.status_code, 403)

    def test_admin_upload_shows_error_when_private_storage_fails(self):
        self.login_admin()

        with patch(
            "documents.views.Document.save",
            side_effect=StorageOperationError("Could not upload document to private storage."),
        ):
            response = self.client.post(reverse("document_create"), self.document_payload())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not upload document to private storage")
        self.assertEqual(Document.objects.count(), 0)

    def test_upload_requires_linked_object(self):
        self.login_admin()

        response = self.client.post(
            reverse("document_create"),
            self.document_payload(participant="", worker="", invoice="", service_log=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select at least one linked record")
        self.assertEqual(Document.objects.count(), 0)

    def test_unsupported_file_extension_is_rejected(self):
        self.login_admin()

        response = self.client.post(
            reverse("document_create"),
            self.document_payload(file=self.upload_file("script.exe")),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unsupported file type")
        self.assertEqual(Document.objects.count(), 0)

    def test_oversized_file_is_rejected(self):
        self.login_admin()

        response = self.client.post(
            reverse("document_create"),
            self.document_payload(file=self.upload_file("large.pdf", b"x" * (10 * 1024 * 1024 + 1))),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "File size cannot exceed 10 MB")
        self.assertEqual(Document.objects.count(), 0)

    def test_worker_sees_only_own_worker_documents(self):
        own_document = Document.objects.create(
            title="Own compliance",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            file=self.upload_file("own.pdf"),
            uploaded_by=self.admin_user,
        )
        Document.objects.create(
            title="Other compliance",
            category=Document.Category.COMPLIANCE,
            worker=self.other_worker,
            file=self.upload_file("other.pdf"),
            uploaded_by=self.admin_user,
        )
        Document.objects.create(
            title="Participant private",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("participant.pdf"),
            uploaded_by=self.admin_user,
        )
        self.login_worker()

        response = self.client.get(reverse("worker_document_list"))

        self.assertContains(response, "Own compliance")
        self.assertContains(response, str(own_document.id))
        self.assertNotContains(response, "Other compliance")
        self.assertNotContains(response, "Participant private")

    def test_worker_cannot_access_participant_document(self):
        document = Document.objects.create(
            title="Participant private",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("participant.pdf"),
            uploaded_by=self.admin_user,
        )
        self.login_worker()

        response = self.client.get(reverse("worker_document_detail", args=[document.id]))

        self.assertEqual(response.status_code, 404)

    def test_worker_document_list_shows_required_compliance_uploads(self):
        self.login_worker()

        response = self.client.get(reverse("worker_document_list"))

        self.assertContains(response, "Required compliance documents")
        self.assertContains(response, "Police Check")
        self.assertContains(response, "NDIS Worker Screening Check")
        self.assertContains(response, "Upload Other Document")
        self.assertContains(response, reverse("worker_document_upload"))

    def test_required_document_upload_locks_selected_type(self):
        self.login_worker()

        response = self.client.get(
            reverse("worker_document_upload"),
            {"type": Document.RequiredDocumentType.POLICE_CHECK},
        )

        self.assertContains(response, "Upload Police Check")
        self.assertContains(
            response,
            '<input type="hidden" name="required_document_type" value="police_check"',
        )
        self.assertContains(response, "Document type")
        self.assertContains(response, "Police Check")
        self.assertNotContains(response, '<select name="required_document_type"')

    def test_uploaded_required_document_uses_view_and_replace_actions(self):
        Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.APPROVED,
            file=self.upload_file("police-check.pdf"),
            uploaded_by=self.worker_user,
        )
        self.login_worker()

        response = self.client.get(reverse("worker_document_list"))

        self.assertContains(response, "Approved")
        self.assertContains(response, ">View<")
        self.assertContains(response, ">Replace<")
        self.assertNotContains(response, "?type=police_check\">Upload</a>")

    def test_rejected_required_document_prompts_upload_again(self):
        Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.REJECTED,
            file=self.upload_file("police-check.pdf"),
            uploaded_by=self.worker_user,
        )
        self.login_worker()

        response = self.client.get(reverse("worker_document_list"))

        self.assertContains(response, "Rejected")
        self.assertContains(response, ">View<")
        self.assertContains(response, ">Upload again<")

    def test_worker_can_upload_own_compliance_document_for_review(self):
        self.login_worker()

        response = self.client.post(
            reverse("worker_document_upload"),
            {
                "required_document_type": Document.RequiredDocumentType.POLICE_CHECK,
                "issue_date": "2026-06-01",
                "expiry_date": "2027-06-01",
                "notes": "Updated police check.",
                "file": self.upload_file("police-check.pdf", b"police-check"),
            },
        )

        document = Document.objects.get(title="Police Check")
        self.assertRedirects(response, reverse("worker_document_list"))
        self.assertEqual(document.category, Document.Category.COMPLIANCE)
        self.assertEqual(document.worker, self.worker)
        self.assertIsNone(document.participant)
        self.assertEqual(document.uploaded_by, self.worker_user)
        self.assertEqual(document.required_document_type, Document.RequiredDocumentType.POLICE_CHECK)
        self.assertEqual(document.review_status, Document.ReviewStatus.PENDING_REVIEW)
        self.assertEqual(document.original_filename, "police-check.pdf")

    def test_worker_can_upload_other_document_for_review(self):
        self.login_worker()

        response = self.client.post(
            reverse("worker_document_upload"),
            {
                "title": "Medication certificate",
                "notes": "Extra training record.",
                "file": self.upload_file("medication.pdf", b"medication"),
            },
        )

        document = Document.objects.get()
        self.assertRedirects(response, reverse("worker_document_list"))
        self.assertEqual(document.title, "Medication certificate")
        self.assertEqual(document.category, Document.Category.COMPLIANCE)
        self.assertEqual(document.worker, self.worker)
        self.assertEqual(document.required_document_type, "")
        self.assertEqual(document.review_status, Document.ReviewStatus.PENDING_REVIEW)

    def test_worker_compliance_upload_rejects_unsupported_file(self):
        self.login_worker()

        response = self.client.post(
            reverse("worker_document_upload"),
            {
                "required_document_type": Document.RequiredDocumentType.POLICE_CHECK,
                "file": self.upload_file("malware.exe", b"not really"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unsupported file type")
        self.assertEqual(Document.objects.count(), 0)

    def test_worker_compliance_upload_shows_error_when_private_storage_fails(self):
        self.login_worker()

        with patch(
            "documents.views.Document.objects.create",
            side_effect=StorageOperationError("Could not upload document to private storage."),
        ):
            response = self.client.post(
                reverse("worker_document_upload"),
                {
                    "required_document_type": Document.RequiredDocumentType.POLICE_CHECK,
                    "file": self.upload_file("police-check.pdf", b"police-check"),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not upload document to private storage")
        self.assertEqual(Document.objects.count(), 0)

    def test_admin_document_list_shows_worker_upload_review_status(self):
        Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_list"))

        self.assertContains(response, "Pending review")

    def test_admin_can_approve_pending_worker_document(self):
        document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("document_review", args=[document.id]),
            {"review_status": Document.ReviewStatus.APPROVED},
        )

        document.refresh_from_db()
        self.assertRedirects(response, reverse("document_detail", args=[document.id]))
        self.assertEqual(document.review_status, Document.ReviewStatus.APPROVED)

    def test_admin_can_reject_pending_worker_document_with_note(self):
        document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("document_review", args=[document.id]),
            {
                "review_status": Document.ReviewStatus.REJECTED,
                "review_note": "Please upload a clearer copy.",
            },
        )

        document.refresh_from_db()
        self.assertRedirects(response, reverse("document_detail", args=[document.id]))
        self.assertEqual(document.review_status, Document.ReviewStatus.REJECTED)
        self.assertIn("Review note: Please upload a clearer copy.", document.notes)
