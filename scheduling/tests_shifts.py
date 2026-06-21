from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from workers.models import SupportWorker


class ShiftSchedulingTests(TestCase):
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
        self.worker_user = self.create_user_with_role("worker", UserProfile.Role.SUPPORT_WORKER)
        self.other_worker_user = self.create_user_with_role(
            "otherworker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.create_user_with_role("accountant", UserProfile.Role.ACCOUNTANT)
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

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def shift_payload(self, **overrides):
        data = {
            "participant": self.participant.id,
            "worker": self.worker.id,
            "service_date": "2026-06-01",
            "start_time": "09:00",
            "end_time": "11:30",
            "break_minutes": "30",
            "support_item": self.support_item.id,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "location": "Participant home",
            "address": "10 Creek Street, Brisbane QLD 4000",
            "instructions": "Use side entrance.",
            "admin_notes": "Admin note.",
            "status": Shift.Status.DRAFT,
        }
        data.update(overrides)
        return data

    def recurring_shift_payload(self, **overrides):
        data = {
            "participant": self.participant.id,
            "worker": self.worker.id,
            "frequency": "weekly",
            "start_date": "2026-06-01",
            "end_date": "2026-06-15",
            "start_time": "09:00",
            "end_time": "11:00",
            "break_minutes": "0",
            "support_item": self.support_item.id,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "location": "Participant home",
            "address": "10 Creek Street, Brisbane QLD 4000",
            "instructions": "Use side entrance.",
            "admin_notes": "Recurring note.",
        }
        data.update(overrides)
        return data

    def create_shift(self, **overrides):
        data = {
            "participant": self.participant,
            "worker": self.worker,
            "service_date": date(2026, 6, 1),
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": self.support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "status": Shift.Status.PUBLISHED,
            "created_by": self.admin_user,
        }
        data.update(overrides)
        return Shift.objects.create(**data)

    def test_admin_can_create_draft_shift_and_planned_hours_are_calculated(self):
        self.login_admin()

        response = self.client.post(reverse("shift_create"), self.shift_payload())

        shift = Shift.objects.get()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.DRAFT)
        self.assertEqual(shift.planned_hours, Decimal("2.00"))
        self.assertEqual(shift.created_by, self.admin_user)

    def test_shift_create_preserves_roster_return_state(self):
        list_path = (
            f"{reverse('roster_list')}?worker=Wendy&status=published"
            "&sort=date&direction=asc&page=2"
        )
        self.login_admin()

        list_response = self.client.get(list_path)
        create_response = self.client.get(reverse("shift_create"), {"next": list_path})
        post_response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(status=Shift.Status.PUBLISHED, next=list_path),
        )

        self.assertContains(list_response, f"{reverse('shift_create')}?next=")
        self.assertContains(create_response, f'href="{list_path.replace("&", "&amp;")}"')
        self.assertContains(create_response, f'name="next" value="{list_path.replace("&", "&amp;")}"')
        self.assertRedirects(post_response, list_path)

    def test_shift_create_plain_get_keeps_full_page_fallback(self):
        self.login_admin()

        response = self.client.get(reverse("shift_create"), {"service_date": "2026-06-10"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="app-shell"')
        self.assertContains(response, 'class="record-form"')
        self.assertContains(response, "New Shift")
        self.assertNotContains(response, 'class="shift-modal-dialog"')

    def test_shift_create_modal_get_returns_partial_form(self):
        self.login_admin()

        response = self.client.get(
            reverse("shift_create"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "service_date": "2026-06-10",
                "modal": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="shift-modal-dialog"')
        self.assertContains(response, "New Shift on 10/06/2026")
        self.assertContains(response, 'name="modal" value="1"')
        self.assertContains(response, 'value="2026-06-10"')
        self.assertNotContains(response, 'class="app-shell"')

    def test_shift_create_modal_uses_friendly_empty_options_and_au_date_hint(self):
        self.login_admin()

        response = self.client.get(
            reverse("shift_create"),
            {"service_date": "2026-06-19", "modal": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="service_date"')
        self.assertContains(response, 'type="date"')
        self.assertContains(response, 'lang="en-AU"')
        self.assertContains(response, "Select participant")
        self.assertContains(response, "Select worker")
        self.assertContains(response, "Select support item")
        self.assertNotContains(response, "---------")

    def test_shift_create_modal_post_valid_returns_json_success(self):
        self.login_admin()

        response = self.client.post(
            f"{reverse('shift_create')}?modal=1",
            self.shift_payload(service_date="2026-06-10", modal="1"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertTrue(Shift.objects.filter(service_date=date(2026, 6, 10)).exists())

    def test_shift_create_modal_post_invalid_returns_partial_with_errors(self):
        self.login_admin()

        response = self.client.post(
            f"{reverse('shift_create')}?modal=1",
            self.shift_payload(end_time="08:00", modal="1"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'class="shift-modal-dialog"', status_code=400)
        self.assertContains(response, "End time must be after start time", status_code=400)
        self.assertEqual(Shift.objects.count(), 0)

    def test_shift_detail_shows_workflow_status_panel(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.DRAFT,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, "Workflow Status")
        self.assertContains(response, "Draft shift")
        self.assertContains(response, "Next step: publish this shift")
        self.assertContains(response, "Publish")
        self.assertContains(response, "Edit Shift")

    def test_shift_detail_only_shows_one_publish_action(self):
        shift = self.create_shift(status=Shift.Status.DRAFT)
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, ">Publish</button>", count=1)

    def test_shift_detail_keeps_edit_action_in_workflow_panel(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertNotContains(response, ">Edit</a>")
        self.assertContains(response, ">Edit Shift</a>", count=1)

    def test_shift_detail_shows_worker_record_link_for_published_shift(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, "View Worker")
        self.assertContains(response, reverse("worker_detail", args=[self.worker.id]))

    def test_shift_detail_uses_scoped_layout_classes(self):
        shift = self.create_shift(status=Shift.Status.COMPLETED)
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, 'class="shift-detail-page"')
        self.assertContains(response, 'class="card roster-workflow-card"')
        self.assertContains(response, 'class="detail-grid shift-detail-grid"')

    def test_shift_detail_uses_scoped_cancel_section(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, 'class="card shift-cancel-card"')
        self.assertContains(response, 'class="shift-cancel-form"')
        self.assertContains(response, "Use this only when the scheduled shift should not go ahead.")

    def test_shift_detail_formats_read_only_information(self):
        shift = self.create_shift(
            status=Shift.Status.PUBLISHED,
            location="",
            address="",
            instructions="",
            admin_notes="",
        )
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, 'class="card shift-info-card"')
        self.assertContains(response, 'class="detail-value detail-value-long"')
        self.assertContains(response, 'class="detail-empty">-</span>')

    def test_shift_detail_back_link_preserves_roster_state(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        list_path = (
            f"{reverse('roster_list')}?worker=Wendy&status=published"
            "&sort=date&direction=asc&page=2"
        )
        self.login_admin()

        list_response = self.client.get(list_path)
        detail_response = self.client.get(reverse("shift_detail", args=[shift.id]), {"next": list_path})

        self.assertContains(
            list_response,
            f"{reverse('shift_detail', args=[shift.id])}?next=",
        )
        self.assertContains(detail_response, f'href="{list_path.replace("&", "&amp;")}"')

    def test_shift_create_prefills_participant_and_worker_from_shortcut(self):
        self.login_admin()

        response = self.client.get(
            reverse("shift_create"),
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

    def test_admin_can_create_published_shift(self):
        self.login_admin()

        response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(status=Shift.Status.PUBLISHED),
        )

        shift = Shift.objects.get()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.PUBLISHED)

    def test_shift_edit_preserves_roster_return_state(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        list_path = (
            f"{reverse('roster_list')}?worker=Wendy&status=published"
            "&sort=date&direction=asc&page=2"
        )
        self.login_admin()

        list_response = self.client.get(list_path)
        edit_response = self.client.get(reverse("shift_edit", args=[shift.id]), {"next": list_path})
        post_response = self.client.post(
            reverse("shift_edit", args=[shift.id]),
            self.shift_payload(status=Shift.Status.PUBLISHED, next=list_path),
        )

        self.assertContains(
            list_response,
            f"{reverse('shift_edit', args=[shift.id])}?next=",
        )
        self.assertContains(edit_response, f'href="{list_path.replace("&", "&amp;")}"')
        self.assertContains(edit_response, f'name="next" value="{list_path.replace("&", "&amp;")}"')
        self.assertRedirects(post_response, list_path)

    def test_end_time_must_be_after_start_time(self):
        self.login_admin()

        response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(start_time="11:00", end_time="09:00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "End time must be after start time")
        self.assertEqual(Shift.objects.count(), 0)

    def test_worker_overlap_is_blocked_for_active_shift_statuses(self):
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("shift_create"),
            self.shift_payload(start_time="10:00", end_time="12:00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Worker has an overlapping active shift")
        self.assertEqual(Shift.objects.count(), 1)

    def test_admin_can_filter_roster_list(self):
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        Shift.objects.create(
            participant=self.participant,
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.DRAFT,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"worker": "Wendy", "status": Shift.Status.PUBLISHED},
        )

        self.assertContains(response, "Wendy Worker")
        self.assertNotContains(response, "<td>Oscar Other</td>", html=True)

    def test_roster_list_renders_status_specific_class(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("roster_list"))

        self.assertContains(response, 'class="status-pill status-published"')

    def test_roster_list_displays_australian_date_format(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("roster_list"))

        self.assertContains(response, 'class="roster-date-cell">01/06/2026</td>')
        self.assertNotContains(response, "June 1, 2026")

    def test_shift_detail_displays_australian_date_format(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("shift_detail", args=[shift.id]))

        self.assertContains(response, "01/06/2026 |")
        self.assertNotContains(response, "June 1, 2026 |")

    def test_roster_list_uses_readability_table_classes(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("roster_list"))

        self.assertContains(response, 'class="card table-card roster-table-card"')
        self.assertContains(response, 'class="roster-table"')
        self.assertContains(response, 'class="roster-date-cell"')
        self.assertContains(response, 'class="roster-time-cell"')
        self.assertContains(response, 'class="roster-person-cell"')
        self.assertContains(response, 'class="roster-service-cell"')

    def test_roster_list_shows_quick_date_filters(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("roster_list"))

        self.assertContains(response, "Today")
        self.assertContains(response, "This week")
        self.assertContains(response, "Next week")
        self.assertContains(response, "All upcoming")
        self.assertContains(response, 'class="quick-filter-row"')

    def test_roster_quick_range_filters_dates(self):
        self.create_shift(
            service_date=date(2026, 6, 8),
            status=Shift.Status.PUBLISHED,
        )
        self.create_shift(
            service_date=date(2026, 6, 20),
            status=Shift.Status.PUBLISHED,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"quick": "this_week", "today": "2026-06-08"},
        )

        self.assertContains(response, "08/06/2026")
        self.assertNotContains(response, "20/06/2026")
        self.assertContains(response, "Showing shifts from 08/06/2026 to 14/06/2026.")

    def test_roster_list_shows_next_action_for_shift_status(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("roster_list"))

        self.assertContains(response, "Awaiting worker confirmation")
        self.assertContains(response, 'class="roster-next-action-cell"')

    def test_roster_list_links_to_quick_planner(self):
        self.login_admin()

        response = self.client.get(reverse("roster_list"))

        self.assertContains(response, "Quick Planner")
        self.assertContains(response, reverse("roster_planner"))

    def test_roster_planner_filters_existing_shifts(self):
        matching_shift = self.create_shift(
            service_date=date(2026, 6, 8),
            status=Shift.Status.DRAFT,
        )
        self.create_shift(
            worker=self.other_worker,
            service_date=date(2026, 6, 9),
            status=Shift.Status.PUBLISHED,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "date_from": "2026-06-08",
                "date_to": "2026-06-14",
            },
        )

        self.assertContains(response, "Quick Roster Planner")
        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, "Wendy Worker")
        self.assertContains(response, "08/06/2026")
        self.assertContains(response, "Draft")
        self.assertContains(response, reverse("shift_detail", args=[matching_shift.id]))
        self.assertNotContains(response, "<p>Oscar Other</p>", html=True)

    def test_roster_planner_defaults_to_participant_view(self):
        self.login_admin()

        response = self.client.get(reverse("roster_planner"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participant view")
        self.assertContains(response, "Participant focus")
        self.assertContains(response, "Worker filter")
        self.assertContains(response, "1 week")
        self.assertContains(response, "planner-week-toolbar")
        self.assertEqual(len(response.context["planner_days"]), 7)

    def test_roster_planner_multi_week_range_is_not_month_view(self):
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "date_from": "2026-06-01",
                "date_to": "2026-06-14",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 weeks")
        self.assertContains(response, "multi-week")
        self.assertNotContains(response, "month view")
        self.assertNotContains(response, "Month view")
        self.assertEqual(len(response.context["planner_days"]), 14)

    def test_roster_planner_worker_view_labels_and_filters(self):
        self.login_admin()
        self.create_shift(
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status=Shift.Status.DRAFT,
        )
        self.create_shift(
            service_date=date(2026, 6, 1),
            status=Shift.Status.DRAFT,
        )

        response = self.client.get(
            reverse("roster_planner"),
            {
                "view": "worker",
                "worker": self.worker.id,
                "date_from": "2026-06-01",
                "date_to": "2026-06-07",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Worker view")
        self.assertContains(response, "Worker focus")
        self.assertContains(response, "Participant filter")
        self.assertContains(response, self.worker.display_name)
        self.assertNotContains(
            response,
            f'<p class="planner-shift-meta">{self.other_worker.display_name}</p>',
            html=True,
        )

    def test_roster_planner_renders_date_grid_with_empty_days(self):
        self.create_shift(
            service_date=date(2026, 6, 8),
            status=Shift.Status.DRAFT,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "date_from": "2026-06-08",
                "date_to": "2026-06-10",
            },
        )

        self.assertContains(response, "planner-date-grid")
        self.assertContains(response, "Mon")
        self.assertContains(response, "08/06")
        self.assertContains(response, "09/06")
        self.assertContains(response, "10/06")
        self.assertNotContains(response, ">No shifts<")
        self.assertContains(response, "9:00 am - 11:00 am")
        self.assertNotContains(response, "a.m.")

    def test_roster_planner_marks_weekly_grid_and_weekends(self):
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "date_from": "2026-06-08",
                "date_to": "2026-06-14",
            },
        )

        self.assertContains(response, 'class="planner-date-grid planner-week-grid"')
        self.assertContains(response, 'class="planner-day-card planner-weekend"')
        self.assertContains(response, "Sat")
        self.assertContains(response, "Sun")

    def test_roster_planner_day_links_prefill_new_shift(self):
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "date_from": "2026-06-08",
                "date_to": "2026-06-08",
            },
        )

        self.assertContains(
            response,
            'class="planner-add-shift planner-add-shift-square js-shift-modal-trigger"',
        )
        self.assertContains(response, 'data-modal-url="')
        self.assertContains(response, "modal=1")
        self.assertContains(response, 'title="Add Shift"')
        self.assertContains(response, ">+</a>")
        self.assertNotContains(response, ">Add Shift</a>")
        self.assertContains(response, "participant=1")
        self.assertContains(response, "worker=1")
        self.assertContains(response, "service_date=2026-06-08")
        self.assertContains(response, "next=")

    def test_roster_planner_shift_copy_link_prefills_new_shift_modal(self):
        self.create_shift(
            service_date=date(2026, 6, 8),
            start_time=time(8, 30),
            end_time=time(12, 30),
            break_minutes=15,
            status=Shift.Status.COMPLETED,
            location="Participant home",
            address="10 Creek Street",
            instructions="Use side entrance.",
            admin_notes="Copied note.",
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "date_from": "2026-06-08",
                "date_to": "2026-06-08",
            },
        )

        self.assertContains(
            response,
            'class="planner-shift-action planner-shift-copy-link js-shift-copy-source js-shift-modal-trigger"',
        )
        self.assertContains(response, 'data-copy-url="')
        self.assertContains(response, 'class="planner-paste-shift planner-paste-shift-hidden js-shift-paste-target"')
        self.assertContains(response, 'data-service-date="2026-06-08"')
        self.assertContains(response, 'title="Paste copied shift"')
        self.assertContains(response, 'class="planner-shift-action planner-shift-view"')
        self.assertContains(response, 'aria-hidden="true"')
        self.assertContains(response, 'title="Copy shift"')
        self.assertContains(response, 'title="View shift"')
        self.assertNotContains(response, ">Copy</a>")
        self.assertNotContains(response, ">View</a>")
        self.assertContains(response, "Copy shift from 08/06/2026")
        self.assertContains(response, "participant=1")
        self.assertContains(response, "worker=1")
        self.assertContains(response, "service_date=2026-06-08")
        self.assertContains(response, "start_time=08%3A30")
        self.assertContains(response, "end_time=12%3A30")
        self.assertContains(response, "break_minutes=15")
        self.assertContains(response, "support_item=1")
        self.assertContains(response, f"service_type={Shift.ServiceType.PERSONAL_CARE}")
        self.assertContains(response, f"status={Shift.Status.DRAFT}")
        self.assertContains(response, "modal=1")
        self.assertContains(response, "next=")

    def test_roster_planner_shows_delete_action_only_for_unstarted_shifts(self):
        draft_shift = self.create_shift(status=Shift.Status.DRAFT, service_date=date(2026, 6, 8))
        published_shift = self.create_shift(
            status=Shift.Status.PUBLISHED,
            service_date=date(2026, 6, 8),
            start_time=time(12, 0),
            end_time=time(14, 0),
        )
        completed_shift = self.create_shift(
            status=Shift.Status.COMPLETED,
            service_date=date(2026, 6, 8),
            start_time=time(15, 0),
            end_time=time(17, 0),
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_planner"),
            {
                "date_from": "2026-06-08",
                "date_to": "2026-06-08",
            },
        )

        self.assertContains(response, reverse("shift_delete", args=[draft_shift.id]))
        self.assertContains(response, reverse("shift_delete", args=[published_shift.id]))
        self.assertNotContains(response, reverse("shift_delete", args=[completed_shift.id]))
        self.assertContains(response, 'class="planner-shift-delete-form"')
        self.assertContains(response, 'class="planner-shift-action planner-shift-delete"')
        self.assertContains(response, 'title="Delete shift"')
        self.assertContains(response, 'aria-label="Delete shift"')

    def test_admin_can_delete_draft_shift_from_planner_and_return_to_current_view(self):
        shift = self.create_shift(status=Shift.Status.DRAFT, service_date=date(2026, 6, 8))
        next_url = f"{reverse('roster_planner')}?date_from=2026-06-08&date_to=2026-06-08"
        self.login_admin()

        response = self.client.post(
            reverse("shift_delete", args=[shift.id]),
            {"next": next_url},
        )

        self.assertRedirects(response, next_url)
        self.assertFalse(Shift.objects.filter(id=shift.id).exists())

    def test_admin_cannot_delete_completed_shift(self):
        shift = self.create_shift(status=Shift.Status.COMPLETED)
        self.login_admin()

        response = self.client.post(reverse("shift_delete", args=[shift.id]))

        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertTrue(Shift.objects.filter(id=shift.id).exists())

    def test_shift_create_prefills_service_date_from_planner(self):
        self.login_admin()

        response = self.client.get(
            reverse("shift_create"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "service_date": "2026-06-08",
            },
        )

        self.assertContains(
            response,
            '<option value="1" selected>Ava Nguyen</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="1" selected>Wendy Worker</option>',
            html=True,
        )
        self.assertContains(response, 'value="2026-06-08"')

    def test_shift_create_prefills_planner_default_location_and_address(self):
        self.participant.address_line_2 = "Unit 4"
        self.participant.save()
        self.login_admin()

        response = self.client.get(
            reverse("shift_create"),
            {
                "participant": self.participant.id,
                "worker": self.worker.id,
                "service_date": "2026-06-08",
                "from_planner": "1",
            },
        )

        self.assertContains(response, '<option value="draft" selected>Draft</option>', html=True)
        self.assertContains(response, 'value="Participant home"')
        self.assertContains(response, "10 Creek Street")
        self.assertContains(response, "Unit 4")
        self.assertContains(response, "Brisbane QLD 4000")

    def test_roster_draft_filter_shows_bulk_publish_action(self):
        self.create_shift(status=Shift.Status.DRAFT)
        self.create_shift(status=Shift.Status.DRAFT, service_date=date(2026, 6, 2))
        self.login_admin()

        response = self.client.get(reverse("roster_list"), {"status": Shift.Status.DRAFT})

        self.assertContains(response, "2 draft shifts ready to publish")
        self.assertContains(response, "Publish 2 draft shifts")
        self.assertContains(response, reverse("shift_bulk_publish"))
        self.assertContains(
            response,
            '<input type="hidden" name="status" value="draft">',
            html=True,
        )

    def test_roster_bulk_publish_publishes_filtered_draft_shifts_only(self):
        matching_shift = self.create_shift(
            service_date=date(2026, 6, 8),
            status=Shift.Status.DRAFT,
        )
        outside_filter = self.create_shift(
            service_date=date(2026, 6, 20),
            status=Shift.Status.DRAFT,
        )
        already_published = self.create_shift(
            service_date=date(2026, 6, 8),
            status=Shift.Status.PUBLISHED,
        )
        self.login_admin()

        response = self.client.post(
            reverse("shift_bulk_publish"),
            {
                "status": Shift.Status.DRAFT,
                "date_from": "2026-06-08",
                "date_to": "2026-06-08",
            },
        )

        matching_shift.refresh_from_db()
        outside_filter.refresh_from_db()
        already_published.refresh_from_db()
        self.assertRedirects(
            response,
            (
                f"{reverse('roster_list')}?status={Shift.Status.PUBLISHED}"
                "&date_from=2026-06-08&date_to=2026-06-08"
            ),
        )
        self.assertEqual(matching_shift.status, Shift.Status.PUBLISHED)
        self.assertEqual(outside_filter.status, Shift.Status.DRAFT)
        self.assertEqual(already_published.status, Shift.Status.PUBLISHED)

    def test_roster_worker_filter_uses_worker_name_search(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"worker": "Wendy"},
        )

        self.assertContains(response, 'name="worker"')
        self.assertContains(response, 'placeholder="Name, email, or phone"')
        self.assertNotContains(response, 'placeholder="Worker ID"')

    def test_roster_can_filter_by_participant_and_worker_name(self):
        ben = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            status=Participant.Status.ACTIVE,
            address_line_1="20 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        Shift.objects.create(
            participant=ben,
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"participant": "Ava", "worker": "Wendy"},
        )

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, "Wendy Worker")
        self.assertNotContains(response, "<td>Ben Taylor</td>", html=True)
        self.assertNotContains(response, "<td>Oscar Other</td>", html=True)
        self.assertContains(
            response,
            'Showing shifts matching participant &quot;Ava&quot; and worker &quot;Wendy&quot;.',
        )
        self.assertContains(response, 'placeholder="Name, NDIS, or phone"')
        self.assertContains(response, 'placeholder="Name, email, or phone"')

    def test_roster_can_filter_participant_by_ndis_or_phone(self):
        self.participant.ndis_number = "430000001"
        self.participant.phone = "0400000001"
        self.participant.save()
        ben = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            ndis_number="430000002",
            phone="0400000002",
            status=Participant.Status.ACTIVE,
            address_line_1="20 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.create_shift(participant=self.participant)
        self.create_shift(
            participant=ben,
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
        )
        self.login_admin()

        ndis_response = self.client.get(reverse("roster_list"), {"participant": "430000001"})
        phone_response = self.client.get(reverse("roster_list"), {"participant": "0400000001"})

        self.assertContains(ndis_response, "Ava Nguyen")
        self.assertNotContains(ndis_response, "<td>Ben Taylor</td>", html=True)
        self.assertContains(phone_response, "Ava Nguyen")
        self.assertNotContains(phone_response, "<td>Ben Taylor</td>", html=True)
        self.assertContains(ndis_response, 'placeholder="Name, NDIS, or phone"')

    def test_roster_can_filter_worker_by_email_or_phone(self):
        self.worker.phone = "0411111111"
        self.worker.save()
        self.other_worker.phone = "0422222222"
        self.other_worker.save()
        self.create_shift(worker=self.worker)
        self.create_shift(
            worker=self.other_worker,
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
        )
        self.login_admin()

        email_response = self.client.get(reverse("roster_list"), {"worker": "worker@example.com"})
        phone_response = self.client.get(reverse("roster_list"), {"worker": "0411111111"})

        self.assertContains(email_response, "Wendy Worker")
        self.assertNotContains(email_response, "<td>Oscar Other</td>", html=True)
        self.assertContains(phone_response, "Wendy Worker")
        self.assertNotContains(phone_response, "<td>Oscar Other</td>", html=True)
        self.assertContains(email_response, 'placeholder="Name, email, or phone"')

    def test_roster_list_shows_status_filter_summary(self):
        self.create_shift(status=Shift.Status.DRAFT)
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"status": Shift.Status.DRAFT},
        )

        self.assertContains(response, "Showing draft shifts.")
        self.assertContains(response, reverse("roster_list"))

    def test_roster_list_shows_multi_filter_summary(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
                "worker": "Wendy",
                "status": Shift.Status.PUBLISHED,
            },
        )

        self.assertContains(
            response,
            'Showing published shifts matching worker &quot;Wendy&quot; from 01/06/2026 to 30/06/2026.',
        )

    def test_roster_list_is_paginated_and_preserves_filters(self):
        for index in range(25):
            self.create_shift(
                service_date=date(2026, 6, index + 1),
                start_time=time(9, 0),
                end_time=time(10, 0),
                planned_hours=Decimal("1.00"),
                status=Shift.Status.PUBLISHED,
            )
        self.create_shift(
            worker=self.other_worker,
            service_date=date(2026, 6, 26),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            status=Shift.Status.DRAFT,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {
                "worker": "Wendy",
                "status": Shift.Status.PUBLISHED,
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
            },
        )

        self.assertEqual(response.context["shifts"].paginator.count, 25)
        self.assertEqual(len(response.context["shifts"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(
            response,
            "?worker=Wendy&amp;status=published&amp;date_from=2026-06-01&amp;date_to=2026-06-30&amp;page=2",
        )
        self.assertNotContains(response, "<td>Oscar Other</td>", html=True)

    def test_roster_list_can_sort_by_date_and_preserve_filters(self):
        self.create_shift(
            service_date=date(2026, 6, 3),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            status=Shift.Status.PUBLISHED,
        )
        self.create_shift(
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            status=Shift.Status.PUBLISHED,
        )
        self.login_admin()

        response = self.client.get(
            reverse("roster_list"),
            {"status": Shift.Status.PUBLISHED, "sort": "date", "direction": "asc"},
        )
        content = response.content.decode()

        self.assertLess(content.index("01/06/2026"), content.index("03/06/2026"))
        self.assertContains(response, "?status=published&amp;sort=date&amp;direction=desc")

    def test_roster_list_distinguishes_empty_filter_results(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.login_admin()

        response = self.client.get(reverse("roster_list"), {"worker": "Missing"})

        self.assertContains(response, "No shifts match the current filters.")
        self.assertContains(response, "Clear filters")
        self.assertNotContains(response, "Create a shift or adjust the filters")

    def test_worker_can_only_see_own_non_draft_shifts(self):
        own_shift = self.create_shift()
        self.create_shift(
            service_date=date(2026, 6, 2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.DRAFT,
        )
        self.create_shift(
            worker=self.other_worker,
            service_date=date(2026, 6, 1),
            start_time=time(12, 0),
            end_time=time(13, 0),
            planned_hours=Decimal("1.00"),
            service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.PUBLISHED,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_shift_list"))

        self.assertContains(response, "Ava Nguyen")
        self.assertContains(response, str(own_shift.id))
        self.assertNotContains(response, "Draft")
        self.assertNotContains(response, "Oscar Other")

    def test_worker_shift_surfaces_display_australian_dates(self):
        shift = self.create_shift(status=Shift.Status.PUBLISHED)
        self.client.login(username="worker", password="test-password-123")

        list_response = self.client.get(reverse("worker_shift_list"))
        detail_response = self.client.get(reverse("worker_shift_detail", args=[shift.id]))

        self.assertContains(list_response, "01/06/2026")
        self.assertNotContains(list_response, "June 1, 2026")
        self.assertContains(detail_response, "<dt>Date</dt><dd>01/06/2026</dd>", html=True)
        self.assertNotContains(detail_response, "<dt>Date</dt><dd>June 1, 2026</dd>", html=True)

    def test_worker_shift_list_groups_and_highlights_shift_statuses(self):
        completed_shift = self.create_shift(
            service_date=date(2026, 5, 21),
            status=Shift.Status.COMPLETED,
        )
        published_shift = self.create_shift(
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        confirmed_shift = self.create_shift(
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))
        content = response.content.decode()

        self.assertContains(response, "1 needs attention")
        self.assertContains(response, "1 upcoming")
        self.assertContains(response, "1 completed")
        self.assertContains(response, "Needs attention")
        self.assertContains(response, "Upcoming")
        self.assertContains(response, "Completed")
        self.assertContains(response, "status-pill status-published")
        self.assertContains(response, "status-pill status-confirmed")
        self.assertContains(response, "status-pill status-completed")
        self.assertLess(
            content.index(f"#{published_shift.id}"),
            content.index(f"#{completed_shift.id}"),
        )
        self.assertLess(
            content.index(f"#{confirmed_shift.id}"),
            content.index(f"#{completed_shift.id}"),
        )

    def test_worker_shift_list_shows_status_quick_actions(self):
        published_shift = self.create_shift(
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        confirmed_shift = self.create_shift(
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        completed_shift = self.create_shift(
            service_date=date(2026, 6, 6),
            status=Shift.Status.COMPLETED,
        )
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))
        content = response.content.decode()

        self.assertContains(response, reverse("worker_shift_confirm", args=[published_shift.id]))
        self.assertContains(response, "Confirm")
        self.assertContains(
            response,
            reverse("worker_service_log_create", args=[confirmed_shift.id]),
        )
        self.assertContains(response, "Complete Log")
        completed_section = content[content.index(f"#{completed_shift.id}") :]
        self.assertNotIn("Confirm", completed_section)
        self.assertNotIn("Complete Log", completed_section)

    def test_worker_shift_list_can_filter_by_shift_group(self):
        published_shift = self.create_shift(
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        confirmed_shift = self.create_shift(
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        completed_shift = self.create_shift(
            service_date=date(2026, 6, 6),
            status=Shift.Status.COMPLETED,
        )
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(
            reverse("worker_shift_list"),
            {"view": "needs_attention"},
        )

        self.assertContains(response, f"#{published_shift.id}")
        self.assertNotContains(response, f"#{confirmed_shift.id}")
        self.assertNotContains(response, f"#{completed_shift.id}")
        self.assertContains(response, "filter-active")
        self.assertContains(response, "Needs attention")
        self.assertNotContains(response, "Upcoming</h2>")
        self.assertNotContains(response, "Completed</h2>")

    def test_worker_shift_list_shows_filter_navigation(self):
        self.create_shift(status=Shift.Status.PUBLISHED)
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))

        self.assertContains(response, '?view=all')
        self.assertContains(response, '?view=needs_attention')
        self.assertContains(response, '?view=upcoming')
        self.assertContains(response, '?view=completed')

    def test_worker_shift_list_marks_sidebar_link_as_active(self):
        self.client.login(username="worker", password="test-password-123")

        response = self.client.get(reverse("worker_shift_list"))

        self.assertContains(
            response,
            f'class="sidebar-link active" href="{reverse("worker_shift_list")}"',
        )

    def test_worker_can_view_and_confirm_own_published_shift(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        self.client.login(username="worker", password="test-password-123")
        detail_response = self.client.get(reverse("worker_shift_detail", args=[shift.id]))
        confirm_response = self.client.post(reverse("worker_shift_confirm", args=[shift.id]))

        shift.refresh_from_db()
        self.assertContains(detail_response, "Confirm Shift")
        self.assertRedirects(confirm_response, reverse("worker_shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.CONFIRMED)
        self.assertIsNotNone(shift.confirmed_at)

    def test_worker_cannot_access_other_worker_shift(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.other_worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        self.client.login(username="worker", password="test-password-123")
        response = self.client.get(reverse("worker_shift_detail", args=[shift.id]))

        self.assertEqual(response.status_code, 404)

    def test_recurring_shift_create_uses_record_form_layout(self):
        self.login_admin()

        response = self.client.get(reverse("recurring_shift_create"))

        self.assertContains(response, 'class="record-form"')
        self.assertContains(response, 'class="card form-section"')
        self.assertNotContains(response, "<p>\n    <label")

    def test_recurring_shift_create_explains_preview_and_cycle_dates(self):
        self.login_admin()

        response = self.client.get(reverse("recurring_shift_create"))

        self.assertContains(response, "Start date and end date define the recurring schedule window.")
        self.assertContains(response, 'class="info-notice recurring-helper-notice"')
        self.assertContains(
            response,
            "Preview proposed dates before creating anything. Confirming creates non-conflicting shifts as drafts.",
        )

    def test_recurring_shift_preview_uses_table_card_layout(self):
        self.login_admin()

        response = self.client.get(
            reverse("recurring_shift_create"),
            self.recurring_shift_payload(),
        )

        self.assertContains(response, "Preview")
        self.assertContains(response, 'class="card table-card recurring-preview-table"')
        self.assertContains(response, "Create Non-conflicting Draft Shifts")
        self.assertContains(response, "Conflicting dates will be skipped when draft shifts are created.")

    def test_recurring_shift_create_keeps_creation_flow(self):
        self.login_admin()

        response = self.client.post(
            reverse("recurring_shift_create"),
            {**self.recurring_shift_payload(), "confirm": "1"},
        )

        self.assertRedirects(response, f"{reverse('roster_list')}?status={Shift.Status.DRAFT}")
        self.assertEqual(
            Shift.objects.filter(
                participant=self.participant,
                worker=self.worker,
                status=Shift.Status.DRAFT,
            ).count(),
            3,
        )

    def test_admin_can_cancel_shift_with_reason(self):
        shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.login_admin()

        response = self.client.post(
            reverse("shift_cancel", args=[shift.id]),
            {"cancellation_reason": "Participant unavailable."},
        )

        shift.refresh_from_db()
        self.assertRedirects(response, reverse("shift_detail", args=[shift.id]))
        self.assertEqual(shift.status, Shift.Status.CANCELLED)
        self.assertEqual(shift.cancellation_reason, "Participant unavailable.")
