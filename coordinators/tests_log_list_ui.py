from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import CoordinationLog, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


class CoordinationLogListPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sc = create_coordinator("log-list-sc")
        cls.participant = create_participant()
        ParticipantCoordinatorAssignment.objects.create(
            participant=cls.participant,
            coordinator=cls.sc,
            start_date=date(2026, 1, 1),
        )
        cls.logs = {}
        for status in ("submitted", "approved", "rejected", "invoiced"):
            cls.logs[status] = CoordinationLog.objects.create(
                participant=cls.participant,
                coordinator=cls.sc,
                service_date=date(2026, 10, 1),
                actual_hours=Decimal("1.00"),
                status=status,
                case_notes="Provider follow-up recorded.",
            )

    def setUp(self):
        self.client.force_login(self.sc.user)

    def test_list_loads_scoped_styles_and_retains_portal_styles(self):
        response = self.client.get(reverse("coordinator_log_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/portal.')
        self.assertContains(response, 'css/sc_log_list.')
        self.assertContains(response, 'class="worker-content sc-log-list"')

    def test_actions_are_grouped_and_original_destinations_are_preserved(self):
        response = self.client.get(reverse("coordinator_log_list"))
        self.assertContains(response, '<div class="sc-log-actions">', count=4)
        self.assertContains(response, 'class="sc-log-action sc-log-action--view"', count=4)
        self.assertContains(response, 'class="sc-log-action sc-log-action--edit"', count=3)
        for log in self.logs.values():
            self.assertContains(response, reverse("coordinator_log_detail", args=[log.pk]))

    def test_edit_links_still_follow_existing_eligibility(self):
        response = self.client.get(reverse("coordinator_log_list"))
        for status, log in self.logs.items():
            with self.subTest(status=status):
                edit_url = reverse("coordinator_log_edit", args=[log.pk])
                if status == "invoiced":
                    self.assertNotContains(response, edit_url)
                else:
                    self.assertContains(response, edit_url)

    def test_list_styles_are_not_loaded_on_other_sc_pages(self):
        urls = [
            reverse("coordinator_dashboard"),
            reverse("coordinator_log_create"),
            reverse("coordinator_log_detail", args=[self.logs["submitted"].pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'css/sc_log_list.')

    def test_empty_list_preserves_all_columns_and_empty_state(self):
        CoordinationLog.objects.all().delete()
        response = self.client.get(reverse("coordinator_log_list"))
        self.assertContains(response, 'colspan="7"')
        self.assertContains(response, "No coordination logs submitted yet.")
        self.assertNotContains(response, '<div class="sc-log-actions">')
