from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from core.models import AuditLog
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class ServiceLogReviewServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="review-admin")
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.worker_user = get_user_model().objects.create_user(username="review-worker")
        UserProfile.objects.create(user=cls.worker_user, role=UserProfile.Role.SUPPORT_WORKER)
        worker = SupportWorker.objects.create(user=cls.worker_user, first_name="Fictional", last_name="Worker")
        participant = Participant.objects.create(first_name="Fictional", last_name="Participant")
        item = SupportItem.objects.create(item_number="REVIEW-TEST", name="Fictional support", price_limit=Decimal("50"))
        cls.shift = Shift.objects.create(
            participant=participant, worker=worker, support_item=item,
            service_date=date(2026, 11, 2), start_time=time(9), end_time=time(10),
            planned_hours=Decimal("1"), service_type=Shift.ServiceType.OTHER,
            status=Shift.Status.COMPLETED, created_by=cls.admin,
        )
        cls.log = ServiceLog.objects.create_from_shift(
            cls.shift, actual_start_time=time(9), actual_end_time=time(10),
            actual_hours=Decimal("1"), case_notes="Fictional report.",
            rejection_reason="Previous reason",
        )

    def review(self, decision, **kwargs):
        try:
            from service_logs.review import review_service_log
        except ModuleNotFoundError:
            self.fail("The canonical service log review service is missing.")
        return review_service_log(actor=kwargs.pop("actor", self.admin), service_log_id=self.log.pk, decision=decision, **kwargs)

    def test_approve_records_reviewer_clears_reason_and_audits_once(self):
        result = self.review("approve")
        self.log.refresh_from_db()
        self.assertEqual(result.pk, self.log.pk)
        self.assertEqual(self.log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(self.log.reviewed_by, self.admin)
        self.assertIsNotNone(self.log.reviewed_at)
        self.assertEqual(self.log.rejection_reason, "")
        audit = AuditLog.objects.get(object_type="ServiceLog", object_id=str(self.log.pk))
        self.assertEqual(audit.actor, self.admin)
        self.assertEqual(audit.action, AuditLog.Action.SERVICE_LOG_APPROVED)
        self.assertEqual(audit.summary, f"Approved service log {self.log.pk}.")

    def test_reject_preserves_actual_trimmed_reason(self):
        result = self.review("reject", reason="  Correct actual times. \n")
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, ServiceLog.Status.REJECTED)
        self.assertEqual(result.rejection_reason, "Correct actual times.")
        self.assertEqual(self.log.rejection_reason, result.rejection_reason)
        self.assertEqual(self.log.reviewed_by, self.admin)
        self.assertIsNotNone(self.log.reviewed_at)
        self.assertEqual(AuditLog.objects.get().action, AuditLog.Action.SERVICE_LOG_REJECTED)

    def test_blank_rejection_and_unknown_decision_do_not_write(self):
        for decision, reason in (("reject", " \n"), ("waive", "reason")):
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                self.review(decision, reason=reason)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, ServiceLog.Status.SUBMITTED)
        self.assertIsNone(self.log.reviewed_at)
        self.assertFalse(AuditLog.objects.exists())

    def test_every_non_submitted_state_is_stale(self):
        for status in (ServiceLog.Status.APPROVED, ServiceLog.Status.REJECTED, ServiceLog.Status.INVOICED):
            ServiceLog.objects.filter(pk=self.log.pk).update(status=status)
            for decision in ("approve", "reject"):
                with self.subTest(status=status, decision=decision), self.assertRaises(ValueError):
                    self.review(decision, reason="A reason")
            self.log.refresh_from_db()
            self.assertEqual(self.log.status, status)
        self.assertFalse(AuditLog.objects.exists())

    def test_worker_cannot_call_public_service(self):
        with self.assertRaises(PermissionDenied):
            self.review("approve", actor=self.worker_user)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, ServiceLog.Status.SUBMITTED)
        self.assertFalse(AuditLog.objects.exists())

    def test_audit_failure_rolls_back_review(self):
        # External persistence failure must not leave an unaudited approval.
        with patch("core.audit.AuditLog.objects.create", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.review("approve")
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, ServiceLog.Status.SUBMITTED)
        self.assertIsNone(self.log.reviewed_at)
        self.assertEqual(self.log.rejection_reason, "Previous reason")

    def test_repeated_post_preserves_404_without_duplicate_audit(self):
        self.review("approve")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("service_log_approve", args=[self.log.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(AuditLog.objects.count(), 1)
