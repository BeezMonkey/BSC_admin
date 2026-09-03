from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from workers.models import SupportWorker

from .models import Participant, ParticipantWorkerAssignment


class ParticipantManagementTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def setUp(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def create_worker(self, username="wendy", first_name="Wendy", last_name="Worker"):
        user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="test-password-123",
        )
        return SupportWorker.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@example.com",
            status=SupportWorker.Status.ACTIVE,
        )

    def participant_payload(self, **overrides):
        data = {
            "first_name": "Ava",
            "last_name": "Nguyen",
            "preferred_name": "Ava",
            "date_of_birth": "1990-01-15",
            "ndis_number": "123456789",
            "status": Participant.Status.ACTIVE,
            "phone": "0400000000",
            "email": "ava@example.com",
            "address_line_1": "10 Creek Street",
            "address_line_2": "",
            "suburb": "Brisbane",
            "state": "QLD",
            "postcode": "4000",
            "emergency_contact_name": "Mia Nguyen",
            "emergency_contact_relationship": "Sister",
            "emergency_contact_phone": "0411111111",
            "emergency_contact_email": "mia@example.com",
            "plan_start_date": "2026-01-01",
            "plan_end_date": "2026-12-31",
            "management_type": Participant.ManagementType.PLAN_MANAGED,
            "plan_manager_name": "Plan Manager Co",
            "plan_manager_email": "pm@example.com",
            "plan_manager_phone": "0730000000",
            "support_coordinator_name": "Sam Lee",
            "support_coordinator_email": "sam@example.com",
            "support_coordinator_phone": "0731111111",
            "worker_visible_notes": "Use side entrance.",
            "address_access_instructions": "Gate code 1234.",
            "risk_safety_notes": "Dog in backyard.",
            "internal_notes": "Admin-only note.",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_participant(self):
        self.login_admin()

        response = self.client.post(reverse("participant_create"), self.participant_payload())

        participant = Participant.objects.get(ndis_number="123456789")
        self.assertRedirects(response, reverse("participant_detail", args=[participant.id]))
        self.assertEqual(participant.first_name, "Ava")
        self.assertEqual(participant.management_type, Participant.ManagementType.PLAN_MANAGED)

    def test_participant_create_success_message_is_rendered(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(),
            follow=True,
        )

        self.assertContains(response, 'class="message success"')
        self.assertContains(response, "Participant created.")

    def test_participant_create_preserves_list_return_state(self):
        list_path = f"{reverse('participant_list')}?q=Ava&status=active&sort=name&direction=asc&page=2"
        self.login_admin()

        list_response = self.client.get(list_path)
        create_response = self.client.get(reverse("participant_create"), {"next": list_path})
        post_response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(next=list_path),
        )

        self.assertContains(list_response, f"{reverse('participant_create')}?next=")
        self.assertContains(create_response, f'href="{list_path.replace("&", "&amp;")}"')
        self.assertContains(create_response, f'name="next" value="{list_path.replace("&", "&amp;")}"')
        self.assertRedirects(post_response, list_path)

    def test_first_and_last_name_are_required(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(first_name="", last_name=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Participant.objects.count(), 0)

    def test_participant_create_form_keeps_section_structure(self):
        self.login_admin()

        response = self.client.get(reverse("participant_create"))

        self.assertContains(response, 'class="card form-section"')
        self.assertContains(response, "Basic Information")
        self.assertContains(response, "NDIS Plan")

    def test_participant_management_type_uses_clear_empty_option(self):
        self.login_admin()

        response = self.client.get(reverse("participant_create"))

        self.assertContains(response, "Select management type")
        self.assertNotContains(response, "---------")

    def test_ndis_number_must_be_unique_when_supplied(self):
        Participant.objects.create(
            first_name="Existing",
            last_name="Participant",
            ndis_number="123456789",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(reverse("participant_create"), self.participant_payload())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participant with this NDIS number already exists")
        self.assertEqual(Participant.objects.count(), 1)

    def test_plan_end_date_cannot_be_before_start_date(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(
                plan_start_date="2026-12-31",
                plan_end_date="2026-01-01",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plan end date cannot be earlier than plan start date")
        self.assertEqual(Participant.objects.count(), 0)

    def test_postcode_must_be_four_digits_when_supplied(self):
        self.login_admin()

        response = self.client.post(
            reverse("participant_create"),
            self.participant_payload(postcode="400"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a 4-digit Australian postcode")
        self.assertEqual(Participant.objects.count(), 0)

    def test_admin_can_search_and_filter_participant_list(self):
        Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            preferred_name="Ava",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            preferred_name="Ben",
            ndis_number="222222222",
            status=Participant.Status.ARCHIVED,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"), {"q": "Ava", "status": "active"})

        self.assertContains(response, "Ava Nguyen")
        self.assertNotContains(response, "Ben Taylor")

    def test_participant_initials_use_first_and_last_name(self):
        participant = Participant(first_name="Ava", last_name="Nguyen")

        self.assertEqual(participant.initials, "AN")

    def test_participant_list_search_matches_phone_and_email(self):
        Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            phone="0400001111",
            email="ava@example.com",
            status=Participant.Status.ACTIVE,
        )
        Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            ndis_number="222222222",
            phone="0400002222",
            email="ben@example.com",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        phone_response = self.client.get(reverse("participant_list"), {"q": "0400001111"})
        email_response = self.client.get(reverse("participant_list"), {"q": "ava@example.com"})

        self.assertContains(phone_response, "Ava Nguyen")
        self.assertNotContains(phone_response, "Ben Taylor")
        self.assertContains(email_response, "Ava Nguyen")
        self.assertNotContains(email_response, "Ben Taylor")

    def test_participant_list_shows_workbench_overview_cards(self):
        active_participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        Participant.objects.create(
            first_name="Inactive",
            last_name="Participant",
            ndis_number="222222222",
            status=Participant.Status.INACTIVE,
        )
        Participant.objects.create(
            first_name="Archived",
            last_name="Participant",
            ndis_number="333333333",
            status=Participant.Status.ARCHIVED,
        )
        worker = self.create_worker()
        ParticipantWorkerAssignment.objects.create(
            participant=active_participant,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"))

        self.assertContains(response, 'class="participant-workbench"')
        self.assertContains(response, "Participant workbench")
        self.assertContains(response, "All participants")
        self.assertContains(response, "3 records")
        self.assertContains(response, "Active")
        self.assertContains(response, "1 active")
        self.assertContains(response, "Needs assignment")
        self.assertContains(response, "0 without workers")
        self.assertContains(response, "Inactive")
        self.assertContains(response, "1 inactive")
        self.assertContains(response, "Archived")
        self.assertContains(response, "1 archived")

    def test_participant_list_filters_by_worker_assignment(self):
        assigned = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        unassigned = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            ndis_number="222222222",
            status=Participant.Status.ACTIVE,
        )
        worker = self.create_worker()
        ParticipantWorkerAssignment.objects.create(
            participant=assigned,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        self.login_admin()

        assigned_response = self.client.get(reverse("participant_list"), {"assignment": "assigned"})
        unassigned_response = self.client.get(reverse("participant_list"), {"assignment": "unassigned"})

        self.assertContains(assigned_response, assigned.display_name)
        self.assertNotContains(assigned_response, unassigned.display_name)
        self.assertContains(unassigned_response, unassigned.display_name)
        self.assertNotContains(unassigned_response, assigned.display_name)

    def test_participant_list_uses_avatar_contact_and_assignment_cells(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            phone="0400000000",
            email="ava@example.com",
            status=Participant.Status.ACTIVE,
        )
        worker = self.create_worker(first_name="Maya", last_name="Singh")
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"))

        self.assertContains(response, 'class="participant-table"')
        self.assertContains(response, 'class="participant-avatar"')
        self.assertContains(response, "AN")
        self.assertContains(response, 'class="participant-contact-stack"')
        self.assertContains(response, "0400000000")
        self.assertContains(response, "ava@example.com")
        self.assertContains(response, 'class="participant-worker-avatars"')
        self.assertContains(response, "MS")
        self.assertContains(response, "1 active worker")

    def test_participant_worker_initials_expose_full_name_tooltips(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        worker = self.create_worker(first_name="Cristian", last_name="Caceres")
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"))

        self.assertContains(response, 'class="participant-worker-avatar"')
        self.assertContains(response, 'data-worker-name="Cristian Caceres"')
        self.assertContains(response, 'aria-label="Cristian Caceres"')
        self.assertContains(response, 'tabindex="0"')

    def test_participant_list_renders_status_specific_class(self):
        Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"))

        self.assertContains(response, 'class="status-pill status-active"')

    def test_participant_list_displays_australian_plan_period_dates(self):
        Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
            plan_start_date=date(2026, 1, 1),
            plan_end_date=date(2026, 12, 31),
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"))

        self.assertContains(response, "01/01/2026 to 31/12/2026")
        self.assertNotContains(response, "Jan. 1, 2026 to Dec. 31, 2026")

    def test_participant_list_is_paginated_and_preserves_filters(self):
        for index in range(25):
            Participant.objects.create(
                first_name=f"Active{index:02d}",
                last_name="Participant",
                ndis_number=f"5000000{index:02d}",
                status=Participant.Status.ACTIVE,
            )
        Participant.objects.create(
            first_name="Archived",
            last_name="Participant",
            ndis_number="599999999",
            status=Participant.Status.ARCHIVED,
        )
        self.login_admin()

        response = self.client.get(
            reverse("participant_list"),
            {"q": "Active", "status": Participant.Status.ACTIVE},
        )

        self.assertEqual(response.context["participants"].paginator.count, 25)
        self.assertEqual(len(response.context["participants"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(response, 'class="pagination"')
        self.assertContains(response, "?q=Active&amp;status=active&amp;page=2")
        self.assertNotContains(response, "Archived Participant")

    def test_participant_list_can_sort_by_name_and_preserve_filters(self):
        Participant.objects.create(
            first_name="Zoe",
            last_name="Zephyr",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        Participant.objects.create(
            first_name="Ava",
            last_name="Anderson",
            ndis_number="222222222",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.get(
            reverse("participant_list"),
            {"status": Participant.Status.ACTIVE, "sort": "name", "direction": "asc"},
        )
        content = response.content.decode()

        self.assertLess(content.index("Ava Anderson"), content.index("Zoe Zephyr"))
        self.assertContains(response, "?status=active&amp;sort=name&amp;direction=desc")

    def test_participant_list_distinguishes_empty_filter_results(self):
        Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_list"), {"q": "Missing"})

        self.assertContains(response, "No participants match the current filters.")
        self.assertContains(response, "Clear filters")
        self.assertNotContains(response, "Add a participant to start building records")

    def test_participant_empty_state_wraps_action_links(self):
        self.login_admin()

        response = self.client.get(reverse("participant_list"))

        self.assertContains(response, 'class="empty-state"')
        self.assertContains(response, 'class="empty-state-actions"')
        self.assertContains(response, "Add Participant")

    def test_admin_can_view_participant_detail(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            preferred_name="Ava",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
            plan_start_date=date(2026, 1, 1),
            plan_end_date=date(2026, 12, 31),
        )
        self.login_admin()

        response = self.client.get(reverse("participant_detail", args=[participant.id]))

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, "111111111")
        self.assertContains(response, 'class="participant-detail-page"')
        self.assertContains(response, "Roster")
        self.assertContains(response, "Service Logs")

    def test_participant_detail_uses_polished_related_records(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        worker_user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Maya",
            last_name="Singh",
            email="maya@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_detail", args=[participant.id]))

        self.assertContains(response, 'class="card related-records-card"')
        self.assertContains(response, 'class="related-records-table"')
        self.assertContains(response, 'class="status-pill status-active"')
        self.assertContains(response, 'class="detail-empty"')

    def test_participant_detail_back_link_preserves_list_state(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        list_path = f"{reverse('participant_list')}?q=Ava&status=active&sort=name&direction=asc&page=2"
        self.login_admin()

        list_response = self.client.get(list_path)
        detail_response = self.client.get(
            reverse("participant_detail", args=[participant.id]),
            {"next": list_path},
        )

        self.assertContains(
            list_response,
            f"{reverse('participant_detail', args=[participant.id])}?next=",
        )
        self.assertContains(detail_response, f'href="{list_path.replace("&", "&amp;")}"')

    def test_participant_detail_shows_readiness_and_next_steps(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            plan_start_date=date(2026, 1, 1),
            plan_end_date=date(2026, 12, 31),
        )
        user = get_user_model().objects.create_user(
            username="assignedworker",
            email="assignedworker@example.com",
            password="test-password-123",
        )
        worker = SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="assignedworker@example.com",
        )
        ParticipantWorkerAssignment.objects.create(
            participant=participant,
            worker=worker,
            start_date=date(2026, 1, 1),
        )
        self.login_admin()

        response = self.client.get(reverse("participant_detail", args=[participant.id]))

        self.assertContains(response, "Readiness")
        self.assertContains(response, "Needs NDIS number")
        self.assertContains(response, "Active worker assigned")
        self.assertContains(response, "Next steps")
        self.assertContains(response, "Upload Document")
        self.assertContains(response, "Create Shift")

    def test_participant_assignment_only_offers_active_workers(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
        )
        active_user = get_user_model().objects.create_user(
            username="activeworker",
            email="active.worker@example.com",
            password="test-password-123",
        )
        archived_user = get_user_model().objects.create_user(
            username="archivedworker",
            email="archived.worker@example.com",
            password="test-password-123",
        )
        active_worker = SupportWorker.objects.create(
            user=active_user,
            first_name="Active",
            last_name="Worker",
            email="active.worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        archived_worker = SupportWorker.objects.create(
            user=archived_user,
            first_name="Archived",
            last_name="Worker",
            email="archived.worker@example.com",
            status=SupportWorker.Status.INACTIVE,
        )
        self.login_admin()

        response = self.client.get(reverse("participant_assign_worker", args=[participant.id]))
        post_response = self.client.post(
            reverse("participant_assign_worker", args=[participant.id]),
            {
                "worker": archived_worker.id,
                "start_date": "2026-06-01",
                "end_date": "",
                "is_active": "on",
                "notes": "",
            },
        )

        self.assertContains(response, active_worker.display_name)
        self.assertNotContains(response, archived_worker.display_name)
        self.assertEqual(post_response.status_code, 200)
        self.assertFormError(
            post_response.context["form"],
            "worker",
            "Select a valid choice. That choice is not one of the available choices.",
        )
        self.assertFalse(ParticipantWorkerAssignment.objects.filter(worker=archived_worker).exists())

    def test_admin_can_edit_participant(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(
            reverse("participant_edit", args=[participant.id]),
            self.participant_payload(
                first_name="Avery",
                ndis_number="111111111",
                email="avery@example.com",
            ),
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("participant_detail", args=[participant.id]))
        self.assertEqual(participant.first_name, "Avery")
        self.assertEqual(participant.email, "avery@example.com")

    def test_participant_edit_preserves_list_return_state(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        list_path = f"{reverse('participant_list')}?q=Ava&status=active&sort=name&direction=asc&page=2"
        self.login_admin()

        list_response = self.client.get(list_path)
        edit_response = self.client.get(
            reverse("participant_edit", args=[participant.id]),
            {"next": list_path},
        )
        post_response = self.client.post(
            reverse("participant_edit", args=[participant.id]),
            self.participant_payload(
                first_name="Avery",
                ndis_number="111111111",
                email="avery@example.com",
                next=list_path,
            ),
        )

        self.assertContains(
            list_response,
            f"{reverse('participant_edit', args=[participant.id])}?next=",
        )
        self.assertContains(edit_response, f'href="{list_path.replace("&", "&amp;")}"')
        self.assertContains(edit_response, f'name="next" value="{list_path.replace("&", "&amp;")}"')
        self.assertRedirects(post_response, list_path)

    def test_admin_can_archive_participant_without_deleting_it(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            ndis_number="111111111",
            status=Participant.Status.ACTIVE,
        )
        self.login_admin()

        response = self.client.post(reverse("participant_archive", args=[participant.id]))

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("participant_detail", args=[participant.id]))
        self.assertEqual(participant.status, Participant.Status.ARCHIVED)
        self.assertEqual(Participant.objects.count(), 1)

    def test_worker_and_accountant_cannot_access_participant_pages(self):
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
        )
        protected_urls = [
            reverse("participant_list"),
            reverse("participant_create"),
            reverse("participant_detail", args=[participant.id]),
            reverse("participant_edit", args=[participant.id]),
            reverse("participant_archive", args=[participant.id]),
        ]

        for username in ["worker", "accountant"]:
            self.client.login(username=username, password="test-password-123")
            for url in protected_urls:
                with self.subTest(username=username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 403)
            self.client.logout()
