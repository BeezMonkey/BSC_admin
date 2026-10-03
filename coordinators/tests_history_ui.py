from copy import deepcopy
from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import UserProfile

from .models import CoordinationLog, CoordinationLogChange, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


class HistoryPresentationTests(SimpleTestCase):
    def test_business_and_review_fields_are_separate_without_dropping_changes(self):
        change = CoordinationLogChange(
            before={"case_notes": "Original", "status": "approved", "reviewed_by": "Admin"},
            after={"case_notes": "Updated", "status": "submitted", "reviewed_by": ""},
        )
        original = deepcopy((change.before, change.after))
        self.assertEqual([field["key"] for field in change.content_changes], ["case_notes"])
        self.assertEqual([field["key"] for field in change.review_changes], ["status", "reviewed_by"])
        self.assertEqual(change.changed_fields_summary, "Case notes")
        self.assertEqual(len(change.field_changes), len(change.content_changes) + len(change.review_changes))
        self.assertEqual((change.before, change.after), original)

    def test_summary_stays_short_when_many_fields_change(self):
        change = CoordinationLogChange(
            before={"service_date": "2026-10-01", "start_time": "09:00:00", "actual_hours": "1.00"},
            after={"service_date": "2026-10-02", "start_time": "10:00:00", "actual_hours": "2.00"},
        )
        self.assertEqual(change.changed_fields_summary, "Service date, Start time + 1 more")
        self.assertEqual(len(change.content_changes), 3)

    def test_review_only_change_has_no_business_diff(self):
        change = CoordinationLogChange(before={"status": "submitted"}, after={"status": "approved"})
        self.assertEqual(change.content_changes, [])
        self.assertEqual(change.changed_fields_summary, "")
        self.assertEqual(change.review_changes[0]["after"], "Approved")


class HistoryTemplateTests(TestCase):
    def setUp(self):
        self.sc = create_coordinator("compact-history-sc")
        self.participant = create_participant()
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.participant, coordinator=self.sc, start_date=date(2026, 1, 1),
        )
        self.admin = get_user_model().objects.create_user(username="compact-history-admin")
        UserProfile.objects.create(user=self.admin, role=UserProfile.Role.ADMIN)
        self.log = CoordinationLog.objects.create(
            participant=self.participant, coordinator=self.sc, service_date=date(2026, 10, 1),
            start_time=time(9), end_time=time(10), actual_hours=Decimal("1.00"), case_notes="Updated notes.",
        )

    def change(self, **overrides):
        fields = {
            "log": self.log, "actor": self.sc.user, "kind": "revision", "reason": "Update notes",
            "before": {"case_notes": "Original notes.", "status": "approved", "reviewed_by": "Admin"},
            "after": {"case_notes": "Updated notes.", "status": "submitted", "reviewed_by": ""},
        }
        fields.update(overrides)
        return CoordinationLogChange.objects.create(**fields)

    def render_history(self, change):
        return render_to_string("coordinators/partials/log_history.html", {"changes": [change]})

    def test_history_has_compact_table_and_collapsed_review_details(self):
        html = self.render_history(self.change())
        self.assertIn('class="sc-log-change-summary"', html)
        self.assertIn('class="sc-log-changed-fields">Case notes</span>', html)
        self.assertIn('class="sc-log-diff"', html)
        self.assertIn('<th scope="col">Before</th>', html)
        self.assertIn('<th scope="col">After</th>', html)
        self.assertIn('<details class="sc-log-review-details">', html)
        self.assertIn('<summary>Review details</summary>', html)
        self.assertNotIn('<details class="sc-log-review-details" open', html)
        self.assertIn("Original notes.", html)
        self.assertIn("Updated notes.", html)
        self.assertIn("Approved", html)
        self.assertIn("Submitted", html)

    def test_long_text_is_complete_and_escaped_with_progressive_toggle(self):
        long_notes = 'A detailed historical note. ' * 80 + '<script>alert("notes")</script>'
        html = self.render_history(self.change(
            before={"case_notes": long_notes}, after={"case_notes": "Short updated note."},
            details="Supporting detail retained in full.",
        ))
        self.assertIn('data-history-text-value', html)
        self.assertIn('data-history-text-toggle', html)
        self.assertIn('hidden>Show full text</button>', html)
        self.assertIn(long_notes[:1000], html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert("notes")</script>', html)
        self.assertIn("Supporting detail retained in full.", html)

    def test_correction_without_diff_keeps_reason_and_details(self):
        html = self.render_history(self.change(
            kind="billing_review", reason="Check billed duration.", details="Confirm with source record.",
            before={"actual_hours": "1.00"}, after={"actual_hours": "1.00"},
        ))
        self.assertIn("Check billed duration.", html)
        self.assertIn("Confirm with source record.", html)
        self.assertIn("This entry does not change the original log or invoice.", html)
        self.assertNotIn('class="sc-log-diff"', html)
        self.assertNotIn('class="sc-log-review-details"', html)

    def test_admin_and_owner_both_have_complete_history(self):
        self.change()
        for user, route in ((self.admin, "coordination_log_detail"), (self.sc.user, "coordinator_log_detail")):
            with self.subTest(route=route):
                self.client.force_login(user)
                response = self.client.get(reverse(route, args=[self.log.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Review details")
                self.assertContains(response, "Original notes.")
                self.assertContains(response, "sc_log_history.")
