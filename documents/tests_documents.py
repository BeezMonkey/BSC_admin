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
from core.models import AuditLog
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
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "next": reverse("participant_document_files", args=[self.participant.id]),
            },
        )

        self.assertContains(response, "Uploading for")
        self.assertContains(response, self.participant.display_name)
        self.assertContains(response, self.worker.display_name)
        self.assertContains(
            response,
            f'name="next" value="{reverse("participant_document_files", args=[self.participant.id])}"',
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

    def test_document_create_prefills_others_category_from_shortcut(self):
        self.login_admin()

        response = self.client.get(
            reverse("document_create"),
            {
                "participant": self.participant.id,
                "category": "general",
            },
        )

        self.assertContains(response, "Uploading for")
        self.assertContains(
            response,
            '<option value="general" selected>Others</option>',
            html=True,
        )

    def test_participant_document_upload_shortcut_uses_simple_person_form(self):
        self.login_admin()

        response = self.client.get(
            reverse("document_create"),
            {
                "participant": self.participant.id,
                "category": "general",
                "next": reverse("participant_document_files", args=[self.participant.id]),
            },
        )

        self.assertContains(
            response,
            f"Upload file for {self.participant.display_name}",
        )
        self.assertContains(response, "Choose a folder, attach the file")
        self.assertContains(response, "Folder")
        self.assertNotContains(response, "Linked Records")
        self.assertNotContains(response, '<select name="participant"')
        self.assertNotContains(response, '<select name="worker"')
        self.assertNotContains(response, '<select name="invoice"')
        self.assertNotContains(response, '<select name="service_log"')
        self.assertContains(
            response,
            f'<input type="hidden" name="participant" value="{self.participant.id}"',
        )
        self.assertContains(response, '<option value="plan">Agreement</option>', html=True)
        self.assertContains(
            response,
            '<option value="compliance">NDIS Forms</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="general" selected>Others</option>',
            html=True,
        )
        self.assertNotContains(response, '<option value="invoice">Invoice</option>')
        self.assertNotContains(response, '<option value="service_log">Service log</option>')

    def test_worker_document_upload_shortcut_uses_simple_person_form(self):
        self.login_admin()

        response = self.client.get(
            reverse("document_create"),
            {
                "worker": self.worker.id,
                "category": "general",
                "next": reverse("worker_document_files", args=[self.worker.id]),
            },
        )

        self.assertContains(
            response,
            f"Upload file for {self.worker.display_name}",
        )
        self.assertContains(response, "Folder")
        self.assertNotContains(response, "Linked Records")
        self.assertNotContains(response, '<select name="participant"')
        self.assertNotContains(response, '<select name="worker"')
        self.assertContains(
            response,
            f'<input type="hidden" name="worker" value="{self.worker.id}"',
        )
        self.assertContains(response, '<option value="plan">Agreement</option>', html=True)
        self.assertContains(
            response,
            '<option value="compliance">Compliance</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="general" selected>Others</option>',
            html=True,
        )
        self.assertNotContains(response, "NDIS Forms")
        self.assertNotContains(response, '<option value="invoice">Invoice</option>')
        self.assertNotContains(response, '<option value="service_log">Service log</option>')

    def test_document_create_returns_to_selected_documents_after_shortcut_upload(self):
        self.login_admin()
        return_url = (
            f"{reverse('participant_document_files', args=[self.participant.id])}"
            "?category=others"
        )

        response = self.client.post(
            reverse("document_create"),
            self.document_payload(
                title="Provider contact note",
                category=Document.Category.GENERAL,
                next=return_url,
            ),
        )

        document = Document.objects.get()
        self.assertEqual(document.title, "Provider contact note")
        self.assertRedirects(response, return_url)

    def test_document_create_ignores_external_next_url(self):
        self.login_admin()

        response = self.client.post(
            reverse("document_create"),
            self.document_payload(next="https://example.invalid/documents/"),
        )

        document = Document.objects.get()
        self.assertRedirects(response, reverse("document_detail", args=[document.id]))

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

        self.assertContains(response, "document-directory-panel")

    def test_admin_document_file_manager_uses_uploaded_files_language(self):
        self.login_admin()

        response = self.client.get(reverse("document_list"))

        self.assertContains(response, "Uploaded Files")
        self.assertContains(response, "CrazyDomains")
        self.assertContains(response, "Upload File")
        self.assertContains(response, ">Uploaded Files</a>")
        self.assertNotContains(response, "Attach a file to one or more business records.")

    def test_admin_document_file_manager_hides_business_record_categories(self):
        self.login_admin()

        response = self.client.get(reverse("document_list"))

        self.assertContains(response, "Agreement")
        self.assertContains(response, "NDIS Forms")
        self.assertContains(response, "Others")
        self.assertNotContains(response, '<option value="invoice">')
        self.assertNotContains(response, '<option value="service_log">')
        self.assertNotContains(response, "Linked Records")

    def test_admin_document_directory_defaults_to_participant_people(self):
        participant_document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        worker_document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            original_filename="police-check.pdf",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_list"))

        self.assertContains(response, "Uploaded Files")
        self.assertContains(response, "Participants")
        self.assertContains(response, "Support Workers")
        self.assertContains(response, "Participant directory")
        self.assertContains(response, self.participant.display_name)
        self.assertContains(response, "1 files")
        self.assertContains(
            response,
            reverse("participant_document_files", args=[self.participant.id]),
        )
        self.assertContains(
            response,
            f"participant={self.participant.id}",
        )
        self.assertContains(
            response,
            f"next=%2Fdocuments%2Fparticipants%2F{self.participant.id}%2F",
        )
        self.assertNotContains(response, participant_document.title)
        self.assertNotContains(response, worker_document.title)

    def test_admin_document_directory_can_switch_to_support_workers(self):
        Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        worker_document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            original_filename="police-check.pdf",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("document_list"),
            {"owner": "workers"},
        )

        self.assertContains(response, "Support Worker directory")
        self.assertContains(response, "Wendy Worker")
        self.assertContains(response, "1 files")
        self.assertContains(
            response,
            f"worker={self.worker.id}",
        )
        self.assertContains(
            response,
            f"next=%2Fdocuments%2Fworkers%2F{self.worker.id}%2F",
        )
        self.assertNotContains(response, worker_document.title)
        self.assertNotContains(response, "Participant plan")

    def test_admin_document_directory_searches_people_without_long_sidebar(self):
        Participant.objects.create(
            first_name="Jia",
            last_name="Li",
            ndis_number="543210987",
        )
        self.login_admin()

        response = self.client.get(reverse("document_list"), {"q": "Ava"})

        self.assertContains(response, self.participant.display_name)
        self.assertNotContains(response, "Jia Li")
        self.assertContains(response, 'name="q"')

    def test_admin_participant_document_files_show_selected_person_documents(self):
        participant_document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        worker_document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            original_filename="police-check.pdf",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("participant_document_files", args=[self.participant.id])
        )

        self.assertContains(response, self.participant.display_name)
        self.assertContains(response, "Back to Uploaded Files")
        self.assertContains(response, participant_document.title)
        self.assertContains(response, "plan.pdf")
        self.assertContains(response, "Agreement")
        self.assertContains(response, "NDIS Forms")
        self.assertContains(response, "Others")
        self.assertNotContains(response, 'href="/documents/participants/1/?category=invoice"')
        self.assertNotContains(response, 'href="/documents/participants/1/?category=service_log"')
        self.assertNotContains(response, "Linked Records")
        self.assertContains(
            response,
            f"next=%2Fdocuments%2Fparticipants%2F{self.participant.id}%2F",
        )
        self.assertNotContains(response, worker_document.title)

    def test_admin_person_file_page_has_inline_upload_dialog(self):
        self.login_admin()

        response = self.client.get(
            reverse("participant_document_files", args=[self.participant.id])
        )

        self.assertContains(response, 'id="document-upload-dialog"')
        self.assertContains(response, 'action="/documents/new/"')
        self.assertContains(
            response,
            f'<input type="hidden" name="participant" value="{self.participant.id}">',
            html=True,
        )
        self.assertContains(response, '<option value="plan">Agreement</option>', html=True)
        self.assertContains(
            response,
            '<option value="compliance">NDIS Forms</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="general" selected>Others</option>',
            html=True,
        )
        self.assertNotContains(response, '<select name="invoice"')
        self.assertNotContains(response, '<select name="service_log"')

    def test_admin_worker_document_files_show_selected_worker_documents(self):
        Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        worker_document = Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=self.worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file=self.upload_file("police-check.pdf"),
            original_filename="police-check.pdf",
            uploaded_by=self.worker_user,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_document_files", args=[self.worker.id]))

        self.assertContains(response, self.worker.display_name)
        self.assertContains(response, "Support worker file folder")
        self.assertContains(response, worker_document.title)
        self.assertContains(response, "police-check.pdf")
        self.assertContains(response, "Pending review")
        self.assertContains(response, "Agreement")
        self.assertContains(response, "Compliance")
        self.assertContains(response, "Others")
        self.assertNotContains(response, "NDIS Forms")
        self.assertNotContains(response, 'href="/documents/workers/1/?category=invoice"')
        self.assertNotContains(response, 'href="/documents/workers/1/?category=service_log"')
        self.assertContains(
            response,
            f"next=%2Fdocuments%2Fworkers%2F{self.worker.id}%2F",
        )
        self.assertNotContains(response, "Participant plan")

    def test_legacy_document_person_query_redirects_to_dedicated_detail_page(self):
        self.login_admin()

        response = self.client.get(
            reverse("document_list"),
            {
                "owner": "participants",
                "person": self.participant.id,
                "category": "others",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('participant_document_files', args=[self.participant.id])}?category=others",
        )

    def test_admin_document_files_filter_selected_person_others(self):
        other_participant = Participant.objects.create(
            first_name="Jia",
            last_name="Li",
            ndis_number="543210987",
        )
        Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        other_document = Document.objects.create(
            title="Provider contact note",
            category=Document.Category.GENERAL,
            participant=other_participant,
            file=self.upload_file("provider-note.docx"),
            original_filename="provider-note.docx",
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("participant_document_files", args=[other_participant.id]),
            {
                "category": "others",
            },
        )

        self.assertContains(response, "Others")
        self.assertContains(response, other_participant.display_name)
        self.assertContains(response, other_document.title)
        self.assertContains(response, "provider-note.docx")
        self.assertContains(response, "category=general")
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

    def test_admin_document_files_link_to_delete_confirmation(self):
        document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("participant_document_files", args=[self.participant.id])
        )

        self.assertContains(response, "Delete")
        self.assertContains(response, reverse("document_delete", args=[document.id]))

    def test_admin_document_detail_links_to_delete_confirmation(self):
        document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(reverse("document_detail", args=[document.id]))

        self.assertContains(response, "Delete")
        self.assertContains(response, reverse("document_delete", args=[document.id]))

    def test_admin_document_delete_confirmation_shows_file_context(self):
        document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("document_delete", args=[document.id]),
            {
                "next": (
                    f"{reverse('document_list')}?owner=participants"
                    f"&person={self.participant.id}"
                )
            },
        )

        self.assertContains(response, "Delete uploaded file")
        self.assertContains(response, "Participant plan")
        self.assertContains(response, "plan.pdf")
        self.assertContains(response, self.participant.display_name)
        self.assertContains(response, "This will delete the database record and private file.")

    def test_admin_can_delete_document_and_private_file(self):
        document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        stored_name = document.file.name
        self.assertTrue(document.file.storage.exists(stored_name))
        self.login_admin()
        return_url = reverse("participant_document_files", args=[self.participant.id])

        response = self.client.post(
            reverse("document_delete", args=[document.id]),
            {"next": return_url},
        )

        self.assertRedirects(response, return_url)
        self.assertFalse(Document.objects.filter(id=document.id).exists())
        self.assertFalse(document.file.storage.exists(stored_name))
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.DOCUMENT_DELETED,
                object_id=str(document.id),
            ).exists()
        )

    def test_document_delete_keeps_record_when_private_file_delete_fails(self):
        document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        self.login_admin()

        with patch.object(
            document.file.storage,
            "delete",
            side_effect=StorageOperationError("Could not delete document from private storage."),
        ):
            response = self.client.post(reverse("document_delete", args=[document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not delete document from private storage")
        self.assertTrue(Document.objects.filter(id=document.id).exists())
        self.assertFalse(
            AuditLog.objects.filter(
                action=AuditLog.Action.DOCUMENT_DELETED,
                object_id=str(document.id),
            ).exists()
        )

    def test_worker_cannot_delete_document_from_admin_view(self):
        document = Document.objects.create(
            title="Participant plan",
            category=Document.Category.PLAN,
            participant=self.participant,
            file=self.upload_file("plan.pdf"),
            original_filename="plan.pdf",
            uploaded_by=self.admin_user,
        )
        self.login_worker()

        response = self.client.post(reverse("document_delete", args=[document.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(id=document.id).exists())

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
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")

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

    def test_person_upload_storage_error_keeps_simple_form(self):
        self.login_admin()

        with patch(
            "documents.views.Document.save",
            side_effect=StorageOperationError("Could not upload document to private storage."),
        ):
            response = self.client.post(
                reverse("document_create"),
                self.document_payload(
                    category=Document.Category.GENERAL,
                    next=reverse("participant_document_files", args=[self.participant.id]),
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"Upload file for {self.participant.display_name}",
        )
        self.assertContains(response, "Could not upload document to private storage")
        self.assertNotContains(response, "Linked Records")
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

        response = self.client.get(
            reverse("worker_document_files", args=[self.worker.id]),
        )

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
