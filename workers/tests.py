from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from documents.models import Document
from participants.models import Participant, ParticipantWorkerAssignment
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog

from .models import SupportWorker


class SupportWorkerManagementTests(TestCase):
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
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.worker_user = self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def worker_payload(self, **overrides):
        data = {
            "username": "newworker",
            "email": "newworker@example.com",
            "password1": "WorkerPass123!",
            "password2": "WorkerPass123!",
            "account_active": "on",
            "first_name": "Maya",
            "last_name": "Singh",
            "phone": "0400000000",
            "address": "12 River Street, Brisbane",
            "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
            "abn": "",
            "start_date": "2026-02-01",
            "status": SupportWorker.Status.ACTIVE,
            "police_check_status": SupportWorker.ComplianceStatus.CURRENT,
            "police_check_expiry": "2027-02-01",
            "wwcc_status": SupportWorker.ComplianceStatus.CURRENT,
            "wwcc_expiry": "2027-03-01",
            "notes": "Experienced worker.",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_worker_account_and_profile(self):
        self.login_admin()

        response = self.client.post(reverse("worker_create"), self.worker_payload())

        worker = SupportWorker.objects.get(user__username="newworker")
        self.assertRedirects(response, reverse("worker_detail", args=[worker.id]))
        self.assertEqual(worker.user.userprofile.role, UserProfile.Role.SUPPORT_WORKER)
        self.assertTrue(worker.user.check_password("WorkerPass123!"))
        self.assertEqual(worker.first_name, "Maya")
        self.assertTrue(worker.user.is_active)

    def test_worker_create_preserves_list_return_state(self):
        list_path = (
            f"{reverse('worker_list')}?q=Maya&status=active&employment_type=employee"
            "&sort=name&direction=asc&page=2"
        )
        self.login_admin()

        list_response = self.client.get(list_path)
        create_response = self.client.get(reverse("worker_create"), {"next": list_path})
        post_response = self.client.post(
            reverse("worker_create"),
            self.worker_payload(next=list_path),
        )

        self.assertContains(list_response, f"{reverse('worker_create')}?next=")
        self.assertContains(create_response, f'href="{list_path.replace("&", "&amp;")}"')
        self.assertContains(create_response, f'name="next" value="{list_path.replace("&", "&amp;")}"')
        self.assertRedirects(post_response, list_path)

    def test_password_confirmation_must_match(self):
        self.login_admin()

        response = self.client.post(
            reverse("worker_create"),
            self.worker_payload(password2="DifferentPass123!"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match")
        self.assertFalse(get_user_model().objects.filter(username="newworker").exists())

    def test_username_and_email_must_be_unique(self):
        get_user_model().objects.create_user(
            username="newworker",
            email="newworker@example.com",
            password="test-password-123",
        )
        self.login_admin()

        response = self.client.post(reverse("worker_create"), self.worker_payload())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username already exists")
        self.assertContains(response, "Email already exists")
        self.assertEqual(SupportWorker.objects.count(), 0)

    def test_admin_can_search_and_filter_worker_list(self):
        active_user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        inactive_user = get_user_model().objects.create_user(
            username="liam",
            email="liam@example.com",
            password="test-password-123",
        )
        SupportWorker.objects.create(
            user=active_user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            phone="0400000000",
            employment_type=SupportWorker.EmploymentType.EMPLOYEE,
            status=SupportWorker.Status.ACTIVE,
        )
        SupportWorker.objects.create(
            user=inactive_user,
            first_name="Liam",
            last_name="Brown",
            email="liam@example.com",
            phone="0411111111",
            employment_type=SupportWorker.EmploymentType.SUBCONTRACTOR,
            status=SupportWorker.Status.INACTIVE,
        )
        self.login_admin()

        response = self.client.get(
            reverse("worker_list"),
            {"q": "Maya", "status": "active", "employment_type": "employee"},
        )

        self.assertContains(response, "Maya Singh")
        self.assertNotContains(response, "Liam Brown")

    def test_worker_list_renders_status_specific_class(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_list"))

        self.assertContains(response, 'class="status-pill status-active"')

    def test_worker_list_defaults_to_active_and_offers_archive_views(self):
        active_user = get_user_model().objects.create_user(
            username="activeworker",
            email="activeworker@example.com",
            password="test-password-123",
        )
        inactive_user = get_user_model().objects.create_user(
            username="inactiveworker",
            email="inactiveworker@example.com",
            password="test-password-123",
        )
        SupportWorker.objects.create(
            user=active_user,
            first_name="Active",
            last_name="Worker",
            email="activeworker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        SupportWorker.objects.create(
            user=inactive_user,
            first_name="Inactive",
            last_name="Worker",
            email="inactiveworker@example.com",
            status=SupportWorker.Status.INACTIVE,
        )
        self.login_admin()

        default_response = self.client.get(reverse("worker_list"))
        archived_response = self.client.get(reverse("worker_list"), {"scope": "archived"})
        all_response = self.client.get(reverse("worker_list"), {"scope": "all"})

        self.assertContains(default_response, "<td>Active Worker</td>", html=True)
        self.assertNotContains(default_response, "<td>Inactive Worker</td>", html=True)
        self.assertContains(default_response, "Active Workers")
        self.assertContains(default_response, "Archived Workers")
        self.assertContains(archived_response, "<td>Inactive Worker</td>", html=True)
        self.assertNotContains(archived_response, "<td>Active Worker</td>", html=True)
        self.assertContains(all_response, "<td>Active Worker</td>", html=True)
        self.assertContains(all_response, "<td>Inactive Worker</td>", html=True)

    def test_worker_list_is_paginated_and_preserves_filters(self):
        for index in range(25):
            user = get_user_model().objects.create_user(
                username=f"activeworker{index:02d}",
                email=f"activeworker{index:02d}@example.com",
                password="test-password-123",
            )
            SupportWorker.objects.create(
                user=user,
                first_name=f"Active{index:02d}",
                last_name="Worker",
                email=f"activeworker{index:02d}@example.com",
                employment_type=SupportWorker.EmploymentType.EMPLOYEE,
                status=SupportWorker.Status.ACTIVE,
            )
        inactive_user = get_user_model().objects.create_user(
            username="inactiveworker",
            email="inactiveworker@example.com",
            password="test-password-123",
        )
        SupportWorker.objects.create(
            user=inactive_user,
            first_name="Inactive",
            last_name="Worker",
            email="inactiveworker@example.com",
            employment_type=SupportWorker.EmploymentType.SUBCONTRACTOR,
            status=SupportWorker.Status.INACTIVE,
        )
        self.login_admin()

        response = self.client.get(
            reverse("worker_list"),
            {
                "q": "Active",
                "status": SupportWorker.Status.ACTIVE,
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
            },
        )

        self.assertEqual(response.context["workers"].paginator.count, 25)
        self.assertEqual(len(response.context["workers"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(
            response,
            "?q=Active&amp;status=active&amp;employment_type=employee&amp;page=2",
        )
        self.assertNotContains(response, "Inactive Worker")

    def test_worker_list_can_sort_by_status_and_preserve_filters(self):
        active_user = get_user_model().objects.create_user(
            username="activeworker",
            email="activeworker@example.com",
            password="test-password-123",
        )
        inactive_user = get_user_model().objects.create_user(
            username="inactiveworker",
            email="inactiveworker@example.com",
            password="test-password-123",
        )
        SupportWorker.objects.create(
            user=active_user,
            first_name="Active",
            last_name="Worker",
            email="activeworker@example.com",
            employment_type=SupportWorker.EmploymentType.EMPLOYEE,
            status=SupportWorker.Status.ACTIVE,
        )
        SupportWorker.objects.create(
            user=inactive_user,
            first_name="Inactive",
            last_name="Worker",
            email="inactiveworker@example.com",
            employment_type=SupportWorker.EmploymentType.EMPLOYEE,
            status=SupportWorker.Status.INACTIVE,
        )
        self.login_admin()

        response = self.client.get(
            reverse("worker_list"),
            {
                "scope": "all",
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                "sort": "status",
                "direction": "desc",
            },
        )
        content = response.content.decode()

        self.assertLess(
            content.index("<td>Inactive Worker</td>"),
            content.index("<td>Active Worker</td>"),
        )
        self.assertContains(
            response,
            "?scope=all&amp;employment_type=employee&amp;sort=status&amp;direction=asc",
        )

    def test_worker_list_distinguishes_empty_filter_results(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_list"), {"q": "Missing"})

        self.assertContains(response, "No support workers match the current filters.")
        self.assertContains(response, "Clear filters")
        self.assertNotContains(response, "Add a worker so they can be assigned shifts")

    def test_admin_can_view_worker_detail(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
            police_check_status=SupportWorker.ComplianceStatus.CURRENT,
            police_check_expiry=date(2027, 2, 1),
        )
        self.login_admin()

        response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertContains(response, "Maya Singh")
        self.assertContains(response, "Police check")
        self.assertContains(response, "Current")

    def test_worker_detail_uses_polished_related_records(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
        )
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertContains(response, 'class="card related-records-card"')
        self.assertContains(response, 'class="related-records-table"')
        self.assertContains(response, 'class="status-pill status-active"')
        self.assertContains(response, 'class="detail-empty"')

    def test_worker_detail_back_link_preserves_list_state(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            employment_type=SupportWorker.EmploymentType.EMPLOYEE,
            status=SupportWorker.Status.ACTIVE,
        )
        list_path = (
            f"{reverse('worker_list')}?q=Maya&status=active&employment_type=employee"
            "&sort=name&direction=asc&page=2"
        )
        self.login_admin()

        list_response = self.client.get(list_path)
        detail_response = self.client.get(reverse("worker_detail", args=[worker.id]), {"next": list_path})

        self.assertContains(
            list_response,
            f"{reverse('worker_detail', args=[worker.id])}?next=",
        )
        self.assertContains(detail_response, f'href="{list_path.replace("&", "&amp;")}"')

    def test_worker_detail_shows_readiness_and_next_steps(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
            police_check_status=SupportWorker.ComplianceStatus.CURRENT,
            wwcc_status=SupportWorker.ComplianceStatus.PENDING,
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
        )
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
        )
        self.login_admin()

        response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertContains(response, "Readiness")
        self.assertContains(response, "Worker active")
        self.assertContains(response, "Police check current")
        self.assertContains(response, "Needs WWCC / Blue Card current")
        self.assertContains(response, "Has active participant assignment")
        self.assertContains(response, "Next steps")
        self.assertContains(response, "Upload Document")
        self.assertContains(response, "Create Shift")

    def test_worker_detail_shows_compliance_document_upload_statuses(self):
        user = get_user_model().objects.create_user(
            username="maya-docs",
            email="maya.docs@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya.docs@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        other_user = get_user_model().objects.create_user(
            username="other-docs",
            email="other.docs@example.com",
            password="test-password-123",
        )
        other_worker = SupportWorker.objects.create(
            user=other_user,
            first_name="Oscar",
            last_name="Other",
            email="other.docs@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        Document.objects.create(
            title="Police Check",
            category=Document.Category.COMPLIANCE,
            worker=worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.PENDING_REVIEW,
            file="documents/police-check.pdf",
            uploaded_by=user,
        )
        Document.objects.create(
            title="First Aid Certificate",
            category=Document.Category.COMPLIANCE,
            worker=worker,
            required_document_type=Document.RequiredDocumentType.FIRST_AID,
            review_status=Document.ReviewStatus.APPROVED,
            expiry_date=date(2027, 6, 1),
            file="documents/first-aid.pdf",
            uploaded_by=user,
        )
        Document.objects.create(
            title="Other worker Police Check",
            category=Document.Category.COMPLIANCE,
            worker=other_worker,
            required_document_type=Document.RequiredDocumentType.POLICE_CHECK,
            review_status=Document.ReviewStatus.APPROVED,
            file="documents/other-police-check.pdf",
            uploaded_by=other_user,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertContains(response, "Compliance Documents")
        self.assertContains(response, "Police Check")
        self.assertContains(response, "Pending review")
        self.assertContains(response, "First Aid Certificate")
        self.assertContains(response, "Approved")
        self.assertContains(response, "Expires 01/06/2027")
        self.assertContains(response, "Not uploaded")
        self.assertContains(response, "Other documents")
        self.assertNotContains(response, "Other worker Police Check")

    def test_worker_detail_shows_active_participants_and_recent_service_logs(self):
        user = get_user_model().objects.create_user(
            username="maya-activity",
            email="maya.activity@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya.activity@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        other_user = get_user_model().objects.create_user(
            username="other-activity",
            email="other.activity@example.com",
            password="test-password-123",
        )
        other_worker = SupportWorker.objects.create(
            user=other_user,
            first_name="Oscar",
            last_name="Other",
            email="other.activity@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
        )
        other_participant = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            status=Participant.Status.ACTIVE,
        )
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        shift = Shift.objects.create(
            participant=participant,
            worker=worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            break_minutes=0,
            planned_hours=Decimal("2.00"),
            support_item=support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.worker_user,
        )
        other_shift = Shift.objects.create(
            participant=other_participant,
            worker=other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(11, 0),
            break_minutes=0,
            planned_hours=Decimal("2.00"),
            support_item=support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.worker_user,
        )
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            break_minutes=0,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("0.00"),
            case_notes="Worker detail log.",
            status=ServiceLog.Status.SUBMITTED,
        )
        ServiceLog.objects.create_from_shift(
            shift=other_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            break_minutes=0,
            actual_hours=Decimal("2.00"),
            kilometres=Decimal("0.00"),
            case_notes="Other worker log.",
            status=ServiceLog.Status.APPROVED,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertContains(response, "Assigned Participants")
        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, reverse("participant_detail", args=[participant.id]))
        self.assertContains(response, "Recent Service Logs")
        self.assertContains(response, "01/06/2026")
        self.assertContains(response, "2.00")
        self.assertContains(response, "Submitted")
        self.assertContains(response, reverse("service_log_detail", args=[service_log.id]))
        self.assertNotContains(response, "Ben Taylor")
        self.assertNotContains(response, "Other worker log")

    def test_worker_list_omits_compliance_summary_but_detail_retains_it(self):
        user = get_user_model().objects.create_user(
            username="maya-list",
            email="maya.list@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya.list@example.com",
            status=SupportWorker.Status.ACTIVE,
            police_check_status=SupportWorker.ComplianceStatus.CURRENT,
            wwcc_status=SupportWorker.ComplianceStatus.PENDING,
        )
        self.login_admin()

        list_response = self.client.get(reverse("worker_list"))
        detail_response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertNotContains(list_response, "<th>Compliance</th>", html=True)
        self.assertNotContains(list_response, "Police: Current")
        self.assertNotContains(list_response, "WWCC: Pending")
        self.assertContains(detail_response, "<h2>Compliance Documents</h2>", html=True)
        self.assertContains(detail_response, "Police check")
        self.assertContains(detail_response, "WWCC / Blue Card")

    def test_worker_edit_distinguishes_login_access_from_worker_status(self):
        user = get_user_model().objects.create_user(
            username="maya-login",
            email="maya.login@example.com",
            password="test-password-123",
            is_active=False,
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya.login@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.login_admin()

        edit_response = self.client.get(reverse("worker_edit", args=[worker.id]))
        detail_response = self.client.get(reverse("worker_detail", args=[worker.id]))

        self.assertContains(edit_response, "Login enabled")
        self.assertContains(
            edit_response,
            "Turn this off to stop this worker signing in. Their worker record and history are kept.",
        )
        self.assertContains(edit_response, "Account Access")
        content = edit_response.content.decode()
        self.assertLess(content.index("Internal Notes"), content.index("Account Access"))
        self.assertLess(content.index("Internal Notes"), content.index("Login enabled"))
        self.assertContains(detail_response, "<dt>Login enabled</dt>", html=True)
        self.assertContains(detail_response, 'class="status-pill status-inactive"')
        self.assertContains(detail_response, ">No</span>")
        self.assertContains(detail_response, "<dt>Worker status</dt>", html=True)
        self.assertContains(detail_response, 'class="status-pill status-active"')
        self.assertContains(detail_response, ">Active</span>")

    def test_worker_edit_explains_archive_without_delete_action(self):
        user = get_user_model().objects.create_user(
            username="maya-archive",
            email="maya.archive@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya.archive@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.get(reverse("worker_edit", args=[worker.id]))

        self.assertContains(response, 'class="card form-section worker-access-section"')
        self.assertContains(response, "Worker Access and Archive")
        self.assertContains(response, "Login access")
        self.assertContains(response, "Archive status")
        self.assertContains(response, "Set Worker status to Inactive to archive this worker.")
        self.assertContains(
            response,
            "Archived workers are removed from new scheduling and assignment choices. Existing shifts, service logs, invoices, and documents are kept.",
        )
        self.assertNotContains(response, "Delete Worker")

    def test_worker_create_shows_access_without_archive_panel(self):
        self.login_admin()

        response = self.client.get(reverse("worker_create"))

        self.assertContains(response, 'class="worker-access-panel worker-access-panel-neutral"')
        self.assertContains(response, 'class="field worker-access-toggle"')
        self.assertContains(response, "Account Access")
        self.assertContains(response, "Login enabled")
        self.assertNotContains(response, "Archive status")
        self.assertNotContains(response, "worker-archive-panel")

    def test_admin_can_edit_worker(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(
            reverse("worker_edit", args=[worker.id]),
            {
                "email": "maya.updated@example.com",
                "account_active": "on",
                "first_name": "Maya",
                "last_name": "Singh-Patel",
                "phone": "0499999999",
                "address": "Updated address",
                "employment_type": SupportWorker.EmploymentType.SUBCONTRACTOR,
                "abn": "12345678901",
                "start_date": "2026-02-01",
                "status": SupportWorker.Status.ACTIVE,
                "police_check_status": SupportWorker.ComplianceStatus.PENDING,
                "police_check_expiry": "",
                "wwcc_status": SupportWorker.ComplianceStatus.NOT_PROVIDED,
                "wwcc_expiry": "",
                "notes": "Updated note.",
            },
        )

        worker.refresh_from_db()
        worker.user.refresh_from_db()
        self.assertRedirects(response, reverse("worker_detail", args=[worker.id]))
        self.assertEqual(worker.last_name, "Singh-Patel")
        self.assertEqual(worker.email, "maya.updated@example.com")
        self.assertEqual(worker.user.email, "maya.updated@example.com")

    def test_worker_edit_preserves_list_return_state(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            employment_type=SupportWorker.EmploymentType.EMPLOYEE,
            status=SupportWorker.Status.ACTIVE,
        )
        list_path = (
            f"{reverse('worker_list')}?q=Maya&status=active&employment_type=employee"
            "&sort=name&direction=asc&page=2"
        )
        self.login_admin()

        list_response = self.client.get(list_path)
        edit_response = self.client.get(reverse("worker_edit", args=[worker.id]), {"next": list_path})
        post_response = self.client.post(
            reverse("worker_edit", args=[worker.id]),
            {
                "email": "maya.updated@example.com",
                "account_active": "on",
                "first_name": "Maya",
                "last_name": "Singh-Patel",
                "phone": "0499999999",
                "address": "Updated address",
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                "abn": "",
                "start_date": "2026-02-01",
                "status": SupportWorker.Status.ACTIVE,
                "police_check_status": SupportWorker.ComplianceStatus.CURRENT,
                "police_check_expiry": "",
                "wwcc_status": SupportWorker.ComplianceStatus.CURRENT,
                "wwcc_expiry": "",
                "notes": "Updated note.",
                "next": list_path,
            },
        )

        self.assertContains(
            list_response,
            f"{reverse('worker_edit', args=[worker.id])}?next=",
        )
        self.assertContains(edit_response, f'href="{list_path.replace("&", "&amp;")}"')
        self.assertContains(edit_response, f'name="next" value="{list_path.replace("&", "&amp;")}"')
        self.assertRedirects(post_response, list_path)

    def test_worker_can_view_own_profile(self):
        SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_profile"))

        self.assertContains(response, "Wendy Worker")
        self.assertContains(response, "worker@example.com")

    def test_worker_profile_wraps_assignment_table_for_small_screens(self):
        SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_profile"))

        self.assertContains(response, 'class="worker-table-scroll"')

    def test_worker_without_profile_sees_profile_setup_message(self):
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_profile"))

        self.assertContains(response, "Your worker profile has not been set up yet.")

    def test_worker_and_accountant_cannot_access_admin_worker_pages(self):
        user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Maya",
            last_name="Singh",
            status=SupportWorker.Status.ACTIVE,
        )
        protected_urls = [
            reverse("worker_list"),
            reverse("worker_create"),
            reverse("worker_detail", args=[worker.id]),
            reverse("worker_edit", args=[worker.id]),
        ]

        for username in ["worker", "accountant"]:
            self.client.login(username=username, password="test-password-123")
            for url in protected_urls:
                with self.subTest(username=username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 403)
            self.client.logout()
