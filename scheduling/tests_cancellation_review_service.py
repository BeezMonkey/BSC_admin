from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from workers.models import SupportWorker


class CancellationReviewServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="cancellation-service-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.worker_user = get_user_model().objects.create_user(username="cancellation-service-worker")
        UserProfile.objects.create(user=cls.worker_user, role=UserProfile.Role.SUPPORT_WORKER)
        worker = SupportWorker.objects.create(user=cls.worker_user, first_name="Fictional", last_name="Worker")
        participant = Participant.objects.create(first_name="Fictional", last_name="Participant")
        item = SupportItem.objects.create(item_number="CANCEL-REVIEW-TEST", name="Fictional support", price_limit=Decimal("50"))
        cls.shift = Shift.objects.create(
            participant=participant, worker=worker, support_item=item,
            service_date=date(2026, 11, 2), start_time=time(9), end_time=time(10),
            planned_hours=Decimal("1"), service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.CANCELLATION_REVIEW, created_by=cls.admin,
        )
        cls.cancellation = ParticipantCancellation.objects.create(
            shift=cls.shift, cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.OTHER, details="Fictional report.",
            received_at=timezone.now(), previous_shift_status=Shift.Status.CONFIRMED,
            submitted_by=cls.worker_user,
        )

    def review(self, decision, **kwargs):
        try:
            from scheduling.cancellation_review import review_participant_cancellation
        except ModuleNotFoundError:
            self.fail("The canonical cancellation review service is missing.")
        return review_participant_cancellation(actor=kwargs.pop("actor", self.admin), cancellation_id=self.cancellation.pk, decision=decision, **kwargs)

    def test_approve_records_charge_decision_and_exact_audit(self):
        result = self.review("approve", admin_note="  Checked notice. \n")
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(result.pk, self.cancellation.pk)
        self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.APPROVED)
        self.assertEqual(self.cancellation.admin_note, "Checked notice.")
        self.assertEqual(self.cancellation.reviewed_by, self.admin)
        self.assertIsNotNone(self.cancellation.reviewed_at)
        self.assertEqual(self.shift.status, Shift.Status.CANCELLED)
        audit = AuditLog.objects.get()
        self.assertEqual(audit.actor, self.admin)
        self.assertEqual(audit.action, AuditLog.Action.PARTICIPANT_CANCELLATION_APPROVED)
        self.assertEqual(audit.summary, f"Cancellation approved for charging. Shift {self.shift.pk}.")

    def test_waive_allows_no_note_and_cancels_shift(self):
        self.review("waive")
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.WAIVED)
        self.assertEqual(self.cancellation.admin_note, "")
        self.assertEqual(self.shift.status, Shift.Status.CANCELLED)
        self.assertEqual(AuditLog.objects.get().action, AuditLog.Action.PARTICIPANT_CANCELLATION_WAIVED)

    def test_reject_restores_stored_previous_status_and_actual_note(self):
        for previous_status in (Shift.Status.PUBLISHED, Shift.Status.CONFIRMED):
            ParticipantCancellation.objects.filter(pk=self.cancellation.pk).update(
                previous_shift_status=previous_status, status=ParticipantCancellation.Status.PENDING,
            )
            result = self.review("reject", admin_note="  Incorrect report. \n")
            self.shift.refresh_from_db()
            self.assertEqual(result.status, ParticipantCancellation.Status.REJECTED)
            self.assertEqual(result.admin_note, "Incorrect report.")
            self.assertEqual(self.shift.status, previous_status)
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.PARTICIPANT_CANCELLATION_REJECTED).count(), 2)

    def test_blank_rejection_or_unknown_decision_leaves_both_records_untouched(self):
        for decision in ("reject", "unknown"):
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                self.review(decision, admin_note=" \n")
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.PENDING)
        self.assertIsNone(self.cancellation.reviewed_at)
        self.assertEqual(self.shift.status, Shift.Status.CANCELLATION_REVIEW)
        self.assertFalse(AuditLog.objects.exists())

    def test_every_reviewed_state_rejects_all_new_decisions(self):
        for status in (ParticipantCancellation.Status.APPROVED, ParticipantCancellation.Status.WAIVED, ParticipantCancellation.Status.REJECTED):
            ParticipantCancellation.objects.filter(pk=self.cancellation.pk).update(status=status)
            for decision in ("approve", "waive", "reject"):
                with self.subTest(status=status, decision=decision), self.assertRaises(ValueError):
                    self.review(decision, admin_note="Review note")
        self.assertFalse(AuditLog.objects.exists())
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, Shift.Status.CANCELLATION_REVIEW)

    def test_worker_cannot_call_public_service(self):
        with self.assertRaises(PermissionDenied):
            self.review("approve", actor=self.worker_user)
        self.cancellation.refresh_from_db()
        self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.PENDING)
        self.assertFalse(AuditLog.objects.exists())

    def test_audit_failure_rolls_back_both_records(self):
        with patch("core.audit.AuditLog.objects.create", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.review("approve")
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.PENDING)
        self.assertIsNone(self.cancellation.reviewed_at)
        self.assertEqual(self.shift.status, Shift.Status.CANCELLATION_REVIEW)

    def test_repeated_post_preserves_404_without_duplicate_audit(self):
        self.review("approve")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("participant_cancellation_waive", args=[self.cancellation.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(AuditLog.objects.count(), 1)
