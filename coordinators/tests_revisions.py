from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from invoices.models import Invoice, InvoiceLine
from scheduling.models import SupportItem

from .models import CoordinationLog, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


class CoordinationLogRevisionTests(TestCase):
    def setUp(self):
        self.sc = create_coordinator("revision-sc")
        self.participant = create_participant()
        self.assignment = ParticipantCoordinatorAssignment.objects.create(
            participant=self.participant, coordinator=self.sc, start_date=date(2026, 1, 1)
        )
        self.admin = get_user_model().objects.create_user(username="revision-admin")
        UserProfile.objects.create(user=self.admin, role=UserProfile.Role.ADMIN)
        self.log = CoordinationLog.objects.create(
            participant=self.participant, coordinator=self.sc,
            service_date=date(2026, 10, 1), start_time=time(9), end_time=time(10),
            actual_hours=Decimal("1.00"), case_notes="Original case note.",
        )
        self.edit_url = f"/sc/logs/{self.log.pk}/edit/"
        self.client.force_login(self.sc.user)

    def edit_data(self, **overrides):
        response = self.client.get(self.edit_url)
        token = response.context.get("revision_token", "missing") if response.context else "missing"
        data = {
            "participant": self.participant.pk, "service_date": "2026-10-01",
            "duration_hours": "1", "duration_minutes": "0", "coordination_type": "general",
            "case_notes": "Revised case note.", "coordinator_notes": "",
            "revision_reason": "other", "revision_details": "Corrected the provider outcome.",
            "revision_token": token,
        }
        data.update(overrides)
        return data

    def review_data(self, **overrides):
        response = self.client.get(reverse("coordination_log_detail", args=[self.log.pk]))
        data = {"revision_token": response.context.get("revision_token", "missing")}
        data.update(overrides)
        return data

    def invoice_log(self, status=Invoice.Status.DRAFT):
        item = SupportItem.objects.create(
            item_number="07_002_0106_8_3", name="Support coordination",
            unit=SupportItem.Unit.HOUR, price_limit=Decimal("100.00"), is_active=True,
        )
        invoice = Invoice.objects.create(
            participant=self.participant, period_start=self.log.service_date,
            period_end=self.log.service_date, created_by=self.admin,
            invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION, status=status,
        )
        InvoiceLine.objects.create_from_coordination_log(invoice, self.log, item)
        self.log.status = CoordinationLog.Status.INVOICED
        self.log.save()
        return invoice

    def test_submitted_edit_preserves_id_and_records_before_after(self):
        response = self.client.post(self.edit_url, self.edit_data())
        self.assertEqual(response.status_code, 302)
        self.log.refresh_from_db()
        self.assertEqual(CoordinationLog.objects.count(), 1)
        self.assertEqual(self.log.case_notes, "Revised case note.")
        self.assertEqual(self.log.status, "submitted")
        change = self.log.changes.get()
        self.assertEqual(change.before["case_notes"], "Original case note.")
        self.assertEqual(change.after["case_notes"], self.log.case_notes)
        self.assertEqual(change.actor, self.sc.user)
        self.assertEqual(change.reason, "Other")
        self.assertEqual(change.details, "Corrected the provider outcome.")
        self.assertTrue(AuditLog.objects.filter(action="coordination_log_revised").exists())

    def test_preset_reasons_do_not_require_details(self):
        reasons = {
            "appointment_changed": "Appointment changed",
            "correct_time": "Correct date / time / hours",
            "update_notes": "Update notes",
            "admin_feedback": "Address admin feedback",
        }
        for reason, label in reasons.items():
            with self.subTest(reason=reason):
                response = self.client.post(self.edit_url, self.edit_data(
                    revision_reason=reason, revision_details="", case_notes=f"Updated for {reason}.",
                ))
                self.assertEqual(response.status_code, 302)
                change = self.log.changes.first()
                self.assertEqual(change.reason, label)
                self.assertEqual(change.details, "")

    def test_reason_picker_starts_empty_and_only_exists_on_edit(self):
        response = self.client.get(self.edit_url)
        self.assertContains(response, '<select name="revision_reason"')
        self.assertContains(response, '<option value="" selected>Select a reason</option>', html=True)
        self.assertNotContains(response, "Add details")
        response = self.client.get(reverse("coordinator_log_create"))
        self.assertNotContains(response, 'name="revision_reason"')
        self.assertNotContains(response, "sc_log_revision.js")

    def test_invalid_or_missing_reason_does_not_save(self):
        for reason in ("", "invented", "Updated appointment details"):
            with self.subTest(reason=reason):
                response = self.client.post(self.edit_url, self.edit_data(revision_reason=reason))
                self.assertEqual(response.status_code, 200)
                self.assertIn("revision_reason", response.context["form"].errors)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertFalse(self.log.changes.exists())

    def test_other_requires_details_and_preserves_entered_changes(self):
        response = self.client.post(self.edit_url, self.edit_data(revision_details="   "))
        self.assertEqual(response.status_code, 200)
        self.assertIn("revision_details", response.context["form"].errors)
        self.assertContains(response, "Additional details (required)")
        self.assertEqual(response.context["form"]["revision_reason"].value(), "other")
        self.assertEqual(response.context["form"]["case_notes"].value(), "Revised case note.")
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertFalse(self.log.changes.exists())

    def test_other_details_are_trimmed_and_recorded(self):
        response = self.client.post(self.edit_url, self.edit_data(
            revision_reason="other", revision_details="  Participant changed appointment.  ",
        ))
        self.assertEqual(response.status_code, 302)
        change = self.log.changes.get()
        self.assertEqual(change.reason, "Other")
        self.assertEqual(change.details, "Participant changed appointment.")

    def test_other_revision_details_length_is_limited(self):
        response = self.client.post(self.edit_url, self.edit_data(
            revision_reason="other", revision_details="x" * 2001,
        ))
        self.assertEqual(response.status_code, 200)
        self.assertIn("revision_details", response.context["form"].errors)
        self.assertFalse(self.log.changes.exists())

    def test_presets_ignore_hidden_details_including_oversized_values(self):
        for reason in ("appointment_changed", "correct_time", "update_notes", "admin_feedback"):
            for details in ("Stale hidden explanation.", "x" * 2001):
                with self.subTest(reason=reason, length=len(details)):
                    response = self.client.post(self.edit_url, self.edit_data(
                        revision_reason=reason, revision_details=details,
                        case_notes=f"Updated for {reason}, details length {len(details)}.",
                    ))
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(self.log.changes.first().details, "")

    def test_revision_details_are_escaped_in_history(self):
        self.client.post(self.edit_url, self.edit_data(revision_details='<script>alert("details")</script>'))
        response = self.client.get(reverse("coordinator_log_detail", args=[self.log.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("details")</script>')

    def test_approved_edit_clears_approval_but_preserves_it_in_history(self):
        self.log.status = "approved"
        self.log.reviewed_by = self.admin
        self.log.reviewed_at = timezone.now()
        self.log.save()
        self.client.post(self.edit_url, self.edit_data(duration_hours="2"))
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, "submitted")
        self.assertIsNone(self.log.reviewed_by)
        self.assertIsNone(self.log.reviewed_at)
        self.assertEqual(self.log.actual_hours, Decimal("2.00"))
        self.assertEqual(self.log.changes.get().before["reviewed_by_id"], self.admin.pk)
        self.assertEqual(self.log.changes.get().before["status"], "approved")

    def test_rejected_edit_resubmits_and_preserves_rejection_reason(self):
        self.log.status = "rejected"
        self.log.rejection_reason = "Clarify outcome."
        self.log.save()
        self.client.post(self.edit_url, self.edit_data())
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, "submitted")
        self.assertEqual(self.log.rejection_reason, "")
        self.assertEqual(self.log.changes.get().before["rejection_reason"], "Clarify outcome.")

    def test_required_reason_and_no_change_and_duration_validation(self):
        cases = [
            {"revision_reason": "   "}, {"case_notes": "Original case note."},
            {"duration_hours": "-1"}, {"duration_minutes": "60"},
            {"duration_hours": "0", "duration_minutes": "0"}, {"case_notes": "   "},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(self.edit_url, self.edit_data(**overrides))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.log.refresh_from_db()
                self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertFalse(self.log.changes.exists())

    def test_forged_participant_is_rejected_even_if_also_assigned(self):
        other = create_participant("Another")
        ParticipantCoordinatorAssignment.objects.create(
            participant=other, coordinator=self.sc, start_date=date(2026, 1, 1)
        )
        response = self.client.post(self.edit_url, self.edit_data(participant=other.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.log.refresh_from_db()
        self.assertEqual(self.log.participant, self.participant)
        self.assertEqual(self.log.case_notes, "Original case note.")

    def test_other_coordinator_and_removed_assignment_cannot_edit(self):
        data = self.edit_data()
        other = create_coordinator("other-revision-sc")
        self.client.force_login(other.user)
        self.assertEqual(self.client.get(self.edit_url).status_code, 404)
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 404)
        self.client.force_login(self.sc.user)
        self.assignment.is_active = False
        self.assignment.save()
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 404)

    def test_worker_and_admin_cannot_use_sc_edit_endpoint(self):
        worker = get_user_model().objects.create_user(username="revision-worker")
        UserProfile.objects.create(user=worker, role=UserProfile.Role.SUPPORT_WORKER)
        for user in (worker, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.edit_url).status_code, 403)
            self.assertEqual(self.client.post(self.edit_url, {}).status_code, 403)

    def test_stale_edit_does_not_overwrite_newer_submission(self):
        data = self.edit_data()
        self.client.post(self.edit_url, data)
        data["case_notes"] = "Old tab overwrites newer record."
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 409)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Revised case note.")
        self.assertEqual(self.log.changes.count(), 1)

    def test_missing_or_forged_edit_token_cannot_save(self):
        for token in ("", "not-signed"):
            response = self.client.post(self.edit_url, self.edit_data(revision_token=token))
            self.assertEqual(response.status_code, 409)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")

    def test_draft_invoice_blocks_edit_even_if_status_drifts(self):
        data = self.edit_data()
        invoice = self.invoice_log()
        self.log.status = "approved"
        self.log.save()
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 403)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertEqual(invoice.lines.get().quantity, Decimal("1.00"))
        response = self.client.get(reverse("coordinator_log_detail", args=[self.log.pk]))
        self.assertNotContains(response, self.edit_url)
        self.assertContains(response, "read-only")

    def test_invoiced_status_without_link_is_still_locked(self):
        self.log.status = "invoiced"
        self.log.save()
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)

    def test_edit_link_and_history_are_visible_to_owner(self):
        response = self.client.get(reverse("coordinator_log_list"))
        self.assertContains(response, self.edit_url)
        self.client.post(self.edit_url, self.edit_data())
        response = self.client.get(reverse("coordinator_log_detail", args=[self.log.pk]))
        self.assertContains(response, "Change history")
        self.assertContains(response, "Original case note.")
        self.assertContains(response, "Revised case note.")

    def test_stale_admin_review_cannot_approve_new_revision(self):
        self.client.force_login(self.admin)
        old = self.review_data()
        self.client.force_login(self.sc.user)
        self.client.post(self.edit_url, self.edit_data())
        self.client.force_login(self.admin)
        for action in ("coordination_log_approve", "coordination_log_reject"):
            response = self.client.post(reverse(action, args=[self.log.pk]), {
                **old, "rejection_reason": "Stale rejection",
            }, follow=True)
            self.assertContains(response, "changed")
            self.log.refresh_from_db()
            self.assertEqual(self.log.status, "submitted")
        self.client.post(reverse("coordination_log_approve", args=[self.log.pk]), self.review_data())
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, "approved")
        self.assertEqual(self.log.changes.count(), 2)

    def test_review_requires_token(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("coordination_log_approve", args=[self.log.pk]))
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, "submitted")

    def test_admin_correction_preserves_invoice_and_source(self):
        invoice = self.invoice_log(Invoice.Status.ISSUED)
        original = invoice.lines.values().get()
        self.client.force_login(self.admin)
        url = f"/coordination-logs/{self.log.pk}/correction/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {
            "kind": "correction", "reason": "Provider name clarification.",
            "details": "Provider name is Example Support.",
            "revision_token": response.context["revision_token"],
        })
        self.assertEqual(response.status_code, 302)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertEqual(self.log.status, "invoiced")
        self.assertEqual(invoice.lines.values().get(), original)
        change = self.log.changes.get()
        self.assertEqual(change.kind, "correction")
        self.assertEqual(change.details, "Provider name is Example Support.")
        self.client.force_login(self.sc.user)
        self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_billing_correction_is_recorded_pending_without_mutation(self):
        self.invoice_log()
        self.client.force_login(self.admin)
        url = f"/coordination-logs/{self.log.pk}/correction/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {
            "kind": "billing_review", "reason": "Review duration.",
            "details": "Confirm 90 minutes with source records.",
            "revision_token": response.context["revision_token"],
        }, follow=True)
        self.assertContains(response, "Invoice review required")
        self.log.refresh_from_db()
        self.assertEqual(self.log.actual_hours, Decimal("1.00"))

    def test_revision_rolls_back_when_audit_write_fails(self):
        data = self.edit_data()
        with patch("coordinators.log_revisions.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.client.post(self.edit_url, data)
        self.log.refresh_from_db()
        self.assertEqual(self.log.case_notes, "Original case note.")
        self.assertFalse(self.log.changes.exists())

    def test_edit_page_keeps_logs_navigation_active(self):
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'aria-current="page"')

    def test_old_edit_token_cannot_override_admin_review(self):
        data = self.edit_data()
        self.client.force_login(self.admin)
        self.client.post(reverse("coordination_log_approve", args=[self.log.pk]), self.review_data())
        self.client.force_login(self.sc.user)
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 409)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, "approved")
        self.assertEqual(self.log.case_notes, "Original case note.")

    def test_another_logs_token_cannot_be_reused(self):
        from .log_revisions import revision_token
        other = CoordinationLog.objects.get(pk=self.log.pk)
        other.pk = None
        other.save()
        response = self.client.post(self.edit_url, self.edit_data(revision_token=revision_token(other)))
        self.assertEqual(response.status_code, 409)

    def test_history_escapes_notes_html(self):
        self.client.post(self.edit_url, self.edit_data(case_notes='<script>alert("x")</script>'))
        response = self.client.get(reverse("coordinator_log_detail", args=[self.log.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("x")</script>')

    def test_admin_correction_requires_reason_details_and_current_token(self):
        self.invoice_log()
        self.client.force_login(self.admin)
        url = f"/coordination-logs/{self.log.pk}/correction/"
        token = self.client.get(url).context["revision_token"]
        for field in ("reason", "details"):
            data = {"kind": "correction", "reason": "A reason", "details": "A detail", "revision_token": token}
            data[field] = "   "
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(self.log.changes.exists())
        self.assertEqual(self.client.post(url, {"kind": "correction", "reason": "Reason", "details": "Details"}).status_code, 409)

    def test_admin_correction_cannot_change_uninvoiced_log(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f"/coordination-logs/{self.log.pk}/correction/").status_code, 403)

    def test_django_admin_cannot_bypass_history_or_invoice_lock(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from .models import CoordinationLogChange
        user = get_user_model().objects.create_superuser(username="super-review", password="test-only")
        request = RequestFactory().get("/admin/")
        request.user = user
        for model in (CoordinationLog, CoordinationLogChange):
            admin_class = admin.site._registry[model]
            self.assertFalse(admin_class.has_add_permission(request))
            self.assertFalse(admin_class.has_change_permission(request))
            self.assertFalse(admin_class.has_delete_permission(request))

    def test_history_formats_dates_and_preserves_zero_breaks(self):
        from .models import CoordinationLogChange
        change = CoordinationLogChange(
            before={"service_date": "2026-10-01", "break_minutes": 0},
            after={"service_date": "2026-10-02", "break_minutes": 15},
        )
        fields = {field["label"]: field for field in change.field_changes}
        self.assertEqual(fields["Service date"]["before"], "01/10/2026")
        self.assertEqual(fields["Break minutes"]["before"], "0")

    def test_rejection_reason_stays_in_log_history_not_general_audit(self):
        self.client.force_login(self.admin)
        reason = "Sensitive participant detail for this record."
        self.client.post(reverse("coordination_log_reject", args=[self.log.pk]),
                         self.review_data(rejection_reason=reason))
        self.assertEqual(self.log.changes.get().reason, reason)
        self.assertNotIn(reason, AuditLog.objects.get(action="coordination_log_rejected").summary)

    def test_confirmed_demo_purge_removes_only_demo_log_history(self):
        from io import StringIO
        from django.core.management import call_command
        from .models import CoordinationLogChange
        self.client.post(self.edit_url, self.edit_data())
        preserved_change = self.log.changes.get()
        demo = create_participant("Fixture", "Only")
        demo.internal_notes = "Created by seed_beta_test_data."
        demo.save()
        demo_log = CoordinationLog.objects.get(pk=self.log.pk)
        demo_log.pk = None
        demo_log.participant = demo
        demo_log.save()
        demo_change = CoordinationLogChange.objects.create(
            log=demo_log, actor=self.admin, kind="correction", details="Demo history only.",
        )
        call_command("purge_trial_demo_data", stdout=StringIO())
        self.assertTrue(CoordinationLogChange.objects.filter(pk=demo_change.pk).exists())
        call_command("purge_trial_demo_data", confirm=True, stdout=StringIO())
        self.assertFalse(CoordinationLogChange.objects.filter(pk=demo_change.pk).exists())
        self.assertTrue(CoordinationLogChange.objects.filter(pk=preserved_change.pk).exists())
        self.assertTrue(CoordinationLog.objects.filter(pk=self.log.pk).exists())
