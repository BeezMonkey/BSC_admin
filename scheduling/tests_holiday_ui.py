from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from scheduling.forms import ShiftForm
from scheduling.models import Shift, SupportItem
from participants.models import Participant
from workers.models import SupportWorker


class HolidayPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="holiday-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.participant = Participant.objects.create(first_name="Holiday", last_name="Participant")
        worker_user = get_user_model().objects.create_user(username="holiday-worker")
        UserProfile.objects.create(user=worker_user, role=UserProfile.Role.SUPPORT_WORKER)
        cls.worker = SupportWorker.objects.create(user=worker_user, first_name="Holiday", last_name="Worker")
        cls.item = SupportItem.objects.create(
            item_number="holiday-test-item", name="Manually chosen item", price_limit=Decimal("65.47"),
        )
        cls.shift = Shift.objects.create(
            participant=cls.participant, worker=cls.worker, service_date=date(2026, 8, 10),
            start_time=time(9), end_time=time(12), planned_hours=Decimal("3.00"),
            support_item=cls.item, status=Shift.Status.CANCELLED, created_by=cls.admin,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_all_planner_views_include_holidays_even_on_empty_days(self):
        for view in ("daily", "participant", "worker"):
            with self.subTest(view=view):
                response = self.client.get(reverse("roster_planner"), {
                    "view": view, "date_from": "2026-08-10", "date_to": "2026-08-16",
                })
                self.assertContains(response, "Logan only")
                self.assertContains(response, "Brisbane only")
                self.assertContains(response, 'class="holiday-badge holiday-regional"')
                self.assertContains(response, "9:00 am")
                self.assertContains(response, "12:00 pm")
                self.assertContains(response, '<span class="planner-time-part">9:00am</span>', html=True)
                self.assertContains(response, '<span class="planner-time-part">12:00pm</span>', html=True)
                self.assertContains(response, 'title="Copy shift"')
                self.assertContains(response, 'title="View shift"')
                self.assertContains(response, "status-cancelled")
                self.assertNotContains(response, 'title="Edit shift"')
                self.assertNotContains(response, 'title="Delete shift"')

    def test_selected_holiday_is_visible_in_full_page_and_modal(self):
        for modal in ("", "1"):
            with self.subTest(modal=modal):
                response = self.client.get(reverse("shift_create"), {
                    "service_date": "2026-12-24", "modal": modal,
                })
                self.assertContains(response, "Christmas Eve")
                self.assertContains(response, "6 pm - midnight")
                self.assertContains(response, 'data-holiday-reminders')
                self.assertContains(response, 'data-holiday-item-reminder')

    def test_unknown_year_warns_without_disabling_planner(self):
        response = self.client.get(reverse("roster_planner"), {
            "view": "daily", "date_from": "2030-08-05", "date_to": "2030-08-11",
        })
        self.assertContains(response, 'class="holiday-coverage-warning"')
        self.assertContains(response, 'title="Add Shift"')

    def test_shared_picker_does_not_opt_in_by_default(self):
        html = render_to_string("scheduling/partials/date_time_picker_field.html", {
            "field": ShiftForm()["service_date"], "picker_type": "date",
        })
        self.assertNotIn("data-holiday-reminders", html)
        self.assertNotIn("data-selected-holidays", html)

    def test_recurring_preview_labels_each_matching_date(self):
        response = self.client.get(reverse("recurring_shift_create"), {
            "participant": self.participant.pk, "worker": self.worker.pk,
            "frequency": "weekly", "start_date": "2026-08-03", "end_date": "2026-08-17",
            "start_time": "09:00", "end_time": "12:00", "break_minutes": "0",
            "support_item": self.item.pk, "service_type": Shift.ServiceType.PERSONAL_CARE,
            "location": "Brisbane", "address": "", "instructions": "", "admin_notes": "",
        })
        self.assertContains(response, "Logan only")
        self.assertContains(response, "Holiday reminder")
        self.assertEqual(Shift.objects.count(), 1)

    def test_holiday_does_not_change_manual_item_or_saving(self):
        response = self.client.post(reverse("shift_create"), {
            "participant": self.participant.pk, "worker": self.worker.pk,
            "service_date": "2026-10-05", "start_time": "09:00", "end_time": "12:00",
            "break_minutes": "0", "support_item": self.item.pk,
            "service_type": Shift.ServiceType.PERSONAL_CARE, "status": Shift.Status.DRAFT,
            "location": "Participant home", "address": "", "instructions": "", "admin_notes": "",
        })
        self.assertEqual(response.status_code, 302)
        saved = Shift.objects.exclude(pk=self.shift.pk).get()
        self.assertEqual(saved.support_item_id, self.item.pk)
        self.assertEqual(saved.planned_hours, Decimal("3.00"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.price_limit, Decimal("65.47"))
