from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant, ParticipantWorkerAssignment

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
                "employment_type": SupportWorker.EmploymentType.EMPLOYEE,
                "sort": "status",
                "direction": "desc",
            },
        )
        content = response.content.decode()

        self.assertLess(content.index("Inactive Worker"), content.index("Active Worker"))
        self.assertContains(
            response,
            "?employment_type=employee&amp;sort=status&amp;direction=asc",
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
